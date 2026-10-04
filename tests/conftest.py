"""Shared fixtures: the demo's two-aircraft conflict scenario as deterministic test input.

Mirrors demo.py so the tests pin the behavior the README advertises.
"""
import pytest

from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    ControlRoom,
    SafetyPolicy,
    WorldState,
)

NOW = 1002.0
OBSERVED_AT = 1000.0


def make_conflict_state() -> WorldState:
    """Two synthetic aircraft on a converging head-on path (same as demo.py)."""
    return WorldState(
        version=1,
        observed_at=OBSERVED_AT,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )


@pytest.fixture
def policy() -> SafetyPolicy:
    return SafetyPolicy()


@pytest.fixture
def state() -> WorldState:
    return make_conflict_state()


@pytest.fixture
def room(policy) -> ControlRoom:
    return ControlRoom(policy)


@pytest.fixture
def advisory(state, policy):
    advisories = AdvisoryPlanner(policy).plan(state, now=NOW)
    assert advisories, "planner produced no advisory for the conflict fixture"
    return advisories[0]


@pytest.fixture
def approval(advisory) -> Approval:
    return Approval(advisory.advisory_hash, "approve", NOW + 0.2, "synthetic-controller")


@pytest.fixture
def ack(advisory) -> Ack:
    return Ack(advisory.advisory_hash, "accepted", NOW + 0.4)
