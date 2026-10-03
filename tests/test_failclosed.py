"""Fail-closed gate contract: screen_batch rejects bad input and apply()
requires explicit human approval.

These tests pin the gate behavior — the rejection reasons, not happy paths.
Every rejection must also leave an audit trail: the audit log keeps appending
even when the gate refuses, and the chain must still verify afterwards.
"""

from dataclasses import replace

import pytest

from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    AuditLog,
    ControlRoom,
    GateRejected,
    SafetyPolicy,
    WorldState,
)

NOW = 1002.0


def make_state(observed_at=1000.0):
    return WorldState(
        version=1,
        observed_at=observed_at,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )


def make_advisory(state, now=NOW):
    planner = AdvisoryPlanner(SafetyPolicy())
    advisories = planner.plan(state, now=now)
    assert advisories, "planner produced no advisory"
    return advisories[0]


def assert_rejected(room, reason, fn):
    with pytest.raises(GateRejected) as excinfo:
        fn()
    assert excinfo.value.reason == reason
    assert AuditLog.verify(room.audit.events)


def test_rejects_stale_state():
    room = ControlRoom()
    state = make_state(observed_at=1000.0)
    advisory = make_advisory(state)
    assert_rejected(
        room,
        "stale_state",
        lambda: room.screen_batch(state, [advisory], now=1020.0),  # age 20s > 10s limit
    )


def test_rejects_future_state():
    room = ControlRoom()
    state = make_state(observed_at=1005.0)
    advisory = make_advisory(make_state())
    assert_rejected(
        room,
        "future_state",
        lambda: room.screen_batch(state, [advisory], now=1000.0),
    )


def test_rejects_conflicting_recommendations():
    room = ControlRoom()
    state = make_state()
    first = make_advisory(state)
    second = replace(first, rationale="a different proposal")
    assert first.advisory_hash != second.advisory_hash
    assert_rejected(
        room,
        "conflicting_recommendations",
        lambda: room.screen_batch(state, [first, second], now=NOW),
    )


def test_rejects_world_hash_mismatch():
    room = ControlRoom()
    state = make_state()
    advisory = make_advisory(state)
    stale = replace(advisory, world_hash="f" * 64)
    assert_rejected(
        room,
        "world_hash_mismatch",
        lambda: room.screen_batch(state, [stale], now=NOW),
    )


def test_rejects_expired_advisory():
    room = ControlRoom()
    state = make_state()
    advisory = make_advisory(state)  # issued 1002.0, expires 1010.0
    expired = replace(advisory, expires_at=1005.0)
    assert_rejected(
        room,
        "expired_advisory",
        lambda: room.screen_batch(state, [expired], now=1006.0),
    )


def test_rejects_unsafe_advisory():
    room = ControlRoom()
    state = make_state()
    advisory = make_advisory(state)
    # 10 nm/min far exceeds the 6 nm/min safety-policy speed limit.
    too_fast = replace(advisory, set_vx_nm_min=10.0, set_vy_nm_min=0.0)
    assert_rejected(
        room,
        "unsafe_advisory",
        lambda: room.screen_batch(state, [too_fast], now=NOW),
    )


def test_apply_without_approval_performs_no_actuation_but_audits():
    room = ControlRoom()
    state = make_state()
    advisory = make_advisory(state)
    ack = Ack(advisory.advisory_hash, "accepted", 1002.4)
    with pytest.raises(GateRejected) as excinfo:
        room.apply(state, advisory, None, ack, now=1002.5)
    assert excinfo.value.reason == "human_approval_required"
    # No actuation recorded ...
    assert not any(e["kind"] == "simulated_actuation" for e in room.audit.events)
    # ... but the rejection itself is on the audit trail, chain intact.
    assert any(
        e["kind"] == "reject" and e["payload"].get("reason") == "human_approval_required"
        for e in room.audit.events
    )
    assert AuditLog.verify(room.audit.events)
