# Selected-flight editor verification

This records qualification of the selected-flight editor against TowerOps base
`e522e53246986327b7903f3c404abf8a04ab5f1d` on 2026-10-08. The implementation
was authored by `prod-72ac1419`; `integration-72ac1419` received the frozen
candidate in a separate workspace and reviewed it without changing product source.

## Results

| Boundary | Result |
| --- | --- |
| Native editor and inherited tests | 37/37 Vitest cases passed, including 30 editor cases |
| Native production build | TypeScript and Vite passed; independent build reproduced all 39 candidate source/build hashes |
| Original Python reference | Four original-source scenarios passed; Python source and reference fixture were unchanged |
| Real browser | Eight consumer groups passed with local CPython/WASM, no page errors, and all 33 source files unchanged |
| UI | Native pointer and keyboard actions; desktop and 390px layouts inspected |

The browser challenge exercises a pending approved proposal before Cancel, an
actual Python readback afterward, scenario edits after actuation, and an edit
while another approved proposal exists. It verifies that Apply advances exactly
one world version, preserves the other aircraft and historical audit events,
invalidates old approvals, and permits a fresh planner/readback cycle with a valid
eight-event audit chain. It also checks preview invalidation after native input,
invalid numeric fields, recovery, and the conflict interval table on a narrow
viewport. The raw checkpoints and served asset hashes are in
[`browser-receipt.json`](browser-receipt.json).

The author found and reproduced a separate target-identity defect during self
review: a preview could be supplied with another flight's edit session if its
world and numeric inputs matched. The corrected module explicitly binds the
preview to the callsign. The failing regression and corrected 37-case result are
retained in the [native receipt](../../receipts/selected-flight-edit-20261008.json).
The independent browser result applies to this corrected source.

## Reproduce the frozen candidate

From the repository root:

```bash
python tools/generate_airspace_reference.py --check
npm --prefix web/airspace ci
npm --prefix web/airspace test
npm --prefix web/airspace run build
TOWEROPS_EVIDENCE_DIR=/tmp/towerops-selected-flight-evidence \
  node docs/verification/selected-flight-edit/browser-receiving.mjs "$PWD"
```

The browser harness requires a Node version with built-in `fetch` and `WebSocket`
and an installed Chrome/Chromium executable. The receiving run used Node 26.3.0
and Google Chrome 154.0.8037.98 on macOS. Set `TOWEROPS_CHROMIUM` to override the
default macOS Chrome path. The harness serves the local production build on an
ephemeral loopback port, creates its own temporary profile and explicit disposable
browser context, and writes its receipt, screenshots and netlog under
`TOWEROPS_EVIDENCE_DIR`. It closes its browser and server and removes its profile.

The default source manifest is
[`receiving-candidate.json`](receiving-candidate.json); the harness refuses source
drift from that frozen candidate. `TOWEROPS_SOURCE_MANIFEST` can select an explicitly
prepared manifest for another candidate. The manifest records 33 source files and
six build outputs; the independent native build compared all 39 entries before
browser receiving. The harness and receipt here are the exact executed files.

## Evidence and limits

[`REVIEW.md`](REVIEW.md) is the receiver's assessment. Native and browser logs,
desktop/mobile screenshots, the candidate manifest, and the raw browser receipt
are retained alongside it. [`transport-attempts.tar.gz`](transport-attempts.tar.gz)
preserves earlier transport attempts and their source identities, including an
unchanged ShadeWindow control that reproduced the same loopback navigation
timeout. A fresh incognito context and a longer navigation budget then succeeded;
those changes were made together, so the evidence does not isolate a single
cause. These historical failures are separate from the accepted candidate result.

This verifies synthetic scenario authoring and the existing demo planner flow.
Scenario edits may introduce conflicts and do not create planner-actuation audit
events. This receipt does not establish a GitHub merge, a Pages deployment, or any
operational aviation assurance; those have their own receiving boundaries.
