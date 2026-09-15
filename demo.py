import json
from dataclasses import asdict

from towerops import Ack, Approval, AdvisoryPlanner, Aircraft, ControlRoom, SafetyPolicy, WorldState


def main():
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
        raise SystemExit("No advisory produced")
    advisory = advisories[0]
    approval = Approval(advisory.advisory_hash, "approve", 1002.2, "synthetic-controller")
    ack = Ack(advisory.advisory_hash, "accepted", 1002.4)
    room = ControlRoom(policy)
    before_conflict = policy.state_has_conflict(state)
    after = room.apply(state, advisory, approval, ack, now=1002.5)
    result = {
        "before_conflict": before_conflict,
        "advisory": asdict(advisory),
        "after_conflict": policy.state_has_conflict(after),
        "audit_valid": room.audit.verify(room.audit.events),
        "audit_events": room.audit.events,
        "disclaimer": "Synthetic research simulation only; not operational ATC or real-aircraft control.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
