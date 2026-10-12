# Review a saved world as a portable document

Run the unchanged native planner with the optional HTML format:

```sh
python3 plan_world.py world.json --html > world-review.html
```

Open `world-review.html` directly in a browser. It is one offline file: no server,
JavaScript, external assets or account is required. The original JSON format
remains the default. All existing stdin, clock and policy arguments still apply:

```sh
python3 plan_world.py - --html --now 125 --horizontal-nm 3 < world.json > review.html
```

This consumes raw WorldState JSON through the existing native admission and
planner. It does not import a saved `towerops.world-plan.v1` report, browser
scenario file or decision trace. See [PLAN_WORLD.md](PLAN_WORLD.md) for the
complete input envelope, synthetic clock and policy rules.

## Compare one alternative at a time

The document presents every individually admitted alternative in the original
native order. Expand a numbered alternative with the pointer, Enter or Space.
Its table places the target flight's current horizontal x/y velocity and climb
beside this proposal's exact setpoints. Units are explicit: nautical miles per
minute and feet per minute. Different numeric setpoints are marked; integer,
floating and signed-zero spellings remain visible exactly as reported.

Each alternative also shows the full native advisory hash, bound world hash,
synthetic issued/expiry times, rationale and complete advisory body. The first
alternative retains the native planner's first-choice priority. The format adds
no score, ranking, trajectory forecast or automatic selection.

The summary distinguishes no conflict, available alternatives and conflict with
no admitted alternative. It includes every recorded conflicting aircraft,
candidate/admitted counts, review clock, world version and observation clock,
original input SHA-256 and native world hash. The complete world snapshot and all
seven policy fields remain available below the alternatives.

These are synthetic research proposals screened independently. They are not a
simultaneous batch, approval or readback. Resolving one target's conflicts can
leave an unrelated pair in conflict. This format neither changes the native
policy nor establishes operational aviation safety.

## Retain the exact native result

**Download exact JSON report** saves precisely the ordinary UTF-8 JSON output for
the same invocation, including indenting, numeric spelling and the final newline.
The document is built from that single serialized result; generating HTML does
not run the planner or screening a second time.

The original world input is identified by its byte SHA-256 but is not embedded
as a separate file. The result contains the native sorted world representation.
Body hashes are identities, not a signature, external producer authentication,
renewed execution or approval.

The underlying JSON can also be inspected in a native disclosure at the end.
All text is displayed literally. The renderer is an internal presentation helper
for the trusted, freshly produced CLI result, not an admission API for arbitrary
saved reports.

## Keyboard, narrow screens and output failures

Report-section links and every disclosure are keyboard accessible. Wide tables
scroll in their own focusable regions; use the arrow keys after focusing a table.
The complete page remains readable on a narrow screen. Native browser printing
is available; the document adds no PDF generator or PDF-validity promise.

The CLI still writes stdout and retains the original exit codes. Invalid input
or native-gate refusal produces no stdout document. An output-device failure
can leave partial bytes: check the exit code before accepting a report.

Shell redirection belongs to the caller. Always choose a different output path
from the input: a shell can truncate an input before the Python program starts.

## Verification

```sh
python3 -m unittest discover -s tests -p test_world_plan_html.py -v
```

The focused suite checks actual CLI output against the native JSON, every
alternative/current-flight binding, both empty outcomes, clock/policy/stdin
behavior, literal content and original refusal/output-failure boundaries.
