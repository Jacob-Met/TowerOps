"""A constructed native world retains the aircraft membership it checked."""

import math
from dataclasses import FrozenInstanceError, replace

import pytest

from advisory_options import review_advisory_options
from towerops import Ack, Aircraft, Approval, ControlRoom, WorldState


def _traffic():
    return [
        Aircraft("A", -5.0, 0.0, 10000.0, 1.0, 0.0),
        Aircraft("B", 5.0, 0.0, 10000.0, -1.0, 0.0),
    ]


@pytest.mark.parametrize("edit", ("clear", "reverse", "replace", "duplicate"))
def test_caller_edits_preserve_world_identity_and_native_options(edit):
    source = _traffic()
    members = tuple(source)
    state = WorldState(1, 1000.0, source)
    original = state.to_dict()
    before = review_advisory_options(state, 1002.0)
    assert before.advisories

    if edit == "clear":
        source.clear()
    elif edit == "reverse":
        source.reverse()
    elif edit == "replace":
        source[0] = replace(source[0], x_nm=-100.0)
    else:
        source.append(source[0])

    after = review_advisory_options(state, 1002.0)
    assert after == before
    assert state.to_dict() == original
    assert tuple(state.aircraft) == members


def test_one_shot_source_is_retained_after_duplicate_validation():
    members = tuple(_traffic())
    visited = []

    def supplied():
        for aircraft in members:
            visited.append(aircraft.aircraft_id)
            yield aircraft

    state = WorldState(1, 1000.0, supplied())
    reference = WorldState(1, 1000.0, members)
    assert visited == ["A", "B"]
    assert state.to_dict() == reference.to_dict()
    assert state.world_hash == reference.world_hash
    assert review_advisory_options(state, 1002.0) == review_advisory_options(reference, 1002.0)
    assert visited == ["A", "B"]


@pytest.mark.parametrize("container", (list, tuple, iter))
def test_duplicate_ids_still_refuse_the_materialized_membership(container):
    aircraft = _traffic()[0]
    with pytest.raises(ValueError, match="duplicate aircraft_id"):
        WorldState(1, 1000.0, container([aircraft, aircraft]))


def test_native_tuple_keeps_order_aircraft_objects_and_numeric_values():
    first = Aircraft("z", -0.0, 0, 10000, 1, 0.0)
    second = Aircraft("A", 5, 0.0, 10000.0, -1.0, 0)
    state = WorldState(7, -0.0, (first, second))
    assert type(state.aircraft) is tuple
    assert state.aircraft[0] is first and state.aircraft[1] is second
    assert type(state.aircraft[0].y_nm) is int
    assert type(state.aircraft[1].y_nm) is float
    assert math.copysign(1, state.aircraft[0].x_nm) == -1
    assert math.copysign(1, state.observed_at) == -1
    with pytest.raises(FrozenInstanceError):
        state.aircraft = ()


def test_caller_edit_does_not_rebind_an_already_reviewed_advisory():
    source = _traffic()
    state = WorldState(1, 1000.0, source)
    original = state.to_dict()
    advisory = review_advisory_options(state, 1002.0).advisories[0]
    approval = Approval(advisory.advisory_hash, "approve", 1002.0, "synthetic-controller")
    ack = Ack(advisory.advisory_hash, "accepted", 1002.0)
    source.clear()

    room = ControlRoom()
    updated = room.apply(state, advisory, approval, ack, 1002.0)
    assert state.to_dict() == original
    assert updated.version == state.version + 1
    assert updated.get(advisory.aircraft_id).vx_nm_min == advisory.set_vx_nm_min
    assert updated.get(advisory.aircraft_id).vy_nm_min == advisory.set_vy_nm_min
    assert updated.get(advisory.aircraft_id).climb_ft_min == advisory.set_climb_ft_min
    assert room.audit.verify(room.audit.events)
