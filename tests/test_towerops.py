"""TowerOps issue #1 CI scaffold: minimal deterministic regression tests.

Grounded in the actual behavior of towerops.py (verified locally against
main @ e8fa18e, 2026-10-03). Pure stdlib unittest: the deterministic surface
has no third-party dependencies, so CI installs nothing for these tests.
"""

import copy
import unittest
from dataclasses import replace

from towerops import (
    ZERO_HASH,
    Ack,
    Advisory,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    AuditLog,
    ControlRoom,
    GateRejected,
    SafetyPolicy,
    WorldState,
)


def converging_state() -> WorldState:
    """The same head-on synthetic scenario demo.py uses (see README)."""
    return WorldState(
        version=1,
        observed_at=1000.0,
        aircraft=(
            Aircraft("TWR218", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("TWR419", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )


def screened_advisory(policy: SafetyPolicy, state: WorldState) -> Advisory:
    advisories = AdvisoryPlanner(policy).plan(state, now=1002.0)
    assert advisories, "planner produced no advisory for the converging scenario"
    return advisories[0]


class AuditLogChainTests(unittest.TestCase):
    def test_append_and_verify_chain(self):
        log = AuditLog()
        first = log.append("screen_pass", {"world_hash": "w1"})
        second = log.append("approval", {"decision": "approve"})
        self.assertTrue(AuditLog.verify(log.events))
        self.assertEqual(log.head, second)
        self.assertEqual(log.events[0]["prev_hash"], ZERO_HASH)
        self.assertEqual(log.events[1]["prev_hash"], first)
        self.assertEqual(log.events[1]["seq"], 1)

    def test_tampered_payload_detected(self):
        log = AuditLog()
        log.append("screen_pass", {"world_hash": "w1"})
        log.append("approval", {"decision": "approve"})
        tampered = copy.deepcopy(log.events)
        tampered[1]["payload"] = {"decision": "reject"}
        self.assertFalse(AuditLog.verify(tampered))

    def test_tampered_hash_detected(self):
        log = AuditLog()
        log.append("screen_pass", {"world_hash": "w1"})
        tampered = copy.deepcopy(log.events)
        tampered[0]["event_hash"] = "f" * 64
        self.assertFalse(AuditLog.verify(tampered))

    def test_dropped_event_breaks_continued_chain(self):
        log = AuditLog()
        log.append("screen_pass", {"world_hash": "w1"})
        log.append("approval", {"decision": "approve"})
        truncated = copy.deepcopy(log.events[:1])
        # an audit that claims to continue the pre-drop chain but re-anchors on
        # the truncated head fails the prev linkage check
        continued = copy.deepcopy(log.events)
        continued.append({
            "seq": 2,
            "kind": "ack",
            "payload": {},
            "prev_hash": truncated[-1]["event_hash"],
        })
        self.assertFalse(AuditLog.verify(continued))
        self.assertTrue(AuditLog.verify(truncated))


class ScreenBatchTests(unittest.TestCase):
    def setUp(self):
        self.policy = SafetyPolicy()
        self.state = converging_state()
        self.room = ControlRoom(self.policy)
        self.advisory = screened_advisory(self.policy, self.state)

    def test_stale_state_rejected(self):
        with self.assertRaises(GateRejected) as ctx:
            self.room.screen_batch(self.state, [], now=1020.0)
        self.assertEqual(ctx.exception.reason, "stale_state")

    def test_future_state_rejected(self):
        with self.assertRaises(GateRejected) as ctx:
            self.room.screen_batch(self.state, [], now=900.0)
        self.assertEqual(ctx.exception.reason, "future_state")

    def test_conflicting_recommendations_rejected(self):
        twin = replace(self.advisory, set_vy_nm_min=self.advisory.set_vy_nm_min + 1.0)
        self.assertNotEqual(twin.advisory_hash, self.advisory.advisory_hash)
        with self.assertRaises(GateRejected) as ctx:
            self.room.screen_batch(self.state, [self.advisory, twin], now=1002.5)
        self.assertEqual(ctx.exception.reason, "conflicting_recommendations")

    def test_world_hash_mismatch_rejected(self):
        bad = replace(self.advisory, world_hash="0" * 64)
        with self.assertRaises(GateRejected) as ctx:
            self.room.screen_batch(self.state, [bad], now=1002.5)
        self.assertEqual(ctx.exception.reason, "world_hash_mismatch")

    def test_unsafe_advisory_rejected(self):
        fast = replace(self.advisory, set_vx_nm_min=99.0, set_vy_nm_min=0.0)
        with self.assertRaises(GateRejected) as ctx:
            self.room.screen_batch(self.state, [fast], now=1002.5)
        self.assertEqual(ctx.exception.reason, "unsafe_advisory")

    def test_valid_advisory_passes_and_is_audited(self):
        hashes = self.room.screen_batch(self.state, [self.advisory], now=1002.5)
        self.assertEqual(hashes, [self.advisory.advisory_hash])
        self.assertEqual(self.room.audit.events[-1]["kind"], "screen_pass")
        self.assertTrue(AuditLog.verify(self.room.audit.events))


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.policy = SafetyPolicy()
        self.state = converging_state()
        self.room = ControlRoom(self.policy)
        self.advisory = screened_advisory(self.policy, self.state)
        self.approval = Approval(self.advisory.advisory_hash, "approve", 1002.2, "synthetic-controller")
        self.ack = Ack(self.advisory.advisory_hash, "accepted", 1002.4)

    def test_apply_requires_approval(self):
        with self.assertRaises(GateRejected) as ctx:
            self.room.apply(self.state, self.advisory, None, self.ack, now=1002.5)
        self.assertEqual(ctx.exception.reason, "human_approval_required")

    def test_apply_rejects_non_approve_decision(self):
        rejection = Approval(self.advisory.advisory_hash, "reject", 1002.2, "synthetic-controller")
        with self.assertRaises(GateRejected) as ctx:
            self.room.apply(self.state, self.advisory, rejection, self.ack, now=1002.5)
        self.assertEqual(ctx.exception.reason, "human_approval_required")

    def test_apply_requires_ack(self):
        with self.assertRaises(GateRejected) as ctx:
            self.room.apply(self.state, self.advisory, self.approval, None, now=1002.5)
        self.assertEqual(ctx.exception.reason, "ack_missing")

    def test_apply_happy_path(self):
        new_state = self.room.apply(self.state, self.advisory, self.approval, self.ack, now=1002.5)
        self.assertEqual(new_state.version, self.state.version + 1)
        updated = new_state.get(self.advisory.aircraft_id)
        self.assertEqual(updated.vx_nm_min, self.advisory.set_vx_nm_min)
        self.assertEqual(updated.vy_nm_min, self.advisory.set_vy_nm_min)
        self.assertFalse(self.policy.state_has_conflict(new_state))
        self.assertTrue(AuditLog.verify(self.room.audit.events))
        kinds = [e["kind"] for e in self.room.audit.events]
        for required in ("screen_pass", "approval", "ack", "simulated_actuation"):
            self.assertIn(required, kinds)


class DeterminismTests(unittest.TestCase):
    def test_identical_runs_produce_identical_hashes(self):
        policy = SafetyPolicy()
        first = screened_advisory(policy, converging_state())
        second = screened_advisory(policy, converging_state())
        self.assertEqual(first.advisory_hash, second.advisory_hash)
        self.assertEqual(converging_state().world_hash, converging_state().world_hash)


if __name__ == "__main__":
    unittest.main()
