"""Fail-closed on non-finite aircraft state.

Regression tests for a demonstrated defect: NaN/inf in aircraft fields made
``SafetyPolicy._pair_conflict`` return False (unknown separation silently
treated as safe), so the gate could approve steering an aircraft with unknown
state into another aircraft. Non-finite fields must now fail closed.
"""

from towerops import (
    Ack,
    Advisory,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    ControlRoom,
    SafetyPolicy,
    WorldState,
)


def _nan_altitude_state() -> WorldState:
    return WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("W", 0.0, 0.0, float("nan"), 0.0, 0.0),
            Aircraft("B", 10.0, 0.0, 10000.0, 0.0, 0.0),
        ),
    )


def test_nan_altitude_reports_conflict():
    policy = SafetyPolicy()
    assert policy.state_has_conflict(_nan_altitude_state()) is True


def test_nan_altitude_head_on_advisory_rejected():
    policy = SafetyPolicy()
    state = _nan_altitude_state()
    advisory = Advisory(
        aircraft_id="W",
        world_hash=state.world_hash,
        set_vx_nm_min=6.0,  # max allowed speed, straight at B
        set_vy_nm_min=0.0,
        set_climb_ft_min=0.0,
        issued_at=1000.0,
        expires_at=1010.0,
        rationale="regression: unknown vertical separation must not pass",
    )
    assert policy.advisory_safe(state, advisory) is False


def test_nan_advisory_velocity_rejected():
    policy = SafetyPolicy()
    state = WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    advisory = Advisory(
        aircraft_id="TWR419",
        world_hash=state.world_hash,
        set_vx_nm_min=float("nan"),
        set_vy_nm_min=2.0,
        set_climb_ft_min=0.0,
        issued_at=1000.0,
        expires_at=1010.0,
        rationale="regression: NaN command velocity must not pass",
    )
    assert policy.advisory_safe(state, advisory) is False


def test_inf_position_reports_conflict():
    policy = SafetyPolicy()
    state = WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("W", float("inf"), 0.0, 10000.0, 0.0, 0.0),
            Aircraft("B", 10.0, 0.0, 10000.0, 0.0, 0.0),
        ),
    )
    assert policy.state_has_conflict(state) is True


def test_finite_baseline_unaffected():
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
    assert advisories, "finite conflict scenario must still produce an advisory"
    advisory = advisories[0]
    assert policy.advisory_safe(state, advisory) is True
    room = ControlRoom(policy)
    after = room.apply(
        state,
        advisory,
        Approval(advisory.advisory_hash, "approve", 1002.2, "synthetic-controller"),
        Ack(advisory.advisory_hash, "accepted", 1002.4),
        now=1002.5,
    )
    assert policy.state_has_conflict(after) is False
    assert room.audit.verify(room.audit.events) is True
