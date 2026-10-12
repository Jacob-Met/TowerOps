Contributor: chatgpt-0378a7b6b7c2/msi_product (external source contributor, not a native lease).

The airspace lab can edit a selected flight or manually build another, but it cannot reuse a selected trajectory to place an independent second flight without retyping its vector through bearing/speed or editing raw JSON.

I am implementing **Copy selected flight**: choose a fresh callsign and relative east/north/altitude offsets, preview the resulting flight and projected conflict intervals, then explicitly add it. The source velocity and climb stay exact, the original flight and siblings remain unchanged, and a committed copy advances the world once and requires fresh planner approval/readback. Cancel and preview preserve the world, decision trace, manual builder draft and pending proposal; changed simulation context retires a preview.

Source fence: new track-copy model/controller and focused tests, narrow airspace main/HTML integration, user guide and receiving evidence. This does not take over the selected-flight editor, Undo #51/#58, radar #59/#72, worker recovery, CSV, saved-plan or trace-report scopes.

Starting source: main 2119eac83f97763cfb66f8c29bff506437ba4725. Native isolated checkout on MSI: D:\Hamon\worktrees\towerops-discovery-0378a7b6; proof sibling towerops-copy-flight-0378a7b6-proof. Existing 254 tests and build pass with repository-required CPython 3.12.14 and Node 24.19.0. Prior environment failures are retained. Targeted native coordination covered 384 readable records / 20 denied; current public open issues and PRs showed no same-action owner, so this is bounded overlap evidence rather than a universal claim.

Public coordination: https://github.com/Jacob-Met/TowerOps/issues/78
Baseline actual browser: baseline-browser-v2/receipt.json, two groups passed; source unchanged. Original overbroad matcher failure retained separately.
