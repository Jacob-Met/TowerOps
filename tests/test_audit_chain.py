"""AuditLog hash-chain integrity: append/verify round-trip and tamper detection.

The audit chain is TowerOps' core receipt mechanism: each event commits to the
previous event's hash (prev_hash -> event_hash, SHA-256 over canonical JSON).
These tests pin that behavior — they assert the current implementation, not a
redesign.
"""

import copy

from towerops import ZERO_HASH, AuditLog


def test_append_verify_round_trip():
    log = AuditLog()
    log.append("screen_pass", {"world_hash": "a" * 64})
    log.append("approval", {"decision": "approve"})
    assert AuditLog.verify(log.events)
    assert log.head == log.events[-1]["event_hash"]


def test_empty_log_verifies():
    assert AuditLog.verify([])
    assert AuditLog().head == ZERO_HASH


def test_tampered_payload_fails_verify():
    log = AuditLog()
    log.append("screen_pass", {"world_hash": "a" * 64})
    events = copy.deepcopy(log.events)
    events[0]["payload"]["world_hash"] = "b" * 64
    assert not AuditLog.verify(events)


def test_reordered_seq_fails_verify():
    log = AuditLog()
    log.append("screen_pass", {"world_hash": "a" * 64})
    log.append("approval", {"decision": "approve"})
    events = copy.deepcopy(log.events)
    events[0], events[1] = events[1], events[0]
    assert not AuditLog.verify(events)


def test_broken_prev_hash_fails_verify():
    log = AuditLog()
    log.append("screen_pass", {"world_hash": "a" * 64})
    log.append("approval", {"decision": "approve"})
    events = copy.deepcopy(log.events)
    events[1]["prev_hash"] = "0" * 64
    assert not AuditLog.verify(events)


def test_forged_event_hash_fails_verify():
    log = AuditLog()
    log.append("screen_pass", {"world_hash": "a" * 64})
    events = copy.deepcopy(log.events)
    events[0]["event_hash"] = "f" * 64
    assert not AuditLog.verify(events)
