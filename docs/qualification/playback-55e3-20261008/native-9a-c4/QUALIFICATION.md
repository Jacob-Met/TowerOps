# Native receiving: 9a source with the joint C4 Reset and playback change

This is a completed qualification of the exact `9a2468f9bbaa25c0ab92cb12f712170420f9e622` application with joint main `c4eefbe7b3fa6b259933e893ca625b279fb079905632ec31597295f61b5ee91e` and native test `fbe02527200a428fae18c6d45b09ef942b9dcfd411d7e8a8bf11c30d5e74a845`. Subsequent editor-lifecycle source at 8d requires a separate current-source receiving receipt. These results remain attached to the C4 source cut.

## Result

The actual pinned Vitest runner passed all 14 playback cases. The native `prepare-python.mjs`, TypeScript check and Vite build completed successfully, with 19 modules transformed. The installed dependency lock and all 53 candidate source files matched before and after execution.

The independently reviewed driver `f1162d6d417327de3a8959e394541c27ab6f9f04aa3ee773c4958e286c4de941` ran actual Chrome 154.0.8037.98 with a new disposable headless profile for each run. It used the actual built page, native input events, drawing and WorldState export. Only requestAnimationFrame scheduling was controlled, so elapsed time and expected aircraft movement were deterministic.

| Native case | Preserved 9a baseline | C4 desktop | C4 mobile |
| --- | --- | --- | --- |
| Reset after 3x | Exact retained-rate and stale-policy-readout defects reproduced | Pass | Pass |
| Reset after 0.5x | Exact retained-rate and stale-policy-readout defects reproduced | Pass | Pass |
| Policy edit while running at 2x | Exact stale pause-action label reproduced | Pass | Pass |
| Refused flight while running at 2x | Exact stale pause label and encounter state reproduced | Pass | Pass |

Each Reset case first changed all three native policy controls to 6 NM, 1,500 FT and 6 MIN. The candidate restored each slider, adjacent readout and active policy statistic to 5 NM, 1,000 FT and 5 MIN. Exported aircraft resumed at the actual default 1x rate with the expected clock, identity, version, velocities and positions. Automatic pauses retained the chosen 2x rate and refreshed the current paused encounter state.

Baseline admission required each exact known defect plus positive observations of the retained rate and stale text; unrelated failures would reject the run. All three runs had no page exceptions, no horizontal overflow, trusted native control events and unchanged source/build bytes. Desktop width was 1280 pixels; mobile width was 390 pixels. The full-page screenshots capture Reset while paused with the safety-envelope controls open.

## Raw evidence and preserved predecessors

`receiving-text.json.gz` is a gzip-compressed JSON packet containing 35 exact files, encoded as base64 entries with original paths, SHA-256 and Git blob hashes. `receiving-manifest.json` lists the same files without embedded bytes. It includes the native test/build logs, the three final browser JSON reports and process receipts, both exact drivers, source manifests, and the earlier completed 2bb baseline. It also preserves the AEC/46a native 14-pass result and its separate TypeScript failure on the two Node-only test imports; that candidate never received a browser run.

The three original PNG files are separate Git artifacts. `image-receiving-manifest.json` records their source paths and exact hashes. No screenshot pixels were edited. The original 5ae keyboard-harness failure and earlier static driver-review finding remain separate historical evidence; neither is counted as a completed baseline here.

The receiving host was the isolated Mac.lan qualification workspace. These receipts do not establish main-hub installation, service deployment, planner/Pyodide execution, approval/readback behavior, or a production browser session.
