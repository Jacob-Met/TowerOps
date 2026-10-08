# TowerOps numeric candidate admission

Owner: `estate-8304a40f6f50`. Scope and coordination: [issue #35](https://github.com/Jacob-Met/TowerOps/issues/35).

## Corrected behavior

With only one aircraft, the pairwise separation loop has no other aircraft to inspect. The original native policy could admit NaN commands or an unknown retained position/altitude, advance the synthetic world, and record a valid audit chain. Its TypeScript counterpart also accepted coercible nonnumeric values through this empty loop.

Seven native Python lines and two TypeScript checks validate the replacement candidate's three commanded rates and retained x/y/altitude before the empty pairwise loop can admit it. The existing `unsafe_advisory` path records rejections. Valid finite commands, exact speed/climb boundaries, and the native policy's finite replacement of unknown old rates retain their behavior. No geometry, temporal checks, approval/readback rules, hash format, worker transport, or UI behavior was edited.

Receiving base: `d99d238f7da62d74852e07fc90da406f87c2d371`. The earlier native snapshot at `e522e53246986327b7903f3c404abf8a04ab5f1d` has the same original Python source. Local selected-source Git commits are not upstream commit identities.

| File | Original Git blob | Candidate Git blob |
| --- | --- | --- |
| `towerops.py` | `97f79799414266ce74ae723fbb9ccbb653969a7a` | `3f541e5f0f3a05dac9d12c96e75d3d69ef3377d1` |
| `web/airspace/src/planner.ts` | `dac041d2c92f0170ebdc4f6d5414a6a9fd84da96` | `82082fa50cbec1a0d30d377bb4cd3e1a67416d5e` |

The separate `python-worker.ts` timestamp and `core.ts` float-format scope in [hamon #140](https://github.com/Jacob-Met/hamon/issues/140#issuecomment-6056309821) remains with its existing owner. The selected-flight editor from #33 is present in the receiving base and is preserved.

## Native and TypeScript checks

- Original native suite: 61 passed. The 30 new cases reproduce 18 failures and retain 12 passing controls on the original policy. Sixteen failing cases apply malformed candidates; two raise TypeError instead of an audited rejection.
- Corrected full native suite: 91 passed using CI-pinned pytest 8.3.5. Ruff 0.16.10 passes. The four existing Python reference scenarios and native demo remain unchanged.
- New TypeScript suite: original source fails 21 cases and retains four passing controls. Corrected source passes all 25, exercising direct policy, real screening/audit, and approved finite application.
- Full current TypeScript suite: 62 passed, including selected-flight editor and Python-reference tests. TypeScript 5.7.3 `tsc --noEmit` passes.
- An independent 14-case differential matrix passes in each language and preserves all 56 baseline/candidate input worlds. It covers safe and conflicting peers, malformed untouched peers, and finite replacement of old malformed rates.

Replay the normal project gates from the repository root, with its documented dependencies installed:

```sh
python -m pytest -q
python -m ruff check .
python tools/generate_airspace_reference.py --check
cd web/airspace
npm test
node node_modules/typescript/bin/tsc --noEmit
```

`native-verification.json`, `typescript-baseline.json`, `typescript-candidate.json`, and the differential fixtures/results retain the measured results and counterexamples. Tool/runtime paths in raw receipts identify the actual local execution, not portable installation locations.

## Actual browser receiving

The browser uses the repository's Python core through its compiled worker and locally served Pyodide 0.27.7. Chromium 153 exercised the exact candidate Python blob, synthetic native hashes, approvals and readbacks.

Five baseline malformed cases fail when the worker parses the native result after application. The candidate instead returns structured `unsafe_advisory` for all six rejection cases, including one already-rejected infinite-command control. Each returns no new state, one rejection event, and a native-verified audit chain. No invalid state was observed being installed in the browser UI on the baseline; the demonstrated improvement is authoritative, auditable rejection in place of a serialization failure.

The two accepted controls preserve complete state and audit bytes, including the native recovery that replaces three unknown old rates with finite commands. Actual UI checks preserve failed-import state, execute the real planner/approval/readback flow, increment the version once, resolve the crossing fixture and retain four verified audit events. No page errors or external requests occurred.

After adding the TypeScript counterpart, an independent `prepare-python.mjs`, TypeScript check and Vite 8.3.3 build produced all 11 served files byte-identical to that browser-qualified artifact. The TypeScript planner is removed from this runtime by type erasure and unused-code elimination; live planning/application uses the native worker. Exact build equality carries the browser result forward without an unnecessary rerun.

`browser-receiver.mjs`, `worker-cases.json`, the baseline/candidate browser receipts, `verification.json`, `final-composition.json`, and `qualified-build-manifest.json` preserve the receiving method and source/artifact hashes. Browser execution requires a Chromium/Playwright environment and a locally served prepared build as recorded in the receiver; no live provider or traffic feed is involved.

## Existing limits

The TypeScript hash implementation still rejects old nonfinite world fields before admission, while native Python can accept a finite replacement for old nonfinite motion. This difference predates the correction and is preserved; no broad cross-runtime encoding equivalence is claimed. Raw JavaScript NaN also becomes null in JSON and is rejected by the existing worker conversion boundary. These transport/encoding paths are distinct from policy rejection.

This is a synthetic simulation. These tests do not establish operational aviation safety. Source verification and local/browser build qualification are separate from hosted CI or deployment; later receiving commits and workflows provide those receipts.
