# Python audit payload snapshots

`AuditLog.append(kind, payload)` captures an independent payload value before
hashing and recording the event. A caller can then reuse its dictionary and
nested mutable containers without changing an event already recorded.

This matters for the ordinary `ControlRoom.screen_batch()` result. The method
returns its list of admitted advisory hashes and also records those hashes in
a `screen_pass` event. Previously, changing the returned list also changed the
recorded event. Even a completed approval, acknowledgement and simulated
actuation then failed saved audit verification while retaining the old head
hash. The Python logger now keeps its own payload snapshot.

```python
from towerops import AuditLog

payload = {"notes": ["recorded"]}
audit = AuditLog()
audit.append("observation", payload)

payload["notes"].append("for a later event")
assert audit.events[0]["payload"] == {"notes": ["recorded"]}
assert AuditLog.verify(audit.events)
```

## Preserved behavior

Each append keeps the existing sequence, kind, payload, previous-hash and
event-hash fields. Canonical JSON encoding and hash construction are unchanged.
Ordinary Python payload values retain their native scalar and container types,
including tuples and the distinction between integer and floating-point values.
Capturing a payload does not edit the caller's input. Reusing one payload for
several appends records the value supplied for each append independently.

Preparation and serialization finish before publication. A failed append adds
no event and consumes no sequence. The public `events` collection remains
mutable: directly changing a recorded payload still causes verification to
fail. Standard Python deep-copy semantics apply; this change adds no
concurrent-append synchronization or persistence mechanism.

## Focused verification

Run the caller-reuse regressions and existing audit/replay checks with:

```sh
python -B -m pytest -q tests/test_audit_payload_snapshot.py tests/test_audit_chain.py tests/test_audit_replay.py tests/test_audit_world_linkage.py
```

The new regressions exercise outer and nested input changes, tuple-reached
mutable values, repeated payload reuse, unchanged canonical hashes and native
types, failed serialization, and deliberate recorded-log tampering. The actual
planner, screening, approval, acknowledgement and simulated-actuation course
is saved after the caller clears its returned list, then read by the unchanged
`audit_replay.py` CLI. These are synthetic Python API and saved-file checks.

The browser TypeScript audit implementation, policy, gate, planner, actuation
and replay readers are unchanged.
