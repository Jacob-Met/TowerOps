# PR50 main composition: native and build receiving

## Result and exact boundary

The frozen scenario/alternatives contribution composes with the named PR50 main without application edits. The received staged tree is `8c11186b1a3f6391879fb0aef14738487f09dc2a`: 589 tracked leaves over detached main `53aa5048b6585aa08592d5513cfcf555a8bba018` (base tree `fc29ac4a02c151ba66ca37c029ff74d968662d58`).

All 335 contribution paths from root's qualified tree `cde965df1dc4a18a94443c386e48686dd6280073` remain exact, and all 254 unrelated leaves from main 53 remain exact. The delta from that 579-leaf qualified publication is exactly PR50's ten added files and root README modification, recorded with old/new Git identities in `exact-pr50-delta.json`. No Airspace application, Python worker/helper, workflow, package lock, or scenario/alternatives algorithm changes were introduced.

At 2026-10-08 14:55 UTC, the first native/build invocation on this composition returned:

| Check | Result |
| --- | --- |
| Normal native pytest | 145 passed, 1 skipped; 146 collected, zero failures/errors |
| Normal Ruff 0.16.10 | Exit 0 |
| Real-source Python reference check | Exit 0; four reference scenarios match |
| Normal production build | Exit 0 |
| Built-asset receiving comparison | All 16 names, byte counts and SHA256s exactly match root's already received build |
| Frozen source readback | All 589 paths, bytes, modes and Git blobs match before and after execution |

The skip is the inherited `WorldPlanProcessReceiving.test_output_io_failure_does_not_claim_a_successful_review`, which requires `/dev/full`; that device is absent on this Mac. The separate inherited independent test `test_generated_report_is_not_raw_input_and_closed_pipe_failure_is_clean` passes, including its actual closed-stdout-pipe refusal. The platform skip remains explicit in the unmodified JUnit and stdout; no replacement predicate was authored here.

## Receiving scope

This is an independent integration receiving layer. It runs the existing native test suite, including PR50's public file/stdin CLI and independent receiving cases, without changing test predicates or product source. It does not relabel those inherited predicates as newly authored tests.

Frontend and browser tests were deliberately not rerun: the complete source closure relevant to the previously qualified application remains exact, and a fresh ordinary production build yields all 16 identical assets. The earlier root/browser packets remain separate evidence with their original source boundaries and authorship. This packet does not claim a deployment, installed service change, hosted-CI runtime parity, or current public-serving state.

The new CLI source and its imports/tests were read before invocation. They use synthetic local files and subprocesses; these gates require no provider or account activity. No browser process or account session was used by this receiving layer.

## Materialization and runtime

The isolated native checkout is:

`/tmp/towerops-pr50-receiving-cf5799f6d38b-2ced04gh/composed`

Its staged tree and object database remain available at that checkout and `.git/objects`. The clone shares existing Git objects but has its own worktree/index. The original lookup of named commit 53 returned 128 because the object was absent; a read-only, credential-free, depth-one fetch of that exact commit then succeeded. Both original lookup failure and fetch logs are retained. No fetch of a moving branch or further rebase was performed.

The executed composition driver is archived unchanged as `compose.py.txt`; the native file is `compose.py`. The native/build driver is archived unchanged as `receive-native-build.py.txt`; the native file is `receive-native-build.py`. These are historical execution bytes with explicit manifest mappings, not additional product modules or lint-policy exceptions. Their absolute paths document this exact receiving run. Reproduction in another directory should substitute a new isolated root and the stated source/dependency inputs, keeping the tree and byte checks intact.

Private copy-on-write copies were created with macOS `cp -cR` for Node dependencies and the qualified Python environment; Ruff was copied with `cp -c`. No package installation occurred. The Python environment has its own site-packages and retains the shared base interpreter, explicitly recorded in `qualification/runtime.json`.

| Runtime | Received version |
| --- | --- |
| Python | 3.12.8 |
| pytest | 8.4.2 |
| Ruff | 0.16.10 |
| Node / npm | v26.3.0 / 11.16.0 |
| TypeScript / Vite | 5.7.3 / 8.3.3 |
| Vitest / Pyodide packages | 4.1.11 / 0.27.7 |

The runtime receipt pins the package lock and selected package metadata. Full dependency trees are excluded from this publication packet.

The exact commands, working directories, environment overrides, timestamps, elapsed times and exit codes are in `qualification/receiving-processes.json`. The four requested gates were ordinary commands:

```text
<private-python> -m pytest -q -p no:cacheprovider --junitxml=<private-output>/native-tests.xml
<private-ruff> check --no-cache .
<private-python> tools/generate_airspace_reference.py --check
npm run build
```

The first three ran at the composed repository root; the build ran at `web/airspace`. Optimization and cache-disabling build shortcuts were not used. `PYTHONDONTWRITEBYTECODE=1` prevents bytecode writes; `TOWEROPS_RECEIVING_OUTPUT` points the existing PR50 tests at this packet's private logs.

## Evidence map and preservation

- `source-manifest.json` pins all 589 received source leaves and the exact 335-path contribution.
- `root-qualified-source-build-pin.json` is an unchanged copy of root's 579-source/16-build receiving pin.
- `exact-pr50-delta.json` records all 11 old/new paths and mode/type/blob identities. The larger binary Git patch remains in the native workspace, with its SHA recorded in `composition-receipt.json`; duplicated upstream evidence ZIPs are not republished here.
- `composition-receipt.json` is the original pre-test receipt, so its `tests_pending: true` remains historical. `qualification/gates-summary.json` is the later completed disposition.
- `qualification/native-tests.xml`, ordinary stdout/stderr, and the unchanged PR50 tests' raw CLI fixtures/reports/source-hash receipts preserve the actual execution.
- `qualification/build-identity-comparison.json` pins all 16 built assets.
- `qualification/source-before.json`, `source-after.json` and `final-integrity.json` record unchanged source and build identities.

The external `review-manifest.json` declares exactly which native files are copied into this publication prefix, with byte counts, SHA256, Git blob identities and modes. It is metadata for transport and is not itself one of its declared files. Source/dependency trees, private profiles and duplicate binary evidence archives are excluded. Frozen earlier review packets and root's qualified source/build remain unchanged.
