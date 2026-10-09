# Review saved decision-trace world links

`python3 audit_replay.py trace.json` reviews an existing native event list.
A demo document with an `audit_events` list is also accepted. With no filename
or a single `-`, the command reads JSON from stdin. It prints a JSON summary:
exit 0 means no replay findings, exit 1 means findings, and exit 2 means the
input could not be read or reviewed.

The existing Airspace Lab decision-trace panel uses the same replay checker
through `decision_trace.review_trace`. Opening a saved trace does not apply
an advisory or change the active world.

## A recorded actuation needs both world identities

For each recorded `simulated_actuation`, replay checks its screening,
approval and acknowledgement order and its link to the screened world.
A clean world link requires both `screen_pass.payload.world_hash` and
`simulated_actuation.payload.before_world_hash` to be nonblank strings
with exactly equal contents.

An absent, null, empty, whitespace-only or non-string value cannot establish
that relationship. It produces a replay finding even when the event-chain
hashes are internally consistent. Missing data is retained in the report;
the checker does not fill it from a later record or another field.

This corrects the previous behavior, which skipped the comparison whenever
either identity was absent or null. Consequently, an older partial trace
that records an actuation without one of these identities now returns
findings rather than a clean result. Keep the original trace and recover
its actual source evidence if available; inserting a guessed identity would
not establish the original world.

## Compatibility and limits

Empty histories, rejection-only histories, unknown event kinds and unfinished
histories without a recorded actuation retain their existing replay meaning.
An unfinished screening or approval sequence is not newly required to contain
a world identity. Existing lifecycle findings still apply.

The checker treats nonblank identity strings as opaque and compares their
exact contents. It does not add a hexadecimal-length rule, trim strings for
comparison or normalize them. This preserves existing nonblank legacy labels.
The unchanged native producer emits its normal SHA-256 world identities.

A clean replay result describes the recorded sequence and these world links.
It does not establish completeness of the saved history, authenticate a real
approval, reconstruct aircraft motion, verify the after-world state or rerun
separation policy. This command performs no actuation or repair.

The focused maintained tests are:

```sh
python3 -m pytest -q tests/test_audit_world_linkage.py tests/test_audit_replay.py tests/test_decision_trace.py
```

The source contribution's receiving evidence distinguishes exact Python API
and captured-stdin checks from any separately performed process, browser or
installed-estate receiving.
