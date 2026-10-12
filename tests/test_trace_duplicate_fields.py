"""Saved trace readers must not silently discard duplicate JSON evidence."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import decision_trace
from audit_replay import replay_audit
from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    AuditLog,
    ControlRoom,
    SafetyPolicy,
    WorldState,
)

ROOT = Path(__file__).resolve().parents[1]


def _rejection_event():
    log = AuditLog()
    log.append("reject", {"reason": "stale_state"})
    return json.dumps(log.events)


def _ambiguous_documents():
    missing_screen = AuditLog()
    missing_screen.append("approval", {"advisory_hash": "b" * 64, "decision": "approve"})
    assert not replay_audit(missing_screen.events).ok
    rejection = _rejection_event()
    nested = AuditLog()
    nested.append("observer_note", {"metadata": {"label": "retained"}})
    return {
        "wrapper-hides-failed-history": (
            '{"audit_events":' + json.dumps(missing_screen.events) + ',"audit_events":[]}'
        ),
        "event-kind": rejection.replace('"kind": "reject"', '"kind":"approval","kind":"reject"'),
        "payload-value": rejection.replace('"reason": "stale_state"', '"reason":"other","reason":"stale_state"'),
        "deep-value": json.dumps(nested.events).replace('"label": "retained"', '"label":"hidden","label":"retained"'),
        "escaped-wrapper-name": r'{"audit_events":[null],"\u0061udit_events":[]}',
        "equal-values": '{"audit_events":[],"audit_events":[]}',
        "unrelated-wrapper-metadata": '{"audit_events":[],"note":1,"note":2}',
    }


AMBIGUOUS = _ambiguous_documents()


@pytest.mark.parametrize("raw", AMBIGUOUS.values(), ids=AMBIGUOUS)
def test_adapter_refuses_duplicate_fields_before_replay(raw, monkeypatch):
    calls = []
    native_replay = decision_trace.replay_audit

    def observed_replay(events):
        calls.append(events)
        return native_replay(events)

    monkeypatch.setattr(decision_trace, "replay_audit", observed_replay)
    with pytest.raises(ValueError, match="not readable JSON"):
        decision_trace.review_trace(raw)
    assert calls == []


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("raw", AMBIGUOUS.values(), ids=AMBIGUOUS)
def test_cli_refuses_duplicate_fields_without_a_successful_summary(raw, source, tmp_path):
    path = tmp_path / "trace.json"
    saved = raw.encode("utf-8")
    path.write_bytes(saved)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "audit_replay.py"), str(path) if source == "file" else "-"],
        input=raw if source == "stdin" else None,
        text=True, capture_output=True, check=False, timeout=10,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert proc.stdout == ""
    assert "Duplicate JSON object fields" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert path.read_bytes() == saved


def _native_history():
    policy = SafetyPolicy()
    state = WorldState(1, 1000.0, (
        Aircraft("LEFT", -5.0, 0.0, 10000.0, 1.0, 0.0),
        Aircraft("RIGHT", 5.0, 0.0, 10000.0, -1.0, 0.0),
    ))
    advisory = AdvisoryPlanner(policy).plan(state, 1002.0)[0]
    room = ControlRoom(policy)
    room.apply(
        state, advisory,
        Approval(advisory.advisory_hash, "approve", 1002.2, "Authored reviewer"),
        Ack(advisory.advisory_hash, "accepted", 1002.4), 1002.5,
    )
    return room.audit.events


@pytest.mark.parametrize("wrapper", [False, True])
def test_real_native_history_has_identical_adapter_and_cli_results(wrapper, tmp_path):
    events = _native_history()
    raw = json.dumps({"audit_events": events, "label": "native"} if wrapper else events)
    original = json.dumps(events)
    expected = decision_trace.review_trace(original)
    assert expected["ok"] and expected["chain_valid"] and expected["event_count"] == 4
    assert decision_trace.review_trace(raw) == expected
    path = tmp_path / "native-trace.json"
    path.write_text(raw, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "audit_replay.py"), str(path)],
        text=True, capture_output=True, check=False, timeout=10,
    )
    assert proc.returncode == 0 and proc.stderr == ""
    assert json.loads(proc.stdout) == {
        "ok": True, "chain_valid": True, "advisories": 1,
        "actuated": 1, "rejects": 0, "issues": [],
    }
    assert path.read_text(encoding="utf-8") == raw
    assert json.dumps(events) == original


def test_unique_fields_preserve_exact_numbers_literals_and_distinct_objects():
    log = AuditLog()
    log.append("observer_note", {
        "integer": 9007199254740993, "float": 1.0, "negative_zero": -0.0,
        "literal": '"label": 1, "label": 2; é',
        "left": {"label": "one"}, "right": {"label": "two"},
    })
    raw = json.dumps(log.events, ensure_ascii=False)
    report = decision_trace.review_trace(raw)
    assert report == {
        "ok": True, "chain_valid": True, "event_count": 1,
        "advisories": [], "rejects": [], "issues": [],
    }
    assert decision_trace.review_trace('{"audit_events":[],"Audit_Events":1}')["ok"]
    assert decision_trace.review_trace("[]")["ok"]
    assert raw == json.dumps(log.events, ensure_ascii=False)


def test_unique_native_findings_are_still_reported_instead_of_parse_errors():
    log = AuditLog()
    log.append("approval", {"advisory_hash": "b" * 64, "decision": "approve"})
    report = decision_trace.review_trace(json.dumps(log.events))
    assert report["chain_valid"] and not report["ok"]
    assert any("never admitted" in issue for issue in report["issues"])
    log.events[0]["payload"]["decision"] = "reject"
    report = decision_trace.review_trace(json.dumps(log.events))
    assert not report["chain_valid"] and not report["ok"]
    assert report["issues"] == ["audit chain integrity check failed"]
