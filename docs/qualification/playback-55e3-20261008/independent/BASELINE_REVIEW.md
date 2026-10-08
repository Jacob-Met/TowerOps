# Independent TowerOps playback baseline review

## Result and scope

The frozen baseline produced 2 passing and 8 failing controls. All eight captured application/source files matched their recorded SHA256 before and after the run. The failures expose two observable defects: Reset restores the slider to 1 while continuing world progression at the prior internal rate; several automatic pauses stop world progression while leaving the run control labeled `Pause traffic`.

Authoritative captured upstream: commit `09b96e31d2867af5b7a9738406d0431cf1010090`, tree `4d22827647c0b2e37d11921aa5273f7a358bcdde`. The main module is Git blob `2aabfdba1292f6db0890b2fb0b9bc8cf9e027636`, SHA256 `e712557df83d2159d8c496393e982de28dc7258be1beeefb7d3d4da0664b8d9f`. The earlier ambiguous 728387a5 label is not used as this review's source identity.

This review was written independently of the product owner's replay driver. Product sources were copied byte-for-byte into the reviewer's small baseline closure and were not edited. No GitHub calls, source changes, installation, browser interaction, deployment or live operation were performed by the reviewer.

## Controls

| Control | Baseline result | Native observation |
| --- | --- | --- |
| Speed input at 1x and 3x | Pass | Native exported world projection and clock reflect the requested rates. |
| Manual pause and resume | Pass | Paused frames preserve the exported world; resume discards elapsed paused wall time. |
| Reset from paused 3x | Fail | Slider returns to 1, but resumed world progresses at 3x. |
| Reset while running at 0.5x | Fail | Reset pauses and restores the reference world, but resume progresses at 0.5x. |
| Add traffic automatic pause | Fail | World stops and 2x rate is retained for restart, but pause label is stale. |
| Perturb track automatic pause | Fail | World stops and 2x rate is retained for restart, but pause label is stale. |
| Policy change automatic pause | Fail | World stops and 2x rate is retained for restart, but pause label is stale. |
| Pending and rejected planner bridge | Fail | Native handler pauses while pending and remains paused after the controlled rejection, but pause label is stale. |
| Last-aircraft removal refusal | Fail | Native early return preserves the world and pauses; the label remains stale. |
| Duplicate-flight refusal | Fail | Native caught refusal preserves the world and pauses; the label remains stale. |

The Reset checks compare actual world state before checking the readout. A label-only correction would not satisfy them. At the same 40 ms playback frame after priming, a fresh 1x world has `observed_at=1004.4` and first aircraft `x_nm=-4.96`. After Reset from 3x, the baseline instead has `observed_at=1009.2` and `x_nm=-4.88`; after Reset from 0.5x it has `observed_at=1003.2` and `x_nm=-4.98`.

## Exact execution boundary

The driver uses Node v24.19.0 syntax stripping and `vm.SourceTextModule` to execute the actual captured `main.ts`, `core.ts`, `world-tools.ts`, `audit.ts`, and reference JSON. A small explicit DOM event/value/disabled-state model is populated from native HTML IDs and form defaults. It invokes installed native event listeners and the native animation-frame callback. World state is observed through the native `export-world` event. Source checks and transformed-code digests are in the report.

Canvas drawing and presentation range are test doubles. Erased TypeScript type import names receive inert exports alongside actual runtime exports. The planner test uses one controlled pending/rejected Python promise; actual Python, gate/apply and actuation are excluded. Track editing is excluded. This evidence does not establish real-browser rendering, layout, TypeScript type checking, Vite/Vitest execution, or operational-airspace behavior. It adds no scenario-file, numeric-validation or audit-algorithm claim.

## Harness correction provenance

An initial eight-control run assumed elapsed clock progression should start at the reference state's `observed_at=1000`. Actual native initialization uses `fixture.now=1002`. That initial run's positive-rate failure was a harness assumption, not a product defect. The exact earlier driver/report/log remain in `harness-before-clock-correction/`.

The positive control was corrected to use the actual native initial clock, and the two refusal controls were added before any candidate existed. The final ten-control baseline is the qualified baseline reported above. The native zero-elapsed priming frame increments world version; the review preserves that behavior.

## Replay and evidence

Baseline directory: `/workspace/scratch/55e3e26c5905/towerops-playback-independent`.

Keep `review_playback.mjs`, `baseline-source-manifest.json`, and the eight-file `baseline/` closure together. Run from that review directory with a new output name to preserve the original report:

```sh
node --experimental-vm-modules review_playback.mjs --app baseline --pins baseline-source-manifest.json --label baseline-replay --report baseline-replay-report.json
```

The known baseline exits with status 1 because eight controls fail. A candidate replay must use the unchanged frozen driver, an exact candidate source closure, a corresponding pins manifest, and distinct output paths:

```sh
node --experimental-vm-modules review_playback.mjs --app /absolute/candidate/app --pins /absolute/candidate/source-manifest.json --label candidate --report /absolute/candidate/report.json
```

Candidate qualification is pending. No result for a changed product source is implied by this baseline receipt.

| Frozen file | SHA256 |
| --- | --- |
| `review_playback.mjs` | `7803c72ba02684290b8bd93fb2ee7c2052a1201b222d8a28d59c11c47f3c501b` |
| `baseline-source-manifest.json` | `843117f2e9e8b9a26d1add208e28a96daf61eb1524b9ddcd20fc8a5bf939aed3` |
| `baseline-report.json` | `282c55bcf538c80ecf28da5daee8685994cef818a148a1ff157a58b432d9a249` |
| `baseline.log` | `c38a723936450e47639fa03f4e89255eac6936ce245ab5d5e5a0d9c7d1cc59d5` |
