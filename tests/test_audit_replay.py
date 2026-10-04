"""Audit replay verification.

Covers the README-advertised "hash-chained audit log with replay verification":
``AuditLog.verify`` proves a chain is untampered, while ``replay_audit`` proves
the chain tells a coherent gate story. The key case is a *recomputed* valid
chain carrying a false story (e.g. an actuation with no approval) — chain
integrity passes, replay must fail.
"""

import json
import subprocess
import sys
from pathlib import Path

from audit_replay import ReplayReport, replay_audit
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

NOW = 1002.0


def _demo_flow_events():
    policy = SafetyPolicy()
    state = WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    room = ControlRoom(policy)
    advisory = AdvisoryPlanner(policy).plan(state, now=NOW)[0]
    room.apply(
        state,
        advisory,
        Approval(advisory.advisory_hash, "approve", NOW + 0.2, "synthetic-controller"),
        Ack(advisory.advisory_hash, "accepted", NOW + 0.4),
        now=NOW + 0.5,
    )
    return room.audit.events, advisory.advisory_hash, state.world_hash


def test_demo_audit_replays_clean():
    events, adv_hash, world_hash = _demo_flow_events()
    report = replay_audit(events)
    assert isinstance(report, ReplayReport)
    assert report.ok, report.issues
    assert report.chain_valid
    assert len(report.advisories) == 1
    adv = report.advisories[adv_hash]
    assert adv.screen_seq == 0
    assert adv.screen_world_hash == world_hash
    assert adv.screen_seq < adv.approval_seq < adv.ack_seq
    assert len(adv.actuations) == 1
    act = adv.actuations[0]
    assert adv.ack_seq < act.seq
    assert act.before_world_hash == world_hash
    assert act.after_world_hash is not None
    assert act.after_world_hash != world_hash
    assert adv.approver == "synthetic-controller"


def test_reject_only_chain_replays_without_issue():
    log = AuditLog()
    log.append("reject", {"reason": "stale_state", "world_hash": "a" * 64})
    report = replay_audit(log.events)
    assert report.ok, report.issues
    assert report.chain_valid
    assert len(report.rejects) == 1
    assert not report.advisories


def test_empty_chain_replays_clean():
    report = replay_audit([])
    assert report.ok
    assert report.chain_valid


def test_broken_chain_hash_fails_replay():
    events, _, _ = _demo_flow_events()
    events = [dict(e) for e in events]
    events[1]["payload"] = dict(events[1]["payload"])
    events[1]["payload"]["decision"] = "reject"
    report = replay_audit(events)
    assert not report.chain_valid
    assert not report.ok


def test_forged_actuation_without_approval_is_caught():
    # A recomputed chain with valid hashes but a false story: screen_pass
    # followed directly by a simulated_actuation, skipping approval and ack.
    # Chain integrity passes; replay must reject the story.
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append(
        "simulated_actuation",
        {"advisory_hash": adv_hash, "before_world_hash": world_hash, "after_world_hash": "c" * 64},
    )
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert report.chain_valid
    assert not report.ok
    adv = report.advisories[adv_hash]
    assert any("without approval" in i for i in adv.issues)
    assert any("without accepted ack" in i for i in adv.issues)


def test_world_hash_linkage_break_is_caught():
    adv_hash = "b" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": "a" * 64, "advisory_hashes": [adv_hash]})
    log.append("approval", {"advisory_hash": adv_hash, "decision": "approve", "approver": "x"})
    log.append("ack", {"advisory_hash": adv_hash, "status": "accepted"})
    log.append(
        "simulated_actuation",
        {"advisory_hash": adv_hash, "before_world_hash": "d" * 64, "after_world_hash": "c" * 64},
    )
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert not report.ok
    assert any("before_world_hash" in i for i in report.advisories[adv_hash].issues)


def test_out_of_order_approval_is_caught():
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append(
        "simulated_actuation",
        {"advisory_hash": adv_hash, "before_world_hash": world_hash, "after_world_hash": "c" * 64},
    )
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append("approval", {"advisory_hash": adv_hash, "decision": "approve", "approver": "x"})
    log.append("ack", {"advisory_hash": adv_hash, "status": "accepted"})
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert not report.ok
    issues = report.advisories[adv_hash].issues
    assert any("after actuation" in i for i in issues)


