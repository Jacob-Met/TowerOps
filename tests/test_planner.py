"""Planner maneuver coverage: vertical-convergence conflicts resolve via climb.

Pins the demonstrated gap: the planner previously varied lateral vy only, so a
pure vertical-convergence conflict (same x/y, climbing into a descent path)
yielded no advisory even though a safe climb adjustment exists. The planner now
also tries climb and speed variants in a fixed deterministic order, with
lateral-only variants first to preserve the historical resolution preference.
"""

import math
from dataclasses import asdict

from towerops import (
    Ack,
    Advisory,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    AuditLog,
    ControlRoom,
    SafetyPolicy,
    WorldState,
)


def _vertical_convergence_state() -> WorldState:
    # TWR101 climbing through TWR202's descent path; same x/y so no lateral
    # vy change can open horizontal separation.
    return WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR101", 0.0, 0.0, 10000.0, 0.0, 0.0, 2000.0),
            Aircraft("TWR202", 0.0, 0.0, 12000.0, 0.0, 0.0, -2000.0),
        ),
    )


def _demo_state() -> WorldState:
    return WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )


def test_vertical_convergence_resolves_with_climb_adjustment():
    policy = SafetyPolicy()
    state = _vertical_convergence_state()
    assert policy.state_has_conflict(state)
    planner = AdvisoryPlanner(policy)
    advisories = planner.plan(state, now=1002.0)
    assert len(advisories) == 1
    advisory = advisories[0]
    assert advisory.aircraft_id == "TWR202"
    assert policy.advisory_safe(state, advisory)
    # Resolution must come from the climb axis: vy unchanged from target.
    target = state.get("TWR202")
    assert advisory.set_vy_nm_min == target.vy_nm_min
    assert advisory.set_climb_ft_min != target.climb_ft_min
    assert abs(advisory.set_climb_ft_min) <= policy.max_climb_ft_min


def test_vertical_convergence_applies_end_to_end():
    policy = SafetyPolicy()
    state = _vertical_convergence_state()
    planner = AdvisoryPlanner(policy)
    advisory = planner.plan(state, now=1002.0)[0]
    room = ControlRoom(policy)
    approval = Approval(advisory.advisory_hash, "approve", 1002.2, "synthetic-controller")
    ack = Ack(advisory.advisory_hash, "accepted", 1002.4)
    after = room.apply(state, advisory, approval, ack, now=1002.5)
    assert not policy.state_has_conflict(after)
    assert AuditLog.verify(room.audit.events)


def test_demo_scenario_still_resolves_laterally_first():
    # Lateral-only variants keep priority: the demo scenario must resolve with
    # the same lateral advisory as before the maneuver expansion.
    policy = SafetyPolicy()
    planner = AdvisoryPlanner(policy)
    advisory = planner.plan(_demo_state(), now=1002.0)[0]
    assert advisory.aircraft_id == "TWR419"
    assert advisory.set_vy_nm_min == 2.0
    assert advisory.set_vx_nm_min == -1.0
    assert advisory.set_climb_ft_min == 0.0


def test_planner_is_deterministic():
    policy = SafetyPolicy()
    planner = AdvisoryPlanner(policy)
    first = planner.plan(_vertical_convergence_state(), now=1002.0)[0]
    second = planner.plan(_vertical_convergence_state(), now=1002.0)[0]
    assert first.advisory_hash == second.advisory_hash
    assert asdict(first) == asdict(second)


def test_no_conflict_still_yields_no_advisory():
    policy = SafetyPolicy()
    state = WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR1", -50.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR2", 50.0, 0.0, 12000.0, -1.0, 0.0),
        ),
    )
    assert not policy.state_has_conflict(state)
    assert AdvisoryPlanner(policy).plan(state, now=1002.0) == []

def _issue4_near_speed_limit_state() -> WorldState:
    # The target crosses the other aircraft's track near the speed cap.
    return WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR101", -15.0, 0.0, 10000.0, 0.0, 0.0),
            Aircraft("TWR202", 0.0, -3.0, 10000.0, -5.90, 0.0),
        ),
    )


def test_issue4_near_limit_lateral_menu_resolves_within_speed_budget():
    policy = SafetyPolicy()
    state = _issue4_near_speed_limit_state()
    assert policy.state_has_conflict(state)
    target = state.get("TWR202")
    for vy in (2.0, -2.0, 3.0, -3.0, 0.0):
        old = Advisory(target.aircraft_id, state.world_hash, target.vx_nm_min, vy,
                       target.climb_ft_min, 1002.0, 1010.0, "baseline fixed menu")
        assert not policy.advisory_safe(state, old)
    advisories = AdvisoryPlanner(policy).plan(state, now=1002.0)
    assert advisories
    for advisory in advisories:
        assert policy.advisory_safe(state, advisory)
        assert math.hypot(advisory.set_vx_nm_min, advisory.set_vy_nm_min) <= 6.0
    assert advisories[0].set_vx_nm_min == -5.90
    assert advisories[0].set_climb_ft_min == target.climb_ft_min
    assert advisories[0].set_vy_nm_min < 0.0


def test_lateral_candidate_order_is_budgeted_and_deduplicated():
    policy = SafetyPolicy()
    target = _issue4_near_speed_limit_state().get("TWR202")
    candidates = list(AdvisoryPlanner(policy)._maneuver_candidates(target))
    vy_max = math.sqrt(policy.max_speed_nm_min ** 2 - target.vx_nm_min ** 2)
    while math.hypot(target.vx_nm_min, vy_max) > policy.max_speed_nm_min:
        vy_max = math.nextafter(vy_max, 0.0)
    expected = (vy_max, -vy_max, 0.0, vy_max / 2.0, -vy_max / 2.0,
                vy_max / 4.0, -vy_max / 4.0)
    lateral = candidates[:len(expected)]
    assert len(lateral) == len(expected)
    assert all(math.isclose(c[1], v, rel_tol=0.0, abs_tol=1e-12)
               for c, v in zip(lateral, expected))
    assert all(c[0] == target.vx_nm_min and c[2] == target.climb_ft_min
               for c in lateral)
    assert all(math.hypot(c[0], c[1]) <= policy.max_speed_nm_min
               for c in lateral)
