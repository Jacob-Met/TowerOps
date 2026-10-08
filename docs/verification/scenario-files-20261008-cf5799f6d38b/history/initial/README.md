# TowerOps local scenario files — native receiving, 2026-10-08

The seven-file browser change preserves a reusable scenario: traffic, all policy parameters, simulation clock, time scale and selected aircraft. A selected local file is reviewed before an explicit apply. Applying it clears obsolete proposals, approvals and audit state and leaves traffic paused; the real planner must run again.

## Source and reproduced product gap

| Item | Exact value |
| --- | --- |
| Repository | `Jacob-Met/TowerOps` |
| Parent commit | `d99d238f7da62d74852e07fc90da406f87c2d371` |
| Parent tree | `f870d8a9d7d7af73035a2ab7465f757f8d19138f` |
| Qualified seven-file source tree | `9d4d1320fcd59b7a635adb6439ca512650e2df71` |
| Full candidate file inventory | 99 tracked files; 92 inherited blobs unchanged |
| Source-manifest SHA256 | `6bd45f0fb10763c300ea86ab64028b4cd03f3a5708ffabe1fb0622cfd8b41bbd` |
| Native runtime | macOS arm64; Node 26.3.0; Chrome 154.0.8037.98; Puppeteer 25.12.0 |
| Exact locked browser dependencies | TypeScript 5.7.3; Vite 8.3.3; Vitest 4.1.11; Pyodide 0.27.7 |

`baseline/receipt.json` records the unchanged parent in real Chrome. Two stationary synthetic tracks are 7 NM apart. At a 9 NM horizontal separation policy they produce one conflict. After exporting the existing raw world, changing the current policy to 3 NM and loading the same world bytes, the parent reports zero conflicts. Restoring 9 NM restores the conflict. The original world format omits policy and clock state; the original UI has no reusable scenario file action.

The Notion seed references in `source-observation.json` are discovery context, not acceptance evidence or a current authority claim. The current browser gap was reproduced independently. This change does not modify the historical Python demo named by those seeds. Parent ownership was checked through the existing HAMON coordination thread; root announced this scope in issue #140, comment 6056849222, after the preceding owner's completed handoff.

## Behavior and validation

The scenario schema has exactly `format`, `version`, `world`, `policy`, `now`, `time_scale`, and `selected_aircraft_id`. The format is `towerops.airspace-scenario`, version 1. Unknown root, world, aircraft or policy keys are refused, including approval-shaped fields. Files are bounded at 256 KiB of UTF-8. World validation reuses the native parser and adds the scenario format's canonical callsign, selected-flight membership and safe world-version checks. Editable policy values and time scale follow the current controls' bounds and steps; the four policy parameters without controls must equal their native defaults. Review shows all seven policy values.

Selecting a file does not change current simulation state. Cancel, read error, malformed input and a stale asynchronous file read leave the current world and any current approval unchanged. Review becomes stale when relevant world, policy, clock, rate, selection, proposal, approval, audit, solver, traffic or track-edit context changes. Only the explicit Load reviewed scenario action applies the complete validated object. Applying it replaces the traffic/policy/clock/rate/selection together, clears old planner and audit state, and pauses traffic. Imported names and file names are literal text.

Numbers are serialized as JSON numbers with finite-value validation and signed-zero preservation. This keeps the clock and native world values usable without executing imported HTML. There is no upload, live traffic access, automatic import, or restored approval. The existing raw WorldState textarea workflow and the existing selected-flight preview/apply behavior remain available.

| Qualification | Result |
| --- | --- |
| Exact parent unit suite | 37 passed |
| Candidate Vitest suite | 105 passed: 68 new and 37 inherited |
| TypeScript and Vite production build | Passed |
| Native Chrome receiving | 7 of 7 groups passed |
| Candidate source before/after receiving | All 99 tracked paths and Git blobs matched the frozen tree |
| Uncaught application errors / external application requests | 0 / 0 |

The browser groups exercise a real download and real file chooser; review/cancel/apply and finite numeric roundtrip; two actual CPython planner → approve → readback cycles with a new trace after applying the file; malformed inputs preserving an existing approval; changed context and out-of-order file reads; the inherited raw-world and track-edit interactions; and keyboard operation at a 390-pixel viewport with a literal HTML-like filename. `browser/receipt.json` is the complete request, source and runtime record. The screenshots show the actual scenario panel at desktop and phone sizes. Files under `examples/` are the actual downloaded bytes, copied without rewriting.