def test_ack_without_approval_is_caught():
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append("ack", {"advisory_hash": adv_hash, "status": "accepted"})
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert not report.ok
    assert any("without any approval" in i for i in report.advisories[adv_hash].issues)


def test_ack_before_approval_is_caught():
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append("ack", {"advisory_hash": adv_hash, "status": "accepted"})
    log.append("approval", {"advisory_hash": adv_hash, "decision": "approve", "approver": "x"})
    log.append(
        "simulated_actuation",
        {"advisory_hash": adv_hash, "before_world_hash": world_hash, "after_world_hash": "c" * 64},
    )
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert not report.ok
    assert any("before approval" in i for i in report.advisories[adv_hash].issues)


def test_second_actuation_with_bad_linkage_is_caught():
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append("approval", {"advisory_hash": adv_hash, "decision": "approve", "approver": "x"})
    log.append("ack", {"advisory_hash": adv_hash, "status": "accepted"})
    log.append(
        "simulated_actuation",
        {"advisory_hash": adv_hash, "before_world_hash": world_hash, "after_world_hash": "c" * 64},
    )
    log.append(
        "simulated_actuation",
        {"advisory_hash": adv_hash, "before_world_hash": "d" * 64, "after_world_hash": "e" * 64},
    )
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert not report.ok
    assert any("before_world_hash" in i for i in report.advisories[adv_hash].issues)


def test_non_approve_decision_is_flagged():
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append("approval", {"advisory_hash": adv_hash, "decision": "reject", "approver": "x"})
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert not report.ok
    assert any("not 'approve'" in i for i in report.advisories[adv_hash].issues)


def test_non_accepted_ack_is_flagged():
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append("approval", {"advisory_hash": adv_hash, "decision": "approve", "approver": "x"})
    log.append("ack", {"advisory_hash": adv_hash, "status": "rejected"})
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)
    assert not report.ok
    assert any("not 'accepted'" in i for i in report.advisories[adv_hash].issues)


def test_missing_advisory_hash_does_not_crash():
    log = AuditLog()
    log.append("screen_pass", {"world_hash": "a" * 64, "advisory_hashes": ["b" * 64]})
    log.append("approval", {"decision": "approve", "approver": "x"})  # no advisory_hash
    assert AuditLog.verify(log.events)
    report = replay_audit(log.events)  # must not raise
    assert not report.ok
    assert any("missing advisory_hash" in i for i in report.issues)


def test_cli_accepts_demo_json(tmp_path):
    events, _, _ = _demo_flow_events()
    demo_doc = {"audit_events": events, "disclaimer": "synthetic"}
    path = tmp_path / "demo.json"
    path.write_text(json.dumps(demo_doc), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "audit_replay.py", str(path)],
        cwd=repo_root,
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    summary = json.loads(proc.stdout.decode())
    assert summary["ok"] is True
    assert summary["actuated"] == 1


def test_cli_rejects_forged_chain(tmp_path):
    adv_hash = "b" * 64
    world_hash = "a" * 64
    log = AuditLog()
    log.append("screen_pass", {"world_hash": world_hash, "advisory_hashes": [adv_hash]})
    log.append(
        "simulated_actuation",
        {"advisory_hash": adv_hash, "before_world_hash": world_hash, "after_world_hash": "c" * 64},
    )
    path = tmp_path / "events.json"
    path.write_text(json.dumps(log.events), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "audit_replay.py", str(path)],
        cwd=repo_root,
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 1, proc.stdout.decode()
    summary = json.loads(proc.stdout.decode())
    assert summary["ok"] is False
    assert summary["issues"]


def test_cli_handles_malformed_event_without_traceback(tmp_path):
    log = AuditLog()
    log.append("approval", {"decision": "approve"})  # no advisory_hash
    path = tmp_path / "events.json"
    path.write_text(json.dumps(log.events), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "audit_replay.py", str(path)],
        cwd=repo_root,
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 1, proc.stderr.decode()
    assert "Traceback" not in proc.stderr.decode()
    summary = json.loads(proc.stdout.decode())
    assert summary["ok"] is False
