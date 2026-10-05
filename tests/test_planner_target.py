"""Planner target selection: advisories must target a conflicting aircraft.

Regression for the defect where ``AdvisoryPlanner.plan()`` always maneuvered
the highest-id aircraft (``values[-1]``) even when the actual conflict was
between two other aircraft: the planner returned a gate-safe advisory for an
uninvolved aircraft while the real conflict persisted.
"""

from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    ControlRoom,
    SafetyPolicy,
    WorldState,
)


def _three_aircraft_state() -> WorldState:
    # TWR1 and TWR2 are head-on (conflict); TWR3 is far away and uninvolved.
    # The old target selection picked TWR3 (highest id) and returned a
    # gate-safe vy=2.0 advisory for it, leaving the conflict unresolved.
    return WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR1", 0.0, 0.0, 5000.0, 3.0, 0.0, 0.0),
            Aircraft("TWR2", 10.0, 0.0, 5000.0, -3.0, 0.0, 0.0),
            Aircraft("TWR3", 100.0, 100.0, 9000.0, 0.5, 0.0, 0.0),
        ),
    )


def test_planner_targets_conflicting_aircraft_not_bystander():
    policy = SafetyPolicy()
    state = _three_aircraft_state()
    assert policy.state_has_conflict(state)
    # TWR3 participates in no conflicting pair.
    assert all(
        not policy._pair_conflict(state.get("TWR3"), other)
        for other in state.aircraft
        if other.aircraft_id != "TWR3"
    )
    planner = AdvisoryPlanner(policy)
    advisories = planner.plan(state, now=1002.0)
    assert len(advisories) == 1
    advisory = advisories[0]
    # The advisory must aim at an aircraft that is actually in conflict.
    assert advisory.aircraft_id in ("TWR1", "TWR2")
    assert advisory.aircraft_id != "TWR3"
    assert policy.advisory_safe(state, advisory)


def test_conflicting_target_advisory_resolves_end_to_end():
    policy = SafetyPolicy()
    state = _three_aircraft_state()
    planner = AdvisoryPlanner(policy)
    advisory = planner.plan(state, now=1002.0)[0]
    room = ControlRoom(policy)
    approval = Approval(advisory.advisory_hash, "approve", 1002.2, "synthetic-controller")
    ack = Ack(advisory.advisory_hash, "accepted", 1002.4)
    after = room.apply(state, advisory, approval, ack, now=1002.5)
    # The gate requires the maneuvered aircraft to be conflict-free with every
    # other aircraft, so applying a planner advisory must clear the conflict.
    assert not policy.state_has_conflict(after)
    # The bystander aircraft is untouched by the advisory.
    assert after.get("TWR3") == state.get("TWR3")


def test_conflicting_aircraft_helper_reports_involved_ids():
    policy = SafetyPolicy()
    state = _three_aircraft_state()
    involved = policy.conflicting_aircraft(state)
    assert [a.aircraft_id for a in involved] == ["TWR1", "TWR2"]
    assert policy.conflicting_aircraft(
        WorldState(
            version=1,
            observed_at=1000.0,
            aircraft=(
                Aircraft("TWR1", -50.0, 0.0, 10000.0, 1.0, 0.0),
                Aircraft("TWR2", 50.0, 0.0, 12000.0, -1.0, 0.0),
            ),
        )
    ) == []
