"""A candidate must have known numeric state even when there are no peers.

Pairwise separation checks alone cannot validate a singleton. Exercise the
complete gate with matching approval and acknowledgement so a malformed
candidate cannot be admitted or written into the next world state.
"""

from dataclasses import replace

import pytest

from towerops import (
    Ack,
    Advisory,
    Aircraft,
    Approval,
    ControlRoom,
    GateRejected,
    WorldState,
)


def _state(**target_changes):
    target = replace(Aircraft("ALONE", 0.0, 0.0, 10000.0, 0.0, 0.0), **target_changes)
    return WorldState(1, 1000.0, (target,))


def _advisory(state, **changes):
    advisory = Advisory("ALONE", state.world_hash, 0.0, 0.0, 0.0, 1000.0, 1010.0,
                        "synthetic numeric candidate regression")
    return replace(advisory, **changes)


def _apply(room, state, advisory):
    return room.apply(
        state,
        advisory,
        Approval(advisory.advisory_hash, "approve", 1000.2, "synthetic-controller"),
        Ack(advisory.advisory_hash, "accepted", 1000.4),
        now=1000.5,
    )


def _assert_rejected(state, advisory):
    room = ControlRoom()
    before_hash = state.world_hash
    with pytest.raises(GateRejected) as exc:
        _apply(room, state, advisory)
    assert exc.value.reason == "unsafe_advisory"
    assert room.policy.advisory_safe(state, advisory) is False
    assert state.world_hash == before_hash
    assert [event["kind"] for event in room.audit.events] == ["reject"]
    assert room.audit.events[0]["payload"] == {
        "reason": "unsafe_advisory", "advisory_hash": advisory.advisory_hash,
    }
    assert room.audit.verify(room.audit.events)


@pytest.mark.parametrize("field", ["set_vx_nm_min", "set_vy_nm_min", "set_climb_ft_min"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")],
                         ids=["nan", "positive-infinity", "negative-infinity"])
def test_singleton_rejects_nonfinite_commands(field, value):
    state = _state()
    _assert_rejected(state, _advisory(state, **{field: value}))


@pytest.mark.parametrize("field", ["x_nm", "y_nm", "altitude_ft"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")],
                         ids=["nan", "positive-infinity", "negative-infinity"])
def test_singleton_rejects_unknown_retained_position(field, value):
    state = _state(**{field: value})
    _assert_rejected(state, _advisory(state))


@pytest.mark.parametrize("field,value", [
    ("set_vx_nm_min", True), ("set_vy_nm_min", "0"), ("set_climb_ft_min", None),
])
def test_nonnumeric_command_is_a_gate_rejection(field, value):
    state = _state()
    _assert_rejected(state, _advisory(state, **{field: value}))


@pytest.mark.parametrize("field,value", [
    ("x_nm", True), ("y_nm", "0"), ("altitude_ft", None),
])
def test_nonnumeric_retained_position_is_a_gate_rejection(field, value):
    state = _state(**{field: value})
    _assert_rejected(state, _advisory(state))


@pytest.mark.parametrize("vx,vy,climb", [(0, 0, 0), (6.0, 0.0, 3000.0), (0.0, -6.0, -3000.0)])
def test_finite_singleton_commands_including_exact_bounds_still_apply(vx, vy, climb):
    state = _state()
    advisory = _advisory(state, set_vx_nm_min=vx, set_vy_nm_min=vy, set_climb_ft_min=climb)
    room = ControlRoom()
    after = _apply(room, state, advisory)
    assert after.version == state.version + 1
    assert after.observed_at == 1000.5
    assert after.get("ALONE") == replace(state.get("ALONE"), vx_nm_min=vx, vy_nm_min=vy,
                                         climb_ft_min=climb)
    assert [event["kind"] for event in room.audit.events] == [
        "screen_pass", "approval", "ack", "simulated_actuation",
    ]
    assert room.audit.verify(room.audit.events)


@pytest.mark.parametrize("with_peer", [False, True], ids=["singleton", "distant-peer"])
def test_finite_commands_can_replace_unknown_previous_velocity(with_peer):
    # The candidate uses these three new setpoints; old rates are not retained.
    state = _state(vx_nm_min=float("nan"), vy_nm_min=float("inf"), climb_ft_min=-float("inf"))
    if with_peer:
        state = replace(state, aircraft=state.aircraft + (Aircraft("FAR", 100.0, 100.0, 10000.0, 0.0, 0.0),))
    before_hash = state.world_hash
    advisory = _advisory(state, set_vx_nm_min=1.0, set_vy_nm_min=0.0, set_climb_ft_min=-500.0)
    room = ControlRoom()
    after = _apply(room, state, advisory)
    assert after.get("ALONE") == Aircraft("ALONE", 0.0, 0.0, 10000.0, 1.0, 0.0, -500.0)
    assert after.version == state.version + 1
    assert state.world_hash == before_hash
    if with_peer:
        assert after.get("FAR") == state.get("FAR")
    assert room.audit.events[-1]["kind"] == "simulated_actuation"
    assert room.audit.verify(room.audit.events)


def test_finite_command_for_unknown_target_still_rejected():
    state = _state()
    _assert_rejected(state, _advisory(state, aircraft_id="MISSING"))
