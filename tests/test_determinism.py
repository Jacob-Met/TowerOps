"""Determinism: two runs of the demo scenario produce an identical world_hash
and an identical audit chain.

TowerOps advertises deterministic simulation. These tests pin the current
behavior: the planner, gate, and actuation take no wall-clock, random, or
unordered-iteration input, so two fresh runs must agree exactly.
"""

from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    AuditLog,
    ControlRoom,
    SafetyPolicy,
    WorldState,
)


def run_demo_scenario():
    """One full pass of the demo scenario; returns (final_state, audit events)."""
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
    assert advisories, "planner produced no advisory for the demo scenario"
    advisory = advisories[0]
    approval = Approval(advisory.advisory_hash, "approve", 1002.2, "synthetic-controller")
    ack = Ack(advisory.advisory_hash, "accepted", 1002.4)
    room = ControlRoom(policy)
    after = room.apply(state, advisory, approval, ack, now=1002.5)
    return after, room.audit.events


def test_two_runs_agree_on_world_hash():
    after1, _ = run_demo_scenario()
    after2, _ = run_demo_scenario()
    assert after1.world_hash == after2.world_hash


def test_two_runs_agree_on_audit_chain():
    _, events1 = run_demo_scenario()
    _, events2 = run_demo_scenario()
    chain1 = [e["event_hash"] for e in events1]
    chain2 = [e["event_hash"] for e in events2]
    assert chain1 == chain2
    assert AuditLog.verify(events1)


def test_demo_resolves_conflict():
    policy = SafetyPolicy()
    before = WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    assert policy.state_has_conflict(before)
    after, _ = run_demo_scenario()
    assert not policy.state_has_conflict(after)
    assert after.world_hash != before.world_hash
