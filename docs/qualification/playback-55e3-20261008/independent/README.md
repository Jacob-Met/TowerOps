# Independent playback receiving qualification

The unchanged independent receiving driver passes **10 of 10 controls** on the private candidate. The exact prior source passes 2 and fails 8. A separate focused failed-load control passes on both sources across four scenarios. No bounded counterexample remains in the reviewed playback contract.

## Candidate and baseline

The candidate changes only `src/main.ts` among the eight captured files. Its SHA256 is `c5867cb7c293eb3f5f104b5f3a0e5d2c94a5b8bb42be833bd2f7df42085ac312` (21,936 bytes). The captured baseline main is Git blob `2aabfdba1292f6db0890b2fb0b9bc8cf9e027636`, SHA256 `e712557df83d2159d8c496393e982de28dc7258be1beeefb7d3d4da0664b8d9f`.

The baseline was captured from commit `09b96e31d2867af5b7a9738406d0431cf1010090`, tree `4d22827647c0b2e37d11921aa5273f7a358bcdde`. This review pins a private candidate over that exact source. It does not establish a later remote head or deployment.

The diff adds `pauseTraffic()` at existing automatic pause assignments and explicitly restores `rate=1` in Reset. Successful world loading still pauses only after native parsing succeeds. The 5,597-byte selected-track-edit block and 2,303-byte frame/event-binding suffix remain byte-identical. The seven other captured files remain unchanged. Exact hashes and inspected sections are retained in [source-review.json](source-review.json), with the exact [source diff](independent-source-diff.patch).

## Receiving results

The main driver's ten controls were frozen before the candidate existed. The same bytes executed against both sources; no assertion was changed to accommodate the fix.

| Control | Baseline | Candidate |
| --- | --- | --- |
| Native speed input changes actual projection and clock | Pass | Pass |
| Manual pause/resume preserves world and discards paused wall time | Pass | Pass |
| Reset from paused 3x restores actual 1x progression | Fail | Pass |
| Reset while running at 0.5x restores actual 1x progression | Fail | Pass |
| Add traffic pauses accurately and retains restart rate | Fail | Pass |
| Perturb track pauses accurately and retains restart rate | Fail | Pass |
| Policy change pauses accurately and retains restart rate | Fail | Pass |
| Pending/rejected planner bridge keeps pause control accurate | Fail | Pass |
| Last-aircraft removal refusal reports actual paused state | Fail | Pass |
| Duplicate-flight refusal reports actual paused state | Fail | Pass |

The Reset controls compare actual exported world progression before checking the speed readout. At the same 40 ms frame after priming, the candidate matches a fresh 1x world: `observed_at=1004.4` and first aircraft `x_nm=-4.96`. The baseline instead continues at the old rate, yielding `1009.2/-4.88` after 3x Reset or `1003.2/-4.98` after 0.5x Reset. The reference clock starts at native `fixture.now=1002`.

The requested failed-load preservation check was added separately after the candidate was received. It reuses the frozen reviewer harness and covers malformed JSON and native world-shape refusal, each while running and paused. In all four scenarios, the native refusal is reached, the immediate world and playback display are preserved, running traffic continues at the retained 2x rate, and paused traffic remains still. This is reported as **one supplementary control per source**, not four additional independent methods. It does not expand the scenario validator's acceptance contract.

Raw observations and source checks are in [baseline-report.json](baseline-report.json), [candidate-report.json](candidate-report.json), [baseline-failed-load-report.json](baseline-failed-load-report.json), and [candidate-failed-load-report.json](candidate-failed-load-report.json). The concise machine-readable rollup is [verification.json](verification.json). All eight source pins remained unchanged before and after every run.

## Execution boundary

Node v24.19.0 syntax stripping and `vm.SourceTextModule` execute the actual captured `main.ts`, `core.ts`, `world-tools.ts`, `audit.ts`, and reference JSON. The driver uses installed native event listeners and the native animation frame, reads actual state through native `export-world`, and populates its small explicit DOM model from native HTML IDs and form defaults. Inert type-only export names account for imports erased by the application's ordinary TypeScript build; actual runtime exports are retained.

Canvas drawing and presentation range are test doubles. One controlled pending/rejected Python promise exercises the planner handler's pause boundary. Actual Python, gate/apply, actuation and selected-track-edit behavior are excluded. Selected-edit source preservation is a byte comparison; the unavailable native track-edit module was not simulated as working behavior.

These results do not constitute a real-browser, visual, layout, TypeScript type-check, Vite/Vitest, Pyodide, deployment or operational-airspace qualification. The product owner's separate native test integration is outside this independent result. No product source was edited by the reviewer, and no network publishing was performed.

## Preserved before evidence

An early eight-control harness used `state.observed_at=1000` as the initial clock, although native code initializes `now` from `fixture.now=1002`. That positive-control failure was a harness assumption. Its exact driver, raw report and log remain in [harness-before-clock-correction/](harness-before-clock-correction/). The final ten-control baseline corrected the clock assumption and added the two refusal controls before the candidate existed.

The frozen [baseline receipt](BASELINE_REVIEW.md) records the earlier baseline stage, when candidate qualification was still pending. This receipt and `verification.json` record the completed candidate stage. Historical reports and the original main driver remain unchanged.

## Reproduction

Run these commands from this directory with Node 24 supporting `stripTypeScriptTypes` and experimental VM modules. Captured `baseline/` and `candidate/` source closures are included. Absolute author paths inside recorded provenance are descriptive and are not required by the replay. New output names preserve the original reports.

```sh
node --experimental-vm-modules review_playback.mjs --app baseline --pins baseline-source-manifest.json --label replay-baseline --report replay-baseline.json
node --experimental-vm-modules review_playback.mjs --app candidate --pins candidate-source-manifest.json --label replay-candidate --report replay-candidate.json
node --experimental-vm-modules review_failed_load.mjs --app baseline --pins baseline-source-manifest.json --label replay-baseline-failed-load --report replay-baseline-failed-load.json
node --experimental-vm-modules review_failed_load.mjs --app candidate --pins candidate-source-manifest.json --label replay-candidate-failed-load --report replay-candidate-failed-load.json
```

The first command intentionally exits 1 for the eight known baseline failures. The other three exit 0 in the preserved runs. Experimental Node warnings are retained in the corresponding raw logs.

| Frozen driver | SHA256 |
| --- | --- |
| `review_playback.mjs` | `7803c72ba02684290b8bd93fb2ee7c2052a1201b222d8a28d59c11c47f3c501b` |
| `review_failed_load.mjs` | `b98e79a7337ae5d3096a5f18c7732db0d47d5d88cb4b96b9191d96c91d2cf20d` |
