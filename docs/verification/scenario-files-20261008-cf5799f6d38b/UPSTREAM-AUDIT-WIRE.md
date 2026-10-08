# Receiving the scenario feature with Python audit-wire transport

This later integration receives the unchanged seven scenario feature files on public TowerOps main `5ae808749c8624d9e267d23997beaa3ae5220dbc`, tree `356e66716c8953a3c2aac8a23790ce6eeaba20d0`. PR38 changed the audit verifier and both Python worker transport paths after the original scenario packet was frozen. Its three source changes and three added test/evidence files are all preserved.

The resulting qualified product tree is **`9ed528ac4281d4ec098b4717d909a08869057d40`**: 139 tracked files, with seven feature paths and all 132 unowned base paths preserved. Every feature blob is identical to the independently qualified `d6b4a1ec5757144f848e1d6ce851a766a7413f2c` candidate. No new production edit was needed for this composition.

## Executed receiving

The root integrator created a separate shared-object Git clone, fetched the exact public base, verified all 136 base files against the GitHub tree, and overlaid only the seven frozen feature paths. It then ran:

| Native gate | Result |
| --- | --- |
| Frontend, including Python audit-wire interoperability | 159 passed, zero failed or pending |
| Python suite | 91 passed, zero failed or skipped |
| Ruff and generated-reference check | Passed |
| TypeScript/Vite production build | Passed |
| Original author browser program, unchanged | Seven groups passed |
| Independent author's scenario browser program, unchanged | Six groups passed |
| Independent author's held real-digest program, unchanged | One group passed |

The last three are **root-operated reruns of the exact previously reviewed programs**, not a new independent author's review. Their earlier independent before/after results remain in the original packet. Each current rerun reports the exact `9ed528ac` source tree. All 139 tracked files remained unchanged after receiving, and the actual enclosing native process exited 0.

The source still clears a previous synchronous audit verdict when an imported scenario is applied. It also discards a pending verification completion if its captured AuditLog, event array or event count no longer matches. The unchanged held-digest receiver lets the discarded trace's four genuine WebCrypto hashes finish and confirms that the replacement verdict stays blank, with an empty valid trace. The newer raw Python audit-wire transport is exercised by both real CPython approval/readback cycles and the inherited interoperability tests.

Reference native execution used macOS arm64, Node26.3.0, Chrome154.0.8037.98 and Puppeteer25.12.0. The separate Python command suite used the existing Python3.12.8/pytest8.4.2 environment and Ruff0.16.10. Browser Python execution uses the project's real bundled Pyodide/CPython worker, as recorded by the unchanged browser receivers. All application requests stayed on the disposable loopback server; the native receivers used new browser profiles and no external accounts.

## Preserved packet and reproduction

All 116 files in the original final scenario overlay remain byte-for-byte unchanged. That packet's labels `current/` and final source `d6b4a1ec` describe its earlier frozen receiving point over `09b96e31`; this note and `root-wire/` describe the later integration. Original `9d4d`, `91131`, `317dd` and `d6b4` failures, source identities and receiver corrections remain separately attributable.

The exact browser scripts already present in the original packet are reused; copies of those scripts and dependency trees are not added again. For a new replay, check out the seven feature blobs on the public base above, install the project's ordinary declared dependencies in the chosen private environment, build the web app, and run the existing author and independent scripts with the source root and three distinct new output directories. Set `REVIEW_SOURCE_TREE` to the verified source tree for the independent scripts, as shown in `root-wire/process-receipt.json`; the author program reads the Git index itself. Never replace the original recorded outputs.

`root-wire/source-manifest.json` lists the complete source closure. `root-wire/final-receipt.json` and the raw test/browser outputs retain the executed commands, source paths, exits and result counts. This is source composition and isolated receiving qualification. It does not establish an installed service, a deployed public site or operational aviation use.
