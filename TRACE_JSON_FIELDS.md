# Unambiguous saved decision traces

Both `python3 audit_replay.py TRACE.json` and the native
`decision_trace.review_trace` adapter reject JSON objects with repeated field
names before replaying the saved history. This applies to the demo wrapper,
each event and payload, and nested metadata. Escaped names that decode to the
same text count as duplicates, even when their values are equal.

Previously, the JSON decoder kept the last value silently. For example, a
document with two `audit_events` fields could replace a recorded failure with
an empty list and report a clean, empty history. A valid chain over the retained
value cannot resolve which of two recorded values was intended.

The audit CLI now returns exit 2, a load diagnostic on stderr, and no summary
for such a file. The adapter raises its existing unreadable-JSON error, which
the existing Airspace Lab worker presents as a failed review. Obtain a fresh
export from the original producer; the reader does not choose one duplicate
value or rewrite the saved file.

Ordinary event lists and demo documents containing `audit_events` retain their
existing behavior. Field names remain case-sensitive. The same name may appear
in different objects, and repeated-looking text inside a string is literal
text. Native integers, floats, signed zero, valid empty histories, unknown
event kinds, chain failures and lifecycle findings retain their existing
meaning. These checks assess saved synthetic evidence, not producer identity
or operational aviation authority.

Run the focused regression tests with:

```bash
python3 -m pytest -q tests/test_trace_duplicate_fields.py
```

The build's existing `prepare-python.mjs` copies these exact native modules
into the Airspace Lab distribution. No additional parser or browser model is
introduced. Original and candidate receiving details are retained under
`docs/receiving/trace-json-6e0637a29ce6/`.
