"""A selected alternative still goes through the original native gate."""
import math
from dataclasses import replace

import pytest

from advisory_options import review_advisory_options
from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    ControlRoom,
    GateRejected,
    canonical_bytes,
)


def test_review_exposes_distinct_choices_in_original_priority_without_mutation(state, policy, room):
    room.audit.append("review_fixture", {"world_hash": state.world_hash})
    before = canonical_bytes(state.to_dict()), canonical_bytes(room.audit.events)
    review = review_advisory_options(state, 1000.0, policy)

    assert review.advisories[0] == AdvisoryPlanner(policy).plan(state, 1000.0)[0]
    assert len(review.advisories) > 2
    assert review.candidate_count >= len(review.advisories)
    assert len({a.advisory_hash for a in review.advisories}) == len(review.advisories)
    assert {a.aircraft_id for a in review.advisories} == {"TWR218", "TWR419"}
    assert any(a.set_vy_nm_min < 0 for a in review.advisories)
    assert any(a.set_climb_ft_min != 0 for a in review.advisories)
    for advisory in review.advisories:
        assert ControlRoom(policy).screen_batch(state, [advisory], 1000.0) == [advisory.advisory_hash]
    assert (canonical_bytes(state.to_dict()), canonical_bytes(room.audit.events)) == before
    assert review == review_advisory_options(state, 1000.0, policy)


def test_nondefault_choice_applies_exactly_once_through_original_gate(state, policy):
    review = review_advisory_options(state, 1000.0, policy)
    first, selected = review.advisories[:2]
    assert selected.advisory_hash != first.advisory_hash
    room = ControlRoom(policy)
    approval = Approval(selected.advisory_hash, "approve", 1000.2, "synthetic-reviewer")
    ack = Ack(selected.advisory_hash, "accepted", 1000.4)
    after = room.apply(state, selected, approval, ack, 1000.5)
    target = after.get(selected.aircraft_id)
    assert (target.vx_nm_min, target.vy_nm_min, target.climb_ft_min) == (
        selected.set_vx_nm_min, selected.set_vy_nm_min, selected.set_climb_ft_min,
    )
    assert after.version == state.version + 1
    assert after.observed_at == 1000.5
    assert not policy.state_has_conflict(after)
    assert [e["kind"] for e in room.audit.events] == ["screen_pass", "approval", "ack", "simulated_actuation"]
    assert room.audit.events[-1]["payload"]["advisory_hash"] == selected.advisory_hash
    assert room.audit.verify(room.audit.events)


@pytest.mark.parametrize("mismatch", ["approval", "ack"])
def test_authorization_for_another_option_cannot_apply_the_selection(state, policy, mismatch):
    first, selected = review_advisory_options(state, 1000.0, policy).advisories[:2]
    approval = Approval((first if mismatch == "approval" else selected).advisory_hash, "approve", 1000.2, "synthetic-reviewer")
    ack = Ack((first if mismatch == "ack" else selected).advisory_hash, "accepted", 1000.4)
    room = ControlRoom(policy)
    with pytest.raises(GateRejected, match="human_approval_required" if mismatch == "approval" else "ack_invalid"):
        room.apply(state, selected, approval, ack, 1000.5)
    assert not any(e["kind"] == "simulated_actuation" for e in room.audit.events)
    assert state.version == 1


@pytest.mark.parametrize("now,reason", [
    (999.0, "future_state"), (1011.0, "stale_state"),
    (float("nan"), "invalid_state_time"), (float("inf"), "invalid_state_time"),
    (True, "invalid_state_time"),
])
def test_review_requires_native_freshness_even_before_a_menu_exists(state, now, reason):
    with pytest.raises(GateRejected, match=reason):
        review_advisory_options(state, now)


def test_expired_choice_has_no_application_authority(state, policy):
    selected = review_advisory_options(state, 1000.0, policy).advisories[1]
    room = ControlRoom(policy)
    with pytest.raises(GateRejected, match="expired_advisory"):
        room.apply(state, selected, None, None, 1009.0)
    assert not any(e["kind"] == "simulated_actuation" for e in room.audit.events)


def test_clear_and_unresolvable_worlds_report_complete_empty_menus(state, policy):
    clear = replace(state, aircraft=(state.aircraft[0], replace(state.aircraft[1], altitude_ft=12000.0)))
    empty = review_advisory_options(clear, 1000.0, policy)
    assert empty.advisories == ()
    assert empty.candidate_count == 0
    coincident = replace(state, aircraft=tuple(replace(a, x_nm=0.0) for a in state.aircraft))
    unresolved = review_advisory_options(coincident, 1000.0, policy)
    assert policy.state_has_conflict(coincident)
    assert unresolved.advisories == ()
    assert unresolved.candidate_count > 0


def test_options_keep_original_target_and_numeric_admission_policy(state, policy):
    state = replace(state, aircraft=(*state.aircraft, Aircraft("ZZZ", 100.0, 100.0, 20000.0, 0.5, 0.0)))
    policy = replace(policy, max_speed_nm_min=2.0, max_climb_ft_min=1000.0)
    review = review_advisory_options(state, 1000.0, policy)
    assert review.advisories
    assert review.advisories[0] == AdvisoryPlanner(policy).plan(state, 1000.0)[0]
    assert all(a.aircraft_id != "ZZZ" for a in review.advisories)
    assert all(math.hypot(a.set_vx_nm_min, a.set_vy_nm_min) <= 2.0 for a in review.advisories)
    assert all(abs(a.set_climb_ft_min) <= 1000.0 for a in review.advisories)
