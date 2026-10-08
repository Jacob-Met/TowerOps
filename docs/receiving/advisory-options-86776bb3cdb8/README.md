# Native advisory alternatives: source and receiving

Claim: https://github.com/Jacob-Met/TowerOps/issues/41

Qualified product source: `45aaacbbaff9c71bf07fc1bc23b50ba56ef11615`  
Qualified tree: `1d582c4c29d61bfd03349639dac65af990bbbac7`  
Current-main parent received: `9d70db6352875c380d64639be2212f1e71de2d12`  
Current-main tree: `e50e0f2c6302be0b5a1d90fed7fffa2a197bd321`.

## The completed workflow

Airspace Lab previously exposed only the original planner's first admitted proposal. On both the existing crossing fixture and a separately authored three-flight world, the original bounded menu contains 68 individually admitted choices out of 74 checked candidates. This contribution makes those choices reviewable in native priority order, with flight filtering, paging and expandable exact proposal bodies and hashes.

Review pauses traffic and retains the current proposal, approval, world and decision trace. Explicitly choosing a different proposal clears prior approval and readback; the existing approval/readback/apply actions then pass its exact native body to the original gate. The currently selected hash is marked and disabled. Changing the full world, policy or simulation clock invalidates both pending review responses and subsequent selection.

`advisory_options.py` uses the unchanged native generator and screens each candidate individually in a private `ControlRoom`. It never submits mutually exclusive choices as a batch or changes the application's decision trace. The existing `towerops.py`, planner priority, approval/readback logic, native audit serialization and `python.ts` lifecycle remain unchanged. The helper loads separately; an unavailable helper does not disable the existing planner operation.

## What was exercised

| Evidence | Source and result |
| --- | --- |
| Original native and browser behavior | Exact original main `5ae8087`: one exposed proposal; native enumeration finds 68 admitted alternatives. Fresh Chromium 153 runs the original Python planner. |
| Focused native addition | 12 passing tests: original first-choice identity, distinct options, unchanged inputs/audit, exact alternate application, crossed authorization, freshness, expiry, empty menus and original target/numeric admission. |
| Focused TypeScript addition | 13 passing tests: exact-copy selection, immutable response ownership, full snapshot binding, changed replies/selections and incomplete metadata refusal. |
| Current-main native gate | 103 tests and 84 subtests pass on `cd40a9c`. Successor `45aaacb` changes only two import blocks; non-import ASTs are exact. Ruff then passes on the final source. |
| Current-main browser gate | All 127 Vitest tests, the four-scenario original Python reference check, TypeScript compilation and Vite production build pass on `45aaacb`. |
| Author browser workflow | Real Chromium/Pyodide preserves an existing approval during review, clears it after a changed choice, applies the exact selected hash/body through the original gate, and verifies four original audit events. Paging, filtering, an empty review and helper-download failure also pass. |
| Independent browser receiving | Three actual Chromium/Pyodide flows on `45aaacb`, with a distinct RX-A/RX-B/RX-Z world. All 68 option bodies/hashes match an independent original-Python oracle. Filtered page-two rank 41 applies exactly. Deliberately crossed readback and changed-world requests are rejected by original Python. |
| Responsive current-main check | At a 390-pixel touch viewport, six option cards fit without horizontal overflow, an alternative can be selected, and fresh approval remains required. |

The independent selected option is RX-A at native rank 41, vector `(1.25, 2.9341736485763756)`, climb `0`, advisory hash `1cf5e15d2b2c10fd8fca8a303ed90ee06bc653b46afd0b1348e2ed83040578d7`. Its exact body is visible in the independent capture. The receiver retains both original and deliberately altered outgoing messages plus the actual native replies; no worker response was substituted.

The author browser receipt records the original-base source hashes. Its product behavior remains preserved in the current-main composition; independent receiving binds the completed composition directly. The final mobile receipt binds `45aaacb`. The original baseline's hidden audit `innerText` observation was empty and is not used as evidence of audit preservation; the later workflows assert actual event contents and native chain verification.

## Preservation and boundaries

The candidate has 146 source leaves. All 140 current-main leaves are accounted for; 134 outside the six modified paths remain byte-identical. Six paths are new. The concurrently merged encounter explorer is retained, including its source modules, markup and live render hooks. Only adjacent HTML insertions and CSS additions required manual composition. Removing the added launcher and complete review panel recreates current-main HTML exactly; existing CSS is an exact prefix.

The original main planner, approval, apply, Reset, load, perturb and policy function bodies are retained. Held scenario-file, decision-trail, selected-flight edit, raw draft, Python lifecycle and workflow scopes remain intact. `author/source-and-build.json` records every qualified Git leaf and every built file; native assets match the frozen source. Independent receiving verifies the complete current-main tree, relevant source blocks, 23 source files on disk, the two fetched native Python sources, and all 14 built leaves before and after execution.

This packet qualifies the repository's synthetic workflow. It does not assert hosted CI, publication or deployment; those are separate receiving steps. The current feature changes the web paths already selected by the Airspace workflow. The owning publication lane was separately notified that future helper-only changes should be added to that workflow's path filters.

## Retained diagnostics and reproduction

Native lint first reported import formatting in two new files. That failure and the corrected clean result are retained. Independent browser instrumentation first read collapsed details, then encountered a CDP charset fallback while recording unlabelled Python HTTP response bytes. The receiver opened the visible details and declared UTF-8 on its own local server. Both earlier driver versions, logs and failure receipts remain available; neither required a product change.

The maintained browser check is `tools/check_advisory_options_browser.py`; its command is documented in `web/airspace/README.md`. Independent command lines and source pins are in `independent/acceptance.json`. Archived Python is retained byte-for-byte as `.py.txt` so evidence is not accidentally collected as product tests; `artifact-paths.json` maps every retained path to its original name and digest. The independent original manifest remains unchanged and uses those original names.

Useful visual evidence: `author/browser/desktop-alternatives.png`, `author/current-main-mobile.png`, and `independent/selected-option.png`. Complete source, build, native, browser and preservation receipts accompany them. No broad suite rerun is necessary for evidence-only packaging.
