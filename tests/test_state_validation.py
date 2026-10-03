"""WorldState structural validation: aircraft ids must be unique.

Regression tests for a demonstrated gate bypass: with duplicate aircraft ids
in one WorldState, `SafetyPolicy.advisory_safe` skipped the id-twin
(`other.aircraft_id != candidate.aircraft_id`), so an advisory steering an
aircraft into its twin passed the safety gate and was actuated. Every id-keyed
operation (get, replace_aircraft, advisory_safe's target exclusion) assumes
uniqueness, so malformed states are rejected at construction.
"""

import pytest

from towerops import Aircraft, WorldState


def test_duplicate_aircraft_ids_rejected():
    with pytest.raises(ValueError, match="duplicate aircraft_id"):
        WorldState(
            version=1,
            observed_at=1000.0,
            aircraft=(
                Aircraft("DUP", 0.0, 0.0, 10000.0, 0.0, 0.0),
                Aircraft("DUP", 10.0, 0.0, 10000.0, 0.0, 0.0),
            ),
        )


def test_duplicate_ids_among_many_rejected():
    with pytest.raises(ValueError, match="duplicate aircraft_id"):
        WorldState(
            version=1,
            observed_at=1000.0,
            aircraft=(
                Aircraft("A", 0.0, 0.0, 10000.0, 0.0, 0.0),
                Aircraft("B", 5.0, 0.0, 10000.0, 0.0, 0.0),
                Aircraft("A", 9.0, 0.0, 10000.0, 0.0, 0.0),
            ),
        )


def test_unique_ids_accepted():
    state = WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    assert state.get("TWR218").x_nm == -5.0


def test_empty_state_accepted():
    state = WorldState(version=1, observed_at=1000.0, aircraft=())
    assert state.aircraft == ()
