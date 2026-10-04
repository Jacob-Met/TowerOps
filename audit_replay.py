"""Audit replay verification for TowerOps.

``AuditLog.verify`` proves a chain is untampered, but a fully recomputed chain
can still tell a false story (e.g. an actuation with no approval). This module
replays the recorded lifecycle and checks the semantic story the gate claims:

- every ``simulated_actuation`` is preceded, for the same advisory hash, by a
  ``screen_pass`` admission, an ``approve`` approval, and an ``accepted`` ack,
  in that order;
- the actuation's ``before_world_hash`` matches the world hash the advisory
  was screened against.

Usage:
    python3 audit_replay.py demo_output.json   # demo.py's JSON (audit_events)
    python3 audit_replay.py events.json        # raw event list
    cat demo_output.json | python3 audit_replay.py

Exit status 0 when the replay is clean, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

from towerops import AuditLog

_BINDING_KINDS = ("approval", "ack", "simulated_actuation")


@dataclass
class ActuationRecord:
    seq: int
    before_world_hash: str | None = None
    after_world_hash: str | None = None


@dataclass
class AdvisoryReplay:
    advisory_hash: str | None
    screen_seq: int | None = None
    screen_world_hash: str | None = None
    approval_seq: int | None = None
    approver: str | None = None
    ack_seq: int | None = None
    actuations: list[ActuationRecord] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def add_issue(self, message: str) -> None:
        if message not in self.issues:
            self.issues.append(message)


@dataclass
class ReplayReport:
    chain_valid: bool
    advisories: dict[Any, AdvisoryReplay] = field(default_factory=dict)
    rejects: list[dict[str, Any]] = field(default_factory=list)

    @property
    def issues(self) -> list[str]:
        found: list[str] = []
        if not self.chain_valid:
            found.append("audit chain integrity check failed")
        for adv in self.advisories.values():
            label = adv.advisory_hash[:12] if adv.advisory_hash else "<missing>"
            found.extend(f"{label}: {i}" for i in adv.issues)
        return found

    @property
    def ok(self) -> bool:
        return not self.issues


def replay_audit(events: list[dict[str, Any]]) -> ReplayReport:
    """Replay an audit event chain and verify its semantic story."""
    report = ReplayReport(chain_valid=AuditLog.verify(list(events)))
    if not report.chain_valid:
        return report

    for seq, event in enumerate(events):
        kind = event.get("kind")
        payload = event.get("payload") or {}
        if kind == "screen_pass":
            world_hash = payload.get("world_hash")
            for adv_hash in payload.get("advisory_hashes", []):
                adv = report.advisories.setdefault(adv_hash, AdvisoryReplay(adv_hash))
                if adv.screen_seq is None:
                    adv.screen_seq = seq
                    adv.screen_world_hash = world_hash
        elif kind == "reject":
            report.rejects.append({"seq": seq, "reason": payload.get("reason")})
        elif kind in _BINDING_KINDS:
            adv_hash = payload.get("advisory_hash")
            adv = report.advisories.setdefault(adv_hash, AdvisoryReplay(adv_hash))
            if adv_hash is None:
                adv.add_issue(f"{kind} event missing advisory_hash")
                continue
            if kind == "approval":
                if adv.approval_seq is None:
                    adv.approval_seq = seq
                    adv.approver = payload.get("approver")
                if payload.get("decision") != "approve":
                    adv.add_issue(f"approval decision is {payload.get('decision')!r}, not 'approve'")
            elif kind == "ack":
                if adv.ack_seq is None:
                    adv.ack_seq = seq
                if payload.get("status") != "accepted":
                    adv.add_issue(f"ack status is {payload.get('status')!r}, not 'accepted'")
            elif kind == "simulated_actuation":
                adv.actuations.append(
                    ActuationRecord(
                        seq=seq,
                        before_world_hash=payload.get("before_world_hash"),
                        after_world_hash=payload.get("after_world_hash"),
                    )
                )
        # Unknown event kinds are ignored: replay checks the gate's story,
        # not an exhaustive event vocabulary.

    for adv_hash, adv in report.advisories.items():
        if adv_hash is None:
            continue  # malformed-binding entry already carries its issue
        if adv.screen_seq is None and (adv.approval_seq is not None or adv.ack_seq is not None):
            adv.add_issue("approval/ack recorded for an advisory never admitted by screen_pass")
        if adv.ack_seq is not None and adv.approval_seq is None:
            adv.add_issue("ack recorded without any approval")
        if (
            adv.ack_seq is not None
            and adv.approval_seq is not None
            and adv.ack_seq < adv.approval_seq
        ):
            adv.add_issue("ack recorded before approval")
        if (
            adv.screen_seq is not None
            and adv.approval_seq is not None
            and adv.screen_seq > adv.approval_seq
        ):
            adv.add_issue("approval recorded before screen_pass admission")
        for act in adv.actuations:
            if adv.screen_seq is None:
                adv.add_issue("actuation without screen_pass admission")
            if adv.approval_seq is None:
                adv.add_issue("actuation without approval")
            elif adv.approval_seq > act.seq:
                adv.add_issue("approval recorded after actuation")
            if adv.ack_seq is None:
                adv.add_issue("actuation without accepted ack")
            elif adv.ack_seq > act.seq:
                adv.add_issue("ack recorded after actuation")
            if (
                adv.screen_world_hash is not None
                and act.before_world_hash is not None
                and act.before_world_hash != adv.screen_world_hash
            ):
                adv.add_issue("actuation before_world_hash does not match screened world_hash")
    return report


def _load_events(source: str) -> list[dict[str, Any]]:
    if source == "-":
        raw = sys.stdin.read()
    else:
        with open(source, "r", encoding="utf-8") as fh:
            raw = fh.read()
    data = json.loads(raw)
    if isinstance(data, dict) and isinstance(data.get("audit_events"), list):
        return data["audit_events"]
    if isinstance(data, list):
        return data
    raise ValueError("expected a JSON event list or an object with an 'audit_events' list")


def main(argv: list[str]) -> int:
    source = argv[1] if len(argv) > 1 else "-"
    try:
        events = _load_events(source)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot load audit events: {exc}", file=sys.stderr)
        return 2
    try:
        report = replay_audit(events)
        summary = {
            "ok": report.ok,
            "chain_valid": report.chain_valid,
            "advisories": len(report.advisories),
            "actuated": sum(1 for a in report.advisories.values() if a.actuations),
            "rejects": len(report.rejects),
            "issues": report.issues,
        }
    except Exception as exc:  # fail closed: never die with a bare traceback
        print(f"error: replay failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
