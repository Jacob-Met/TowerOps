# TowerOps / Airspace Lab

An interactive 2D traffic-management workbench, not a recorded animation. Add flights from your own callsign, position, flight level, bearing, speed and climb; or edit/import a `WorldState` JSON. Traffic advances from those velocity vectors. You can add/perturb/remove tracks, tune the horizontal/vertical separation envelope and look-ahead, run repeated planner passes, then approve and read back a world-bound setpoint before simulated actuation. A hash-chained audit trace can be verified in the page.

## Real TowerOps logic

The browser hosts a faithful TypeScript port of the Python `SafetyPolicy`, `AdvisoryPlanner`, `ControlRoom` safety gates, canonical world/advisory hashes and SHA-256 audit log. `tools/generate_airspace_reference.py` executes the original Python classes to maintain four reference scenarios; Vitest checks the browser port against those outputs. Additional tests construct visitor-authored worlds and run them through conflict timing, advisory search, approval, readback, actuation and audit verification. No prerecorded output drives the UI, and there is no model, network, live aircraft or external data call.

## Review a saved world from the terminal

`python3 plan_world.py world.json` inspects raw synthetic WorldState JSON with the
existing native planner and returns every individually screened alternative.
It preserves the saved input and performs no actuation. See [PLAN_WORLD.md](PLAN_WORLD.md)
for file/stdin use, clock and policy settings, complete results, and refusal limits.

For a saved synthetic Explorer result, select its before or after world explicitly
and pass it to the same planner. In Bash:

```bash
set -o pipefail
python3 explorer_world.py approved-explorer.json --phase before | python3 plan_world.py -
python3 explorer_world.py approved-explorer.json --phase after | python3 plan_world.py -
```

Replay recomputes the local synthetic fixture; the planner results remain
`proposal_only: true`. See [EXPLORER_WORLD.md](EXPLORER_WORLD.md) for creating
an export, complete replay validation and refusal statuses.

`python3 compare_plans.py left.plan.json right.plan.json` compares saved policy
experiments for the same exact native world and review clock, showing policy
changes and complete advisory membership/order without planning again.
See [COMPARE_PLANS.md](COMPARE_PLANS.md) for exact identities, file limits and JSON output.

## Edit one aircraft in a saved synthetic world

Create an explicit authored alternative with
`python3 edit_world.py before.json --aircraft ALPHA --x-nm 4.5 --out after.json`.
The new file preserves other aircraft and the recorded observation time, while
using the native one-step version increment. It does not plan or apply an advisory.
See [EDIT_WORLD.md](EDIT_WORLD.md) for all six field options, exact identity and
representation rules, and new-file output behavior.

## Launch the installed Synthetic Explorer on the ThinkPad

The [fixed ThinkPad installation](docs/EXPLORER_INSTALL.md) provides
`towerops-explorer --port 8765` after one explicit, reviewed adoption of the
accepted source. Open its printed loopback address to replay a saved synthetic
export and choose **Explain this mismatch**. The command runs in the foreground;
Ctrl+C stops it. Existing commands and prior versions are preserved by refusal
when the target command or TowerOps namespace is already occupied.

## Explain a saved Explorer result

To see which saved fields differ from a locally reconstructed synthetic scenario,
add `--explain` to the replay command:

```bash
python3 explorer.py run approved > approved-explorer.json
python3 explorer.py replay approved-explorer.json --explain
```

The JSON result retains the ordinary replay summary and adds typed differences
with JSON Pointer paths. These rows describe literal field differences in the
local synthetic reproduction. It reports up to 32 differences and indicates
when more were observed. Exit 0 means a match, exit 1 means a mismatch, and exit 2
means invalid input or a read, replay or output error. The input file is preserved.
See [EXPLORER.md](EXPLORER.md) for limits and complete output, or try the
[retained one-field mismatch example](docs/qualification/explorer-replay-explain-anvil-d3745/independent/README.md).

## Review a saved audit trace from the terminal

The audit checker reviews a saved hash chain, recorded lifecycle and world links
without changing the trace or applying an advisory:

```bash
python3 audit_replay.py trace.json
python3 audit_replay.py - < trace.json
python3 audit_replay.py --help
```

A completed review emits a JSON summary; `--help` prints usage and exits 0.
For a review, exit 0 means no findings, exit 1 means findings, and exit 2 means
invalid arguments or an input, review or output error.
Supply one source at most; omit it or use `-` for stdin.
See [AUDIT_REPLAY.md](AUDIT_REPLAY.md) for accepted trace formats,
dash-prefixed filenames, output-failure behavior and the limits of the review.

## Read a compact recorded plan summary

For an existing `towerops.world-plan.v1` report, inspect its recorded status,
clock, counts and all seven policy values without planning again:

```bash
python3 review_saved_plan.py after.plan.json
python3 review_saved_plan.py after.plan.json --json
```

The recorded candidate count stays distinct from saved alternatives. No option
is selected or applied; internal body-hash consistency does not establish
freshness, menu completeness or safety approval. See
[REVIEW_SAVED_PLAN.md](REVIEW_SAVED_PLAN.md) for input and output limits.

## Match a saved plan to an exact original world

`python3 check_plan_source.py saved.plan.json source-world.json` compares an
existing recorded plan with an explicitly selected raw synthetic world, without
rerunning the planner or changing traffic. It distinguishes exact original
bytes, the same native world with different serialized bytes, and genuinely
different world content. Add `--json` for a structured provenance check.
See [CHECK_PLAN_SOURCE.md](CHECK_PLAN_SOURCE.md) for statuses, exit codes and
the limits of this non-authenticating comparison.

## Verify

From the repository root:

```bash
py -3 tools/generate_airspace_reference.py --check
cd web/airspace
npm ci
npm test
npm run build
```

Optional Raider browser acceptance and desktop/phone captures:

```bash
py -3 tools/capture_airspace.py
```

The app uses synthetic or visitor-provided state only. It is a research simulation, not operational air-traffic-control software or aviation assurance. Approval/readback controls are fixtures, not real authority.