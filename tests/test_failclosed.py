"""Fail-closed gate contract: every listed hazard is rejected, with no actuation.

Pins the current screening behavior only; no towerops.py behavior changes.
"""
from dataclasses import replace

import pytest

from towerops import (
    Advisory,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    GateRejected,
    WorldState,
)

NOW = 1002.0
# apply() requires approval/ack timestamps <= now, so the actuation instant sits
# slightly after the fixture approval (1002.2) / ack (1002.4) timestamps.
APPLY_NOW = NOW + 0.5


def _rejects(fn, reason):
    with pytest.raises(GateRejected) as exc:
        fn()
    assert exc.value.reason == reason


def test_stale_state_rejected(room, state, advisory):
    stale = WorldState(version=state.version, observed_at=NOW - 11.0, aircraft=state.aircraft)
    _rejects(lambda: room.screen_batch(stale, [advisory], NOW), "stale_state")


def test_future_state_rejected(room, state, advisory):
    future = WorldState(version=state.version, observed_at=NOW + 1.0, aircraft=state.aircraft)
    _rejects(lambda: room.screen_batch(future, [advisory], NOW), "future_state")


def test_conflicting_recommendations_rejected(room, state, advisory):
    other = replace(advisory, set_vy_nm_min=advisory.set_vy_nm_min + 1.0)
    assert other.advisory_hash != advisory.advisory_hash
    _rejects(
        lambda: room.screen_batch(state, [advisory, other], NOW),
        "conflicting_recommendations",
    )


def test_world_hash_mismatch_rejected(room, state, policy):
    moved = WorldState(
        version=state.version,
        observed_at=state.observed_at,
        aircraft=tuple(replace(a, x_nm=a.x_nm + 50.0) for a in state.aircraft),
    )
    assert moved.world_hash != state.world_hash
    stale_advisory = AdvisoryPlanner(policy).plan(state, now=NOW)[0]
    _rejects(lambda: room.screen_batch(moved, [stale_advisory], NOW), "world_hash_mismatch")


def test_expired_advisory_rejected(room, state, advisory):
    expired = replace(advisory, issued_at=NOW - 1.5, expires_at=NOW - 1.0)
    _rejects(lambda: room.screen_batch(state, [expired], NOW), "expired_advisory")


def test_unsafe_advisory_rejected(room):
    a = Aircraft("TWRA", 0.0, 0.0, 10000.0, 0.0, 0.0)
    b = Aircraft("TWRB", 20.0, 0.0, 10000.0, 0.0, 0.0)
    state = WorldState(version=1, observed_at=1000.0, aircraft=(a, b))
    advisory = Advisory(
        aircraft_id="TWRB",
        world_hash=state.world_hash,
        set_vx_nm_min=-6.0,
        set_vy_nm_min=0.0,
        set_climb_ft_min=0.0,
        issued_at=1001.0,
        expires_at=1010.0,
        rationale="test: puts TWRB on a collision course with TWRA",
    )
    _rejects(lambda: room.screen_batch(state, [advisory], NOW), "unsafe_advisory")


def test_apply_without_approval_rejected_no_actuation(room, state, advisory, ack):
    with pytest.raises(GateRejected) as exc:
        room.apply(state, advisory, None, ack, APPLY_NOW)
    assert exc.value.reason == "human_approval_required"
    kinds = [e["kind"] for e in room.audit.events]
    assert "simulated_actuation" not in kinds
    rejects = [e for e in room.audit.events if e["kind"] == "reject"]
    assert rejects and rejects[-1]["payload"]["reason"] == "human_approval_required"
    assert room.audit.verify(room.audit.events)


def test_apply_with_denied_decision_rejected(room, state, advisory, ack):
    denied = Approval(advisory.advisory_hash, "deny", NOW + 0.2, "synthetic-controller")
    with pytest.raises(GateRejected) as exc:
        room.apply(state, advisory, denied, ack, APPLY_NOW)
    assert exc.value.reason == "human_approval_required"


def test_apply_without_ack_rejected(room, state, advisory, approval):
    with pytest.raises(GateRejected) as exc:
        room.apply(state, advisory, approval, None, APPLY_NOW)
    assert exc.value.reason == "ack_missing"
