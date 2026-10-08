# Raw WorldState draft preservation

This receiving packet supports [TowerOps #43](https://github.com/Jacob-Met/TowerOps/issues/43). Airspace Lab now keeps typed raw JSON when the user changes focus, selects a flight, resizes the page, or leaves traffic running. Failed validation keeps the exact text available to correct. Explicit **Export live world** replaces the draft; successful **Load into simulation** applies it and resumes live synchronization. Untouched editors continue to reflect the simulation.

## Source and scope

The receiving parent is `9d70db6352875c380d64639be2212f1e71de2d12`, tree `e50e0f2c6302be0b5a1d90fed7fffa2a197bd321`, including the original Python audit-byte work and encounter explorer. The product change consists of five narrow edits in `web/airspace/src/main.ts`: a draft flag, the editor assignment guard, the first-input listener, and flag reset after explicit export or successful parsing and validation.

Current parent main.ts SHA-256: `99cb1b1d676b6004d00a1efd531323c0b6d6831127410d1764437b856afd335a`. Qualified main.ts: `35d95fa3e931ffef4f11562358f59a7a6128bbb1a7cbad36946a2c490551f6eb`.

Reversing those five edits produces the complete current parent file byte for byte. The current README is retained as an exact prefix before the new raw-editor section. The 138 other parent leaves remain exact. No reset/rate/policy-caption statement, selected-track code, planner, worker, audit, scenario format, dependency, or workflow changes are included. The earlier source precursor is retained natively at `1253c1bf983249ae6d373ec4098c20d89202b060`; it was based on `09b96e31` before the audit and encounter contributions.

An independent teammate read and hash-matched the complete original and candidate main.ts files, the original negative browser receipt, and the parser. They accepted the five edits: validation precedes clearing the draft flag, and the editor assignment occurs before render's asynchronous audit check, so no later continuation can replace the text.

## Actual native receiving

The same nine browser assertions ran against an isolated current parent and the candidate with Node 22.22.1, Chromium 153.0.8010.47, and the existing lock-pinned Vite 8.3.3 toolchain.

| Receiving source | Passed | Failed | Process exit | Cleanup |
| --- | ---: | ---: | ---: | --- |
| Current parent | 4 | 5 intended draft-loss failures | 1 | Passed |
| Candidate | 9 | 0 | 0 | Passed |

The five failures demonstrate lost authored values after flight selection, loading the old world after a focus-changing render, lost incomplete JSON after resize, lost blurred text during moving traffic, and lost text after a rejected load. Passing controls cover untouched live synchronization, explicit export, direct valid load, and absence of JavaScript exceptions. Actual browser keyboard/mouse events enter and submit the text; observations retain the authored and loaded callsigns.

Both final runs preserve all source bytes, report no JavaScript exceptions, and remove their own browser profiles. The candidate preserves traffic progression while protecting the draft. The final receiver SHA-256 is `441e5b9ef989ce9e301ae09c21441dcba41bcb0188b85319dbbd1434fd58849f`.

The existing Python reference check, TypeScript check, all **114 existing frontend tests**, preparation of exact repository Python assets, and production Vite build also pass. The native gate receipt records every command, status, source snapshot and the thirteen output files. Dependencies were read from an existing native checkout with the identical package lock; all Vite/Vitest cache paths and output were directed to this contributor's own workspace.

## Reproduce

Use the repository's existing setup and build commands. With Node 22+ and an installed Chrome/Chromium, run from the repository root:

```sh
node web/airspace/tests/world-json-draft.browser.mjs --root . --browser /path/to/chromium --output /tmp/towerops-world-json-receiving
```

The receiver normally uses this checkout's `web/airspace/node_modules`. An explicit `--toolchain` can select an existing identical-lock toolchain; it is read through a link in the receiving checkout, with cache and output in the receiving workspace. No browser automation package or new product dependency is required.

## Retained execution history

The original frozen receiver `4d8196cdda7ab4509fdf0eba577966dbc03f62b9286d7ac93e84b5175253d7d2` also passed all nine candidate assertions, then its process exited 1 because Chromium was still finishing profile writes during removal. That successful workflow report and failing process transcript are preserved under `history/`. The final receiver adds an owned-process close barrier, bounded profile-removal retries, and records final status after cleanup. The nine scenario/assertion blocks remain identical.

Two earlier browser attempts timed out during startup before any scenario; their original raw files remain in native QA, and are not counted as product failures. An ENOSPC receiver-copy attempt also occurred before the final run; it was restored from the exact retained source. Product source, prior receipts and other owners' files remained intact.

The packet's JSON files and logs retain original native paths and timestamps. `manifest.json` records exact copied byte sizes, SHA-256 digests and Git blob identities. The readable native test transcript removes terminal formatting only; its original raw digest is recorded. This qualification covers these synthetic editor workflows in the recorded browser, not operational aviation use or unrelated feature claims.
