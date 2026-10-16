# Manual radar navigation and current scenario receiving

Issue: https://github.com/Jacob-Met/TowerOps/issues/59

The radar keeps automatic fitting as its default and gives the operator an explicit manual view: zoom, four directions, focus the selected flight, and return to automatic fit. Camera actions redraw only the radar. The range, center and offscreen counts describe the current view without changing traffic, clock, selection, drafts, proposals, approvals or audit.

## Exact source and accepted results

| Input | Acceptance |
| --- | --- |
| Canonical 5b3015567a01017245c5f715c1bce65e20a06138 | 6 native baseline checks; broad traffic compresses the local pair and no manual controls exist |
| Authored 6eb54df0ad71ef3539d3ca6d8dd985eff875f435 | 168 unit tests, TypeScript, production build, and 22 native author checks |
| Same authored runtime, independent successor 55242537323d9ee47df505c6c5509de59acb66c3 | 38 native held-proposal/edit/audit checks; see docs/receiving/radar-navigation-held-state-401c5d17da79 |
| Genuine merge c06ade187171300112c29f2b9f4944d1e4b93240, tree 6cb2831f10ec127c385b995925257e702ff0bc9c | 236 tests, TypeScript/production build, and 18 current saved-scenario/native checks |

The merge has genuine parents 55242537323d9ee47df505c6c5509de59acb66c3 and saved-scenario main 89529c5459b1c3d52448e197de2b2f7fe8b6d128. It preserves all 1,085 nonowned existing current leaves and both scenario helper modules exactly. The five existing deltas are the airspace README, markup, main radar hooks, renderer and scoped styles. The new model/test and original independent evidence remain attributed. The live-register loop and operational handlers are unchanged.

This documentation/evidence successor changes no runtime or test byte. Earlier receipts retain their actual source pins. The original CURRENT-FREEZE manifest still records qualification pending at its creation time; the completed gates are recorded here.

## Current scenario boundary

The real built app ran in native Chromium 153 with its real Pyodide planner. A native approval and unfinished raw JSON draft were held while the receiver delayed completion of one actual File.text read. Pointer camera controls preserved both the reading context and later explicit review. Normal Save produced identical complete live scenario bytes after camera changes.

Only explicit Load replaced the traffic, all seven policy fields, clock, time scale and selection and performed the incumbent decision reset. Manual geometry remained fixed, with truthful 0/2 and selected-EAST feedback; Auto fit then included both replacement aircraft. Both actual versioned browser downloads matched the recorded native Blob bytes. No additional worker request, page exception, external request, source change or built-asset change occurred. All 1,117 source files and 16 production files remained exact. Both final frames were directly inspected.

The original 22-check gate separately covers running traffic, clipping, crossing trajectories, inverse raster geometry, phone controls and unavailable/recovery. The independent 38-check gate separately preserves a nonempty four-event audit, pending approval, another selection, unfinished track edit and raw draft through native pointer/button/canvas keyboard interaction and exact subsequent native readback.

## Evidence and retained negatives

author-current-evidence.tar.gz contains exact methods, raw receipts/logs, source pins, fixtures, native frames, downloads and every retained negative attempt. MANIFEST.json lists every member SHA256. Methods retain their actual native absolute roots; replay elsewhere requires changing receiver paths, not application modules. Dependencies were borrowed read-only; no package installation was needed.

Current attempt v1 omitted the .mjs MIME mapping in the receiver static server, so Pyodide could not finish loading. v2 suffered a partial ENOSPC method write and never qualified. v3 reached the real planner but Snap Chromium refused the input under the hidden estate directory. v4 exceeded the original 20-second browser-start allowance. v5 reached approved setup and then exhausted root disk while writing the fixture/evidence. These are preserved without being labeled product failures.

The completed receiver moved only its profile, input, downloads and outputs to owned /dev/shm/snap.chromium.towerops-radar-401c5d17da79 staging, retaining the same browser and frozen application. The helper's sole change was a 90-second startup allowance. v6 passed product interactions but expected the text 0 EVENTS instead of incumbent 0 EVENTS / VALID. v7 passed interactions and byte comparisons but expected four filenames; CDP allow download behavior reused the two versioned names. v8 corrects that expectation and passed 18/18.

Original author negatives are retained: callsigns longer than the incumbent ten-character limit and a raster mask treating a partially intersecting fractional CSS pixel as wholly outside. The independent packet retains its Enter-key encoding calibration. None required application changes.

Automatic fit retains its existing behavior. Manual state lasts for the page session and is excluded from saved scenarios. Existing aircraft metadata placement is unchanged; dense aircraft labels can still overlap at phone widths. This is a synthetic research simulation, not operational air traffic control.