All HTTP application traffic was directed to the isolated local Vite server, using a separate disposable browser profile. A separate loopback proxy refused any nonlocal browser background request and did not forward it. These background refusals are retained separately in the receipt. No live provider, Canvas account, production browser profile, traffic feed, installed estate deployment or user adoption is qualified.

## Reproduce from immutable source

Use an authorized Git checkout containing the parent commit and a supported Node environment. In a fresh checkout, apply the exact seven-file patch from this packet:

```sh
git clone https://github.com/Jacob-Met/TowerOps.git scenario-replay
cd scenario-replay
git checkout d99d238f7da62d74852e07fc90da406f87c2d371
git apply --index /absolute/path/to/this/packet/candidate.patch
git write-tree
```

The resulting tree must be `9d4d1320fcd59b7a635adb6439ca512650e2df71`. The patch includes product code, its tests and its README; publication evidence is outside that qualified source tree. The final published repository tree will include this packet as an additional documentation delta. `source-manifest.json` also specifies every file's SHA256, byte count and Git blob for source-only receiving copies.

```sh
cd web/airspace
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run build
```

The reference run installed exactly the existing lockfile from a pre-existing local npm cache with `--offline`; dependencies and the lockfile were not changed. Reproduction may obtain those locked dependencies normally. No captured `node_modules`, generated production bundle, Git object database, test fixture directory or browser profile is part of this packet.

Install or use Puppeteer 25.12.0 in a separate receiving directory and provide its `node_modules` through `NODE_PATH`. Set `CHROME_PATH` to the Chrome executable when the native macOS default does not apply. Then run the unchanged current receiving script against the fresh staged source checkout and a new output directory:

```sh
NODE_PATH=/absolute/path/to/receiving/node_modules \
CHROME_PATH=/absolute/path/to/chrome \
node /absolute/path/to/this/packet/scripts/scenario-browser-receiving.mjs \
  /absolute/path/to/scenario-replay /absolute/path/to/new-receiving-output
```

The script starts its own Vite listener, deny proxy and browser process, supplies only synthetic traffic, regenerates its input fixtures, and closes its own processes. The source collector reads the staged Git index. Do not overwrite the reference receipt or reuse its browser profile. To replay the parent counterexample, run `scripts/baseline-repro.mjs` against a separate unmodified parent checkout; that original script uses the macOS Chrome executable recorded in its source.

## Preserved receiving failures

Receiving failures were kept instead of being silently replaced. They did not cause a product or dependency change.

1. The first candidate run passed the download roundtrip and then timed out loading Pyodide under Puppeteer request interception. An identical interception configuration stalled the unchanged parent after `pyodide.asm.js`, before the WebAssembly and package requests. The paired diagnosis scripts and receipts are under `history/r1/`. Removing interception on the same parent allowed the actual CPython planner to initialize. The final receiver uses passive request observation and a denying loopback proxy. This is an empirical limitation of that receiving configuration, not a claim of a general Puppeteer defect. Puppeteer's request-interception API documentation is https://pptr.dev/api/puppeteer.page.setrequestinterception.
2. The second candidate run passed all seven product groups, then its source collector failed with EISDIR because a local dependency symlink appeared in an untracked-file glob. The collector now reads only the staged Git file list. `history/r2/` retains the original script and failure receipt. The frozen seven-file product source did not change.

`process-observations.json` distinguishes captured raw process results from the earlier parent unit/build summary, whose remote process session expired before a later raw-output read. It does not reconstruct an absent raw log. The final build and browser runs have complete preserved results and successful exits.

## Packet contents

`source-manifest.json`, `candidate.patch` and the build/runtime receipts pin the complete candidate. `scripts/` holds the two primary replay programs. `baseline/` holds the actual parent control. `browser/` holds final receiving and screenshots. `history/` records the failed receiving configurations and paired controls. `examples/` holds the two real downloads. The publication manifest records exact bytes and hashes without shipping any captured dependency tree.
