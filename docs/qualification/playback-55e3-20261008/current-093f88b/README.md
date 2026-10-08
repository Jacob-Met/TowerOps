# Current native alternatives and playback composition

This packet composes TowerOps main `093f88b29d6e1ede778f967528c7e010b7689ab1`, tree `4a87643d57cabf81e570b21c119f00b43f79448e`, with the previously qualified playback and Reset changes. It preserves the merged PR48 advisory alternatives consumer and the earlier WorldState draft lifecycle. Only the production `web/airspace/src/main.ts` is replaced by this packet; the existing playback test remains unchanged.

The final main has SHA256 `0893cae0bedbe7e7516b92c0f55eb01a0d6c09289dac3ed14d6f4da153b3b0dd`, Git blob `3c29b72c944df2c38a5a5fc6104aea6809bdca55`, and 26,601 bytes. The unchanged playback test has SHA256 `fbe02527200a428fae18c6d45b09ef942b9dcfd411d7e8a8bf11c30d5e74a845`.

## Preserved source and exact proof

PR48's five insertions are retained exactly: imports, review state, render integration, review/selection functions and button bindings. The complete native review/selection function block is byte-identical to current main. Its existing pause-and-label operations and subsequent renders are unchanged. Alternatives still flow through the original native response admission, explicit proposal selection, approval and readback paths.

The existing qualified pause helper and pause points are carried forward unchanged. The complete Reset body remains byte-identical to the earlier qualified source, including its policy, rate, controls and label synchronization. All five WorldState draft edits remain: the dirty flag, guarded render, explicit Export reset, successful Load reset and input binding. JSON/native-shape parsing still precedes clearing the draft flag and pausing; no transactional rollback guarantee for unrelated later exceptions is claimed.

`composition-receipt.json` records both independently constructed routes: current native093 plus the qualified changes, and qualified803 plus the five current native insertions. Both yield the same final bytes. Removing the qualified changes recovers every native093 byte; removing the native insertions recovers every qualified803 byte. Removing those insertions from native093 also recovers every native8d byte.

The three exact patches are `native-alternatives-on-8d.patch`, `qualified-playback-on-current.patch` and `native-alternatives-on-qualified803.patch`. The current native main is preserved under `native-source/web/airspace/src/main.ts` for direct inspection. Earlier frozen source and receiving packets remain unchanged.

## Complete native closure and receiving limits

`source-manifest.json` names 59 exact native inputs. `candidate-source-manifest.json` names 60: that current closure with the composed main and unchanged playback test. Every native source blob/mode was checked against the untruncated current tree. The closure includes PR48's `advisory_options.py`, its Python test/browser source, new TypeScript modules/test, and current build preparer, worker, workflow, HTML and styles. The other 46 local input paths are reused from the frozen prior closure. Existing current-source files are identified by immutable Git URLs and hashes instead of broadly duplicated in these evidence files.

`root-source-captures.json` preserves the thirteen new/changed captures, and `native-tree.json` preserves the exact current tree observation. Absolute local paths record execution custody; the source URLs and hashes identify their immutable Git contents. No new maintained authoring script or dependencies are introduced.

At this packet's freeze, the result is exact source composition evidence. The earlier 803 candidate's native 134-test pass and successful build remain tied to 803. Its interrupted browser transfer produced no browser result. New current native tests/build/browser receiving must name this source and both current manifests. Prior PR48 qualification is retained with its original owner and is not reattributed to this composition. The unchanged fourteen playback cases do not claim alternatives-flow or draft-persistence coverage. No deployment or operational airspace use occurred.
