# Current decision-trace composition

This supplement qualifies the raw WorldState draft repair on application source from TowerOps main `9a2468f9bbaa25c0ab92cb12f712170420f9e622`, after the decision-trace feature merged. The files one directory above retain the earlier `9d70db6` baseline and candidate evidence unchanged. Their source versions are historical; this supplement carries the final application qualification.

## Observed result

The unchanged maintained receiver, SHA-256 `441e5b9ef989ce9e301ae09c21441dcba41bcb0188b85319dbbd1434fd58849f`, passed all **9/9** checks in actual Chromium 153 on the ThinkPad. The process exited **0**, its owned profile was removed, no JavaScript exception occurred, and all 162 source input hashes stayed unchanged. The entered `DRAFT202` world was actually loaded after a focus-changing render; the incomplete draft survived resize and moving traffic while the clock advanced.

The preserved paired baseline in the parent directory passed 4/9 and failed the five draft-loss cases. The assertions are identical in that run and this current-source run. No new negative baseline is claimed for this application composition.

Native reference freshness, TypeScript checking, **120/120 frontend tests**, Python asset preparation and the production build all passed. The build produced 15 files. The report records all source input and output hashes, the exact commands, raw-log hashes and the read-only dependency installation used. The existing decision-trace, audit, encounter, selected-track and numeric tests remained in the run. The browser receiver exercises only the draft lifecycle; it does not claim a new planner or decision-trace browser suite.

## Source boundary

The application change is still the same five edits reviewed independently: one explicit edited-state flag; a render guard; clearing the flag after successful JSON/schema parsing; clearing it on explicit Export; and setting it from an actual editor input event. Reversing those edits reconstructs the entire current main.ts byte for byte. The current README prefix and all other application source remain exact.

| Input | SHA-256 |
| --- | --- |
| Current parent main.ts | `347cca82b84ea49c55efd468db995820d55d32249543aa69cc744797c4f3fc80` |
| Qualified candidate main.ts | `234a50fe1eeb05125dc633120cc9902c8e5a5a9f15b142aa1a5b2f50ff55f1fa` |
| Qualified README | `3180fca723a615465152ab3586236c5e77f246107982df94c6076dd88a93fe68` |
| Raw current browser report | `c669f02e854169faeef36c0a49fb12418af7f2b5872a3faa757dd4a1ead2dd46` |
| Native gates report | `2088e0ae0026d35821e6a8e48ac04b67c4a055e7d539a0ff4bc1d84061f8a0ab` |

The subsequent receiving parent `a704b2c9f957a5f65169fa7eeb5e98f34c5a9d2c` adds only 15 paths under the independent draft/reset verification directories; every existing application byte remains unchanged. Its independent seven-case draft review is retained and credited to that cohort. It does not replace this receiver's own negative cases or imply a deployed-site check.

Raw reports and logs are copied without modification. Only the readable test transcript removes terminal control sequences; the original raw log hash remains in the gate report and transcript header. The manifest identifies each saved file. No installed service, deployment configuration, central worker or other owner's checkout was modified.
