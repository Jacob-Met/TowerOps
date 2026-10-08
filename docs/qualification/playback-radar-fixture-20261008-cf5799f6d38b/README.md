# Playback fixture receives the current radar helper

The three playback failures come from the test's complete replacement of the drawing module. Current `main.ts` imports and calls `radarRangeLabel`, but the existing mock exports only `drawAirspace` and the obsolete `viewRange`. Vitest rejects that missing export during `render()`.

The failure is inherited on main `687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8` and reproduces on the scenario composition tree `8cd8023a2f676b2faa17d5d5120e3ae3e4fd54f4`. It is not caused by an uncompleted scenario guard. The exact before/after process receipts, original errors and source snapshots are retained in `records.json`.

## Why the three assertions fail

`render()` draws the updated world before calling `radarRangeLabel`, then updates the displayed speed later. Reset therefore updates the actual world, rate and range-input value, but the missing mocked export prevents the speed label from reaching `1.0x`. Those are the two rate-label failures.

`runPlanner()` pauses traffic, sets its busy state and awaits `render()` before entering the planner request. The same missing export rejects that render, so the mocked Python boundary has zero calls when the existing test expects one. The original default reporter records **45 unhandled missing-export errors** in addition to the three failed assertions. The retained JSON reporter alone does not expose those unhandled errors.

## Minimal correction

The only proposed changed repository path is `web/airspace/tests/playback-controls.test.ts`. Replace the complete drawing-module mock with a partial mock:

```ts
vi.mock('../src/draw', async importOriginal => ({
  ...await importOriginal<typeof import('../src/draw')>(),
  drawAirspace: draw,
}));
```

The actual radar helpers remain available. Canvas painting remains mocked, matching the fixture's stated scope. No product module, timer, dispatch helper, scenario behavior, test predicate or assertion changes.

| Test file | Identity |
|---|---|
| Original | Git blob `de7a02cd88f69bf8192516cb1acf7aa6eb276853`; SHA256 `fbe02527200a428fae18c6d45b09ef942b9dcfd411d7e8a8bf11c30d5e74a845`; 9,072 bytes |
| Corrected | Git blob `4e2196722e94c9970fa3e137327a5bb53ac15ad8`; SHA256 `b9acb952ff5d6a1991d2d877fdf42b875dafa670f40bf81f108be75d5959a911`; 9,131 bytes |

The change adds 59 bytes. Reversing that one mock replacement restores the original file exactly. TypeScript parsing independently verifies that all **40 assertion-call texts** and all **21 other top-level statement texts** remain exact, including every test body and fixture timing helper. See [predicate-preservation.json](predicate-preservation.json).

## Native before/after results

| Source and gate | Original fixture | Partial mock |
|---|---:|---:|
| Main 687, playback controls | 11/14, 3 failures | 14/14 |
| Composed tree 8cd, playback controls | 11/14, 3 failures | 14/14 |
| Composed tree 8cd, full maintained Vitest suite | 223/226, 3 failures | 226/226 |
| TypeScript `tsc --noEmit` with corrected fixture | — | Exit 0 |

All successful Vitest and TypeScript runs have empty stderr. The original playback failures on both sources include the same missing-export cause. The full before/after runs use identical captured product inputs; only the drawing mock differs.

Runtime: existing Node 26.3.0, Vitest 4.1.11 and TypeScript 5.7.3. The full suite's actual Python child processes use the existing Python 3.13.7. No dependency installation was performed. Dependency files were copied privately with the filesystem's copy-on-write facility; root's dependency directory remained untouched.

## Retained receiving setup failures

Two preliminary receiving setup failures are preserved and distinguished from product results:

- The first private dependency directory was named `private-node_modules`. Node could not resolve sibling packages such as `@vitest/utils`, so no tests executed. Renaming the private directory to `dependencies/node_modules` restored native package resolution without changing dependency bytes.
- The first full-suite attempt materialized only the 50-file web source closure. Thirteen Python-facing controls failed because the private repository root lacked `towerops.py`. The four unchanged native modules (`towerops.py`, `decision_trace.py`, `audit_replay.py`, `advisory_options.py`) were then received with exact source pins. Both complete 226-case before/after runs use that same closure. The incomplete 213/226 record is retained.

No assertion was removed or changed to address either setup failure. Exact scripts, argv, exits and failed records remain available.

## Custody and reproduction

Original root source:

`/tmp/towerops-root-current-cf5799f6d38b-dgopydr1/candidate`

Independent private receiving root:

`/tmp/towerops-playback-fixture-cf5799f6d38b-j_43xy6w`

Final custody verifies all **1,017 root source files and 16 root build files** against root's frozen pin, with no mismatch. Original private captures and every unowned successor file also remain exact. See [final-custody.json](final-custody.json) and [source-freeze.json](source-freeze.json).

To reproduce, use the full source at main 687 or the recorded 8cd composition and its existing compatible dependencies. Keep the original test for the negative control, then apply [playback-fixture.patch](playback-fixture.patch) in a separate checkout. Run:

```bash
npm test -- tests/playback-controls.test.ts
npm test
node node_modules/typescript/bin/tsc --noEmit
```

`records.json` stores exact native text files by SHA256 with byte count and Git blob identities; identical streams share one blob. `execution-scripts.json` retains the original execution scripts and setup corrections. This packet qualifies the maintained fixture boundary. The separate estate worker owns actual browser playback/radar receiving; those browser results are not counted here.
