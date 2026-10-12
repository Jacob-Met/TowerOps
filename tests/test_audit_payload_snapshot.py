"""Caller reuse must not rewrite a Python audit event already recorded."""

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from audit_replay import replay_audit
from towerops import (
    ZERO_HASH,
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    AuditLog,
    ControlRoom,
    SafetyPolicy,
    WorldState,
    canonical_bytes,
)


def test_later_outer_dictionary_edits_do_not_rewrite_event():
    payload = {"decision": "approve", "approver": "caller"}
    log = AuditLog()
    head = log.append("approval", payload)

    payload["decision"] = "reject"
    payload["later"] = True
    del payload["approver"]

    assert log.events[0]["payload"] == {"decision": "approve", "approver": "caller"}
    assert log.head == head
    assert AuditLog.verify(log.events)


def test_nested_aliases_and_tuple_members_are_captured():
    shared = {"steps": [{"status": "accepted"}]}
    nested_numbers = [-0.0, 1, None, True]
    payload = {"routes": [shared, {"same": shared}], "metadata": ("café 雪", nested_numbers)}
    log = AuditLog()
    log.append("authored_observation", payload)
    before = canonical_bytes(log.events)

    shared["steps"][0]["status"] = "changed"
    shared["steps"].clear()
    nested_numbers.append("later")
    payload["routes"].reverse()

    assert canonical_bytes(log.events) == before
    captured = log.events[0]["payload"]
    assert captured["routes"][0] == {"steps": [{"status": "accepted"}]}
    assert captured["routes"][1]["same"] == captured["routes"][0]
    assert type(captured["metadata"]) is tuple
    assert type(captured["metadata"][1][0]) is float
    assert math.copysign(1.0, captured["metadata"][1][0]) == -1.0
    assert type(captured["metadata"][1][1]) is int
    assert AuditLog.verify(log.events)


def test_reusing_one_payload_keeps_each_append_value():
    payload = {"iteration": 1, "observations": []}
    log = AuditLog()
    first = log.append("observation", payload)
    payload["iteration"] = 2
    payload["observations"].append("second")
    second = log.append("observation", payload)
    payload["iteration"] = 3
    payload["observations"].append("unsaved")

    assert log.events[0]["payload"] == {"iteration": 1, "observations": []}
    assert log.events[1]["payload"] == {"iteration": 2, "observations": ["second"]}
    assert log.events[1]["prev_hash"] == first
    assert log.head == second
    assert AuditLog.verify(log.events)


def test_screen_return_list_reuse_keeps_saved_replay_valid(tmp_path):
    world = WorldState(
        1,
        1000.0,
        (
            Aircraft("PAYLOAD-A", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("PAYLOAD-B", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    policy = SafetyPolicy()
    room = ControlRoom(policy)
    advisory = AdvisoryPlanner(policy).plan(world, now=1000.0)[0]
    returned = room.screen_batch(world, [advisory], now=1000.0)
    room.apply(
        world,
        advisory,
        Approval(advisory.advisory_hash, "approve", 1000.0, "synthetic-controller"),
        Ack(advisory.advisory_hash, "accepted", 1000.0),
        now=1000.0,
    )
    assert len(room.audit.events) == 5
    assert replay_audit(room.audit.events).ok
    before = canonical_bytes(room.audit.events)
    returned.clear()

    saved = tmp_path / "recorded-audit.json"
    saved.write_bytes(canonical_bytes({"audit_events": room.audit.events}))
    process = subprocess.run(
        [sys.executable, "-B", "audit_replay.py", str(saved)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    summary = json.loads(process.stdout)
    assert canonical_bytes(room.audit.events) == before, summary
    assert process.returncode == 0, (process.stdout, process.stderr)
    assert summary["ok"] is True
    assert summary["chain_valid"] is True
    assert summary["actuated"] == 1
    assert replay_audit(room.audit.events).ok


def test_unchanged_payload_keeps_native_types_and_exact_wire_hash():
    payload = {
        "unicode": "café 雪\n",
        "values": [-0.0, 1.0, 1, 2**80, None, False],
        "tuple": ("retained", {"value": 3}),
    }
    event = {"seq": 0, "kind": "observation", "payload": payload, "prev_hash": ZERO_HASH}
    encoded = canonical_bytes(event)
    expected = hashlib.sha256(ZERO_HASH.encode("ascii") + b"\n" + encoded).hexdigest()
    original_input = canonical_bytes(payload)

    log = AuditLog()
    assert log.append("observation", payload) == expected
    assert canonical_bytes(payload) == original_input
    assert canonical_bytes({key: value for key, value in log.events[0].items() if key != "event_hash"}) == encoded
    captured = log.events[0]["payload"]
    assert type(captured["tuple"]) is tuple
    assert [type(value) for value in captured["values"]] == [float, float, int, int, type(None), bool]
    assert AuditLog.verify(log.events)


def test_direct_recorded_payload_tampering_is_still_detected():
    log = AuditLog()
    log.append("observation", {"rows": [{"value": "recorded"}]})
    log.events[0]["payload"]["rows"][0]["value"] = "tampered"
    assert not AuditLog.verify(log.events)


@pytest.mark.parametrize("cyclic", [False, True])
def test_failed_serialization_does_not_publish_or_consume_sequence(cyclic):
    log = AuditLog()
    head = log.append("observation", {"record": "kept"})
    before = canonical_bytes(log.events)
    if cyclic:
        payload = {"rows": []}
        payload["rows"].append(payload)
        error = ValueError
    else:
        payload = {"unsupported": object()}
        error = TypeError

    with pytest.raises(error):
        log.append("invalid_observation", payload)

    assert canonical_bytes(log.events) == before
    assert log.head == head
    log.append("observation", {"record": "next"})
    assert log.events[-1]["seq"] == 1
    assert log.events[-1]["prev_hash"] == head
    assert AuditLog.verify(log.events)
