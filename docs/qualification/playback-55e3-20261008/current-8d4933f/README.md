# Current WorldState draft and playback composition

This packet composes the five WorldState editor lifecycle changes merged in TowerOps commit `8d4933f33a0f5e0673fa9d00002e8b29302a1c53` (tree `918931cb2034049be9e7717012b3b3309a63b4c3`) with the previously received C4 playback and Reset changes. It adds no further product behavior.

The final `web/airspace/src/main.ts` has SHA256 `80333c3dc3f533fdc0b9cfc3f807ce0475a5656c2a294f3b8838028d3bf92b86` and Git blob `35a72d5c9b3a3072f2c6069aa4964964521fb38f`. The existing playback test remains SHA256 `fbe02527200a428fae18c6d45b09ef942b9dcfd411d7e8a8bf11c30d5e74a845`; it is not changed or duplicated by this packet.

## Preserved behavior

The current native draft flag, render guard, explicit Export reset, successful Load reset and input event binding are preserved exactly. A JSON or native-shape parse refusal still exits before clearing the draft flag or pausing traffic; this source proof makes no transactional rollback claim for unrelated exceptions after assignment. A successful Load parses first, clears the draft flag, pauses, and then assigns the new state. Explicit Export remains the existing way to replace the editor text with the live world.

The C4 pause helper, encounter update, existing pause points and existing-owner Reset body are preserved exactly. Reset retains C4's rate, policy, controls and label synchronization. This composition does not add a draft-flag clear to Reset. Selected-track editing and decision trace remain in the receiving native source.

## Exact source proof

`composition-receipt.json` records two independently constructed routes to the same final bytes: current 8d plus the qualified changes, and C4 plus the five current draft edits. Both inverse routes recover every original byte. The exact patches are:

- `bd1-native-lifecycle.patch`: common source to current 8d, exactly five draft lifecycle edits.
- `qualified-c4-on-current.patch`: current 8d to the composed candidate.
- `bd1-on-qualified-c4.patch`: qualified C4 to the same composed candidate.

The common source has SHA256 `347cca82b84ea49c55efd468db995820d55d32249543aa69cc744797c4f3fc80`. Qualified C4 has SHA256 `c4eefbe7b3fa6b259933e893ca625b279fb079905632ec31597295f61b5ee91e`. Current 8d has SHA256 `234a50fe1eeb05125dc633120cc9902c8e5a5a9f15b142aa1a5b2f50ff55f1fa`.

## Source closure and receiving boundary

`source-manifest.json` identifies all 53 current native build and test inputs. `candidate-source-manifest.json` identifies the 54 candidate inputs: the same native closure with the composed main and the unchanged playback test. Every native blob and mode was checked against the captured current tree. Fifty exact local source paths were reused; the three newly received files are preserved under `native-source/`. The remaining native files are addressable at the immutable source URLs in the manifest. Their bytes are not duplicated in this publication packet.

Absolute local paths in the frozen manifests and receipt record execution custody. The native source URLs and content hashes identify their immutable source. `tree.json` retains the complete current tree observation. The temporary authoring script is not published as maintained code; the exact patches and inverse receipt preserve the composition evidence.

At this packet's freeze, this is source composition evidence. The earlier C4 Vitest, build and browser results remain attached to C4. New native receiving must name this final source and both manifests. The captured owner's `world-json-draft.browser.mjs` has not been executed or newly qualified by this packet. No deployment or operational airspace use occurred.
