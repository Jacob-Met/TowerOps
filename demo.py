import json
import sys
from dataclasses import asdict

from towerops import Ack, Approval, AdvisoryPlanner, Aircraft, ControlRoom, SafetyPolicy, WorldState


def main() -> int:
    policy = SafetyPolicy()
    state = WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    planner = AdvisoryPlanner(policy)
    advisories = planner.plan(state, now=1002.0)
    if not advisories:
        print("FAIL: planner produced no advisory for the conflict scenario", file=sys.stderr)
        return 1
    advisory = advisories[0]
    approval = Approval(advisory.advisory_hash, "approve", 1002.2, "synthetic-controller")
    ack = Ack(advisory.advisory_hash, "accepted", 1002.4)
    room = ControlRoom(policy)
    before_conflict = policy.state_has_conflict(state)
    after = room.apply(state, advisory, approval, ack, now=1002.5)
    after_conflict = policy.state_has_conflict(after)
    audit_valid = room.audit.verify(room.audit.events)
    actuated = any(e["kind"] == "simulated_actuation" for e in room.audit.events)
    result = {
        "before_conflict": before_conflict,
        "advisory": asdict(advisory),
        "after_conflict": after_conflict,
        "audit_valid": audit_valid,
        "audit_events": room.audit.events,
        "disclaimer": "Synthetic research simulation only; not operational ATC or real-aircraft control.",
    }
    print(json.dumps(result, indent=2))
    # The demo advertises deterministic conflict resolution with a verified
    # audit chain; fail loudly instead of printing unchecked claims.
    failed = []
    if before_conflict is not True:
        failed.append("before_conflict")
    if after_conflict is not False:
        failed.append("after_conflict")
    if audit_valid is not True:
        failed.append("audit_valid")
    if not actuated:
        failed.append("simulated_actuation")
    if failed:
        print(f"FAIL: demo invariants violated: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
