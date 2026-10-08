# TowerOps playback controls — 2026-10-08

## Product change

Reset now restores the simulation rate to the displayed 1× default. The existing automatic-pause paths update the Run/Pause button immediately, including validation refusals and the time before a planner response settles.

The only production change is in `web/airspace/src/main.ts`: one local `pauseTraffic()` helper, calls at the existing pause points, and `rate=1` during Reset. WorldState loading still pauses only after successful validation. The selected-flight editor, manual run/pause handler, frame integration, policy calculations, approval and readback logic retain their existing behavior. There is no new production dependency, module or state model.

Base main: [`09b96e31d2867af5b7a9738406d0431cf1010090`](https://github.com/Jacob-Met/TowerOps/commit/09b96e31d2867af5b7a9738406d0431cf1010090).
Explicit base tree: `4d22827647c0b2e37d11921aa5273f7a358bcdde`.
Baseline main blob: `2aabfdba1292f6db0890b2fb0b9bc8cf9e027636`.
Candidate main SHA256: `c5867cb7c293eb3f5f104b5f3a0e5d2c94a5b8bb42be833bd2f7df42085ac312`.

## Reproduced behavior

The [unmodified baseline](baseline-result.json) passes two positive controls and fails eight product controls. After selecting a valid 3× rate and pressing Reset, the slider reads 1 while the label and engine remain at 3×. On the same 80 ms frame, the restarted baseline advances 14.4 simulated seconds and 0.24 NM, versus 4.8 seconds and 0.08 NM from a fresh 1× state. Reset restores the scenario state itself correctly; the defect is the retained rate.

The baseline's successful add/remove/load/policy/perturb actions and failed custom-flight validation pause actual world advancement while continuing to display `Pause traffic`. Updating only `render()` would leave validation refusals that return before rendering unresolved.

The [candidate replay](candidate-result.json) passes all ten unchanged controls. Default advancement and manual pause/resume preserve their original behavior. The exact source hashes are recorded before and after every run.

The independent reviewer reports ten unchanged controls passing on the candidate versus two on the baseline. Additional independent coverage preserves failed-load behavior across malformed JSON and invalid native shapes while either running or paused. The reviewer verified the 5,597-byte selected-edit block, 2,303-byte frame/event-binding suffix and all seven unchanged captured dependencies. The independent packet is under `independent/`; its native track-edit runtime is not exercised.

## Executable checks

The existing project test runner discovers `web/airspace/tests/playback-controls.test.ts` through its normal Vitest command:

```sh
cd web/airspace
npm test -- tests/playback-controls.test.ts
```

The file adds 14 focused event/RAF controls using the actual page module. It substitutes drawing and the asynchronous Python boundary, uses the existing page HTML for control defaults, and needs no browser-DOM dependency. **At this packet's authoring cut, native Vitest is unavailable locally.** Node TypeScript syntax erasure succeeds, but that is not recorded as a Vitest pass. Native runner and browser results must be recorded separately when available.

The executed standalone qualification uses Node 24.19.0:

```sh
node --experimental-vm-modules docs/qualification/playback-55e3-20261008/playback-baseline.mjs web/airspace /tmp/towerops-playback-result.json
```

Run that same command against an app root checked out at the pinned base commit to reproduce the eight baseline failures. `before-main.ts` preserves the original affected source, `baseline-source-manifest.json` pins the eight source captures, and `original-replay.mjs` preserves the exact driver behind the baseline result. `replay-adaptation.json` records that the publishable driver changes only its default app/output paths; its test bodies and expectations are unchanged.

## What the executed replay establishes

The replay executes exact `main.ts`, `core.ts`, `world-tools.ts`, `audit.ts` and the repository's existing Python-reference scenario. Node erases TypeScript syntax, with narrow facades for erased type-only imports. Runtime exports come from the executed modules. A controlled DOM, event callbacks and deterministic RAF queue observe world state, clock, rate slider and labels. Drawing is captured as state/policy data. This result does not execute browser layout, Canvas rendering, Pyodide, the selected-edit runtime, a full app build or deployment.

Public integration remains the parent's responsibility after fresh base and ownership checks. The active scenario save/load work owns different page-module areas and must be preserved during composition.
