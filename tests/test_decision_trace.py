"""The read-only browser adapter receives actual native decision histories."""

import copy
import json

import pytest

from decision_trace import MAX_TRACE_BYTES, MAX_TRACE_EVENTS, review_trace
from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    AuditLog,
    ControlRoom,
    GateRejected,
    SafetyPolicy,
    WorldState,
)


def produced_history(now=0.8):
    policy = SafetyPolicy()
    before = WorldState(
        1, now,
        (
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    advisory = AdvisoryPlanner(policy).plan(before, now)[0]
    room = ControlRoom(policy)
    approval = Approval(advisory.advisory_hash, "approve", now + 0.2, "Controller <review>")
    ack = Ack(advisory.advisory_hash, "accepted", now + 0.4)
    after = room.apply(before, advisory, approval, ack, now + 0.5)
    with pytest.raises(GateRejected):
        room.apply(after, advisory, approval, ack, now + 0.6)
    return before, after, room


@pytest.mark.parametrize("now", [0.8, 1000.0, 1e16])
def test_actual_producer_roundtrip_preserves_world_and_history(now):
    before, after, room = produced_history(now)
    snapshot = copy.deepcopy(room.audit.events)
    raw = json.dumps(snapshot, ensure_ascii=False)
    report = review_trace(raw)
    assert report["chain_valid"] and report["ok"]
    assert report["event_count"] == 5
    assert len(report["advisories"]) == len(report["rejects"]) == 1
    advisory = report["advisories"][0]
    assert (advisory["screen_seq"], advisory["approval_seq"], advisory["ack_seq"]) == (0, 1, 2)
    assert advisory["approver"] == "Controller <review>"
    assert advisory["screen_world_hash"] == before.world_hash
    assert advisory["actuations"] == [{
        "seq": 3, "before_world_hash": before.world_hash, "after_world_hash": after.world_hash,
    }]
    assert report["rejects"] == [{"seq": 4, "reason": room.audit.events[4]["payload"]["reason"]}]
    assert room.audit.events == snapshot
    assert raw == json.dumps(room.audit.events, ensure_ascii=False)
    assert review_trace(json.dumps({"audit_events": snapshot, "label": "native demo"})) == report


def test_recomputed_chain_can_be_valid_while_decision_sequence_is_invalid():
    _, _, room = produced_history()
    changed = AuditLog()
    for event in room.audit.events:
        if event["kind"] != "approval":
            changed.append(event["kind"], event["payload"])
    assert AuditLog.verify(changed.events)
    report = review_trace(json.dumps(changed.events))
    assert report["chain_valid"] and not report["ok"]
    assert any("without approval" in issue for issue in report["issues"])
    assert report["advisories"][0]["approval_seq"] is None
    assert report["advisories"][0]["actuations"]


def test_tampered_hashes_do_not_produce_a_semantic_acceptance():
    _, _, room = produced_history()
    changed = copy.deepcopy(room.audit.events)
    changed[1]["payload"]["decision"] = "reject"
    report = review_trace(json.dumps(changed))
    assert not report["chain_valid"] and not report["ok"]
    assert report["advisories"] == []
    assert report["issues"] == ["audit chain integrity check failed"]
    assert room.audit.events[1]["payload"]["decision"] == "approve"


@pytest.mark.parametrize("raw", [None, "{", "null", "{}", "[null]", "[[[]]]", '{"audit_events": {}}'])
def test_unreadable_inputs_raise_a_delivery_error(raw):
    with pytest.raises((TypeError, ValueError), match="Decision trace|Expected an event list"):
        review_trace(raw)


def test_valid_hashes_with_malformed_binding_are_not_presented_as_a_review():
    log = AuditLog()
    log.append("approval", {"advisory_hash": [], "decision": "approve"})
    assert AuditLog.verify(log.events)
    with pytest.raises(ValueError, match="malformed event data"):
        review_trace(json.dumps(log.events))


def test_empty_and_rejection_only_histories_keep_native_meaning():
    empty = review_trace("[]")
    assert empty["ok"] and empty["event_count"] == 0 and empty["advisories"] == []
    log = AuditLog()
    log.append("reject", {"reason": "stale_state"})
    report = review_trace(json.dumps(log.events))
    assert report["ok"] and report["chain_valid"]
    assert report["rejects"] == [{"seq": 0, "reason": "stale_state"}]


def test_byte_limit_accepts_boundary_and_counts_utf8_bytes():
    assert review_trace("[]" + " " * (MAX_TRACE_BYTES - 2))["ok"]
    with pytest.raises(ValueError, match="2 MiB"):
        review_trace("[]" + " " * (MAX_TRACE_BYTES - 1))
    raw = json.dumps({"audit_events": [], "note": "é" * (MAX_TRACE_BYTES // 2)}, ensure_ascii=False)
    assert len(raw) < MAX_TRACE_BYTES < len(raw.encode("utf-8"))
    with pytest.raises(ValueError, match="2 MiB"):
        review_trace(raw)


def test_event_limit_checks_before_processing_and_accepts_exact_boundary():
    with pytest.raises(ValueError, match="5,000 event"):
        review_trace(json.dumps([{}] * (MAX_TRACE_EVENTS + 1)))
    log = AuditLog()
    for _ in range(MAX_TRACE_EVENTS):
        log.append("reject", {"reason": "stale_state"})
    report = review_trace(json.dumps(log.events))
    assert report["ok"] and report["event_count"] == MAX_TRACE_EVENTS
    assert len(report["rejects"]) == MAX_TRACE_EVENTS


def test_excessive_nesting_and_invalid_text_are_bounded_delivery_errors():
    with pytest.raises(ValueError, match="not readable JSON|malformed event data"):
        review_trace("[" * 1500 + "]" * 1500)
    with pytest.raises(ValueError, match="valid UTF-8"):
        review_trace("\ud800")
