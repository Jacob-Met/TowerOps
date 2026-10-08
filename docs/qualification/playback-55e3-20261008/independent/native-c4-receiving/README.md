# Independent receiving of the completed C4 native run

The exact C4 main and corrected fbe playback test passed native receiving on the Mac qualification host. This packet independently checked the returned raw records and the three original screenshots. It did not rerun the app, tests or browser.

| Received execution | Observed result |
| --- | --- |
| Native Vitest playback test | 14 passed, 0 failed |
| Native `prepare-python`, TypeScript and Vite build | Exit 0; 19 modules transformed |
| Preserved 9a baseline, joint browser driver | All four exact known defect patterns admitted; unrelated checks pass |
| C4 candidate, desktop Chrome viewport | 4/4 cases pass; no page exceptions |
| C4 candidate, 390 px Chrome mobile viewport | 4/4 cases pass; no page exceptions |

The baseline is an expected-defect receipt. Its four case records contain the intended failed assertions; they are not four ordinary passing candidate cases. The driver rejects any other failure pattern.

## Source and build custody

All 35 returned text files were checked for byte length, SHA-256 and Git blob identity against the received manifest `884de02e…`. All 53 candidate source entries in the build's before/after maps match the independently reviewed joint source manifest `e3eac6eb…`, including main `c4eefbe7…` and test `fbe02527…`. Both candidate browser runs use those same source entries and the exact 15 output files fingerprinted by the successful native build. Their source/build maps remain unchanged after execution.

The baseline run retains all 52 baseline source entries. Its reused build map exactly matches the earlier baseline browser's preserved build map, and its source entries match the successful baseline build receipt. The first baseline build receipt does not itself carry a complete output-file map; the preserved browser map and explicit reuse check supply that part of the chain.

All three final runs use the reviewed driver `f1162d6d…`, Chrome 154.0.8037.98, native input events, actual WorldState exports, actual canvas drawing and actual styles. The driver only supplies controlled timestamps to the native RAF callback. This does not qualify unconstrained wall-time scheduling, a physical phone, a production service or planner/approval/Pyodide execution.

## Raw observations

Both candidate Reset cases restore the exact native fixture, a `Run traffic` label, slider 1, `1.0x`, and policy defaults of `5.0 NM`, `1,000 FT` and `5.0 MIN`. The adjacent readouts agree with both the slider values and active policy statistics. The world remains unchanged across two paused frames. Resuming then advances the actual exported world by 4.8 seconds from the fixture clock and by 0.08 NM for each one-NM-per-minute east/west track over the controlled 80 ms frame interval. The preceding 3x and 0.5x rates no longer persist after Reset.

The baseline retains the prior rate label and engine rate, and all three prior adjacent policy readouts, while its reset slider values and active policy statistics already show defaults. Those precise mismatches agree with the accepted failure-name set. Other world, identity, velocity, version, native-input and layout checks pass.

The policy and refused-flight cases pause without changing the exported world, retain the chosen 2x rate, display `Run traffic`, keep the world stationary through paused frames and resume at 2x. The candidate encounter panel reflects the actual paused source version after the early refusal. On the baseline, that refusal leaves the panel in its exact prior running presentation; the policy path's ordinary render still refreshes it.

## Screenshot inspection

All three original PNG byte sequences were independently checked and viewed at original resolution. The baseline desktop image shows the known stale `3.0x` and edited policy readouts. The candidate desktop and mobile images show `1.0x` and the three default readouts with the native range controls. Scoped playback/policy controls are legible, contained and unobscured; the recorded page widths are 1280/1280 and 390/390 with no horizontal overflow.

The screenshots depict the Reset-from-3x paused step. They do not visually demonstrate every later behavioral assertion. `c4-native-receiving.json` was frozen before binary image readback and therefore records visual inspection as pending; the separate `c4-visual-review.json` closes that step without rewriting the earlier receipt.

## Preserved history and publication

The first current CI run had 120 passing existing tests and 14 setup failures because the old DOM stub did not support the new encounter control lookup. The later AEC/46a native run passed 14 playback tests but failed TypeScript on the two Node-specific imports. The corrected C4/fbe execution is the one accepted above. Earlier 5ae numeric-input clearing failure remains a separate harness precondition failure. No failure has been removed or counted as a product regression it did not reach.

The provider's [native C4 packet](../../native-9a-c4/QUALIFICATION.md) publishes its 35 exact raw files in [receiving-text.json.gz](../../native-9a-c4/receiving-text.json.gz), a gzip JSON envelope whose file records contain the original base64 bytes. `publication-custody.json` verifies those decoded members against the independently read raw files, plus the exact three published PNGs. `provider-receiving-manifest.json` and `provider-image-receiving-manifest.json` preserve their mappings without duplicating the raw packet here.

This completed result is bound to the C4/fbe source cut on the captured 9a dependencies. The later 8d WorldState-draft integration has its own source and native receiving gate. The C4 result does not automatically qualify it.
