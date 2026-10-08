# Independent receiving — selected-flight editor, revision 2

## Decision and ownership

**ACCEPT the frozen revision 2 product source for the selected-flight editor browser and model behavior described below.** Receiver: `integration-72ac1419`, independent of the author in `/root/production`. The author owns publication and integration. This receipt does not assert a GitHub merge, deployment, or operational aviation qualification.

Repository: `Jacob-Met/TowerOps`. Issue: https://github.com/Jacob-Met/TowerOps/issues/32. Receiving base: `e522e53246986327b7903f3c404abf8a04ab5f1d`. The 39-leaf `receiving-candidate.json` manifest pins 33 source files and six build files. Its SHA-256 is `f63e18b012d028ffbbdde4302584e08fb2f4e0b7be74c2ac9ae3dc33ff845d4b`.

| Accepted source | Git blob | SHA-256 |
| --- | --- | --- |
| `web/airspace/src/track-edit.ts` | `ff3668979df28a70f848078356a096dd876cf692` | `80ce537aa01e613a47d7c9620b6a8ff732f7ada0c48c21dc02d5947fb8f06046` |
| `web/airspace/src/main.ts` | `2aabfdba1292f6db0890b2fb0b9bc8cf9e027636` | `e712557df83d2159d8c496393e982de28dc7258be1beeefb7d3d4da0664b8d9f` |
| `web/airspace/tests/track-edit.test.ts` | `3c0812f94ff7d2dd9ff6a32f573ac28102ff10fe` | `58adb9d2d42ae7284e8d3c3a949157ff80b46a1d63d9a2859b28d418497a647e` |

The author identified and repaired the revision 1 target-binding gap: a preview must bind the aircraft identity as well as the world and numeric fields. The author preserved a failing-before regression and the 37-test passing result for revision 2. This finding and source repair belong to the author.

## Native verification and browser challenge

The receiver used an isolated Mac source copy. Node was `v26.3.0` and Chrome was `154.0.8037.98`. Independent `npm test` passed all **37 tests** (30 edit tests, three world-tools tests, four algorithm tests). The independent TypeScript/Vite build succeeded and reproduced all 39 supplied source/build leaf hashes.

The final exact executed `browser-receiving.mjs` has SHA-256 `942ae4e4f1cf6b89b39784e3563ae1d1c9a6d1d122785f1a9e5e94a0ac7072e9`. Its portable replay exited **0 in 6.56 seconds**, with eight passing workflow groups:

1. The actual local CPython planner in the Pyodide WebWorker produced an approvable proposal bound to the world.
2. Native Tab, ArrowUp, and Enter input previewed removal of the analytic `T+2.50–5.00 min` crossing interval. Cancel preserved the world, all seven prior new-flight draft values, the proposal and approval, and returned focus.
3. The proposal retained by Cancel actually passed Python readback and appended four valid audit events.
4. Apply advanced exactly one world version, changed only the selected track, preserved the other track and existing audit, and rejected a preview invalidated by a native field change even when the numeric value was restored.
5. Applying an edit with an approved proposal cleared the previous proposal and approval gates without erasing the audit history.
6. Replanning the edited world used actual Python actuation, advanced the world again, and preserved the four-event audit prefix within an eight-event valid chain.
7. A fresh 390 × 844 browser viewport displayed the interval table without horizontal overflow. An empty numeric field prevented Preview/Apply; corrected keyboard submission succeeded and preserved the other track.
8. No runtime exceptions were recorded. Recorded page requests stayed on the isolated loopback server, real Python and WASM assets were served, and all 33 source files remained byte-identical.

The runtime source `towerops.py` was served with SHA-256 `8abe33edea5a7bdcdf6e6f81d31168c485f5a29229aa8d14c3310ae08728745e`. The served Pyodide WASM had 10,105,545 bytes and SHA-256 `a50dd1843f805a0b7c45b61037ee0d7b26dfe85efe0e18ef95a34ad24e401f5f`. No substitute planner or mocked actuation was used. Desktop and narrow-viewport screenshots were visually inspected. The narrow test used browser input and viewport emulation, not a physical touch device.

The eight groups and 37 unit tests overlap in behavior; they are not independent statistical trials.

## Transport failures and bounded interpretation

`transport-attempts.tar.gz` preserves three failed receiver versions, their raw logs and receipts, a diagnostic Chrome netlog, the initial revision 1 success, and the unchanged ShadeWindow control with its contemporaneous failure.

All three initial TowerOps attempts stopped at a 15-second `Page.navigate` timeout before product assertions. The loopback Node self-probe succeeded. The third attempt added direct networking and a netlog; its connection reached loopback but the HTTP request stalled. The unchanged ShadeWindow receiver also timed out at navigation at that time. This supports a shared browser transport limitation; it does not establish a specific root cause or a TowerOps product failure.

The next attempt changed incognito mode and the navigation timeout to 45 seconds together, and passed on revision 1. Their individual causal contribution was not isolated. The accepted revision 2 runs also used an explicit disposable CDP browser context. The previously successful, machine-specific revision 2 script, receipt, and raw log remain unchanged under `history/machine-specific-v2/`.

The portable final script changes exactly two expressions from that successful revision 2 script: the manifest path and the netlog path. Assertions, product source, browser arguments, context isolation, and timeout budgets are unchanged. The final portable script was executed after staging the exact accepted manifest at its repository default path. Its successful receipt and log are the top-level files in this evidence set.

## Replay from the repository

Build the frozen source with its lockfile, then run the standalone receiver from the repository root:

```sh
cd web/airspace
npm ci
npm test
npm run build
cd ../..
TOWEROPS_CHROMIUM="/absolute/path/to/chromium" \
TOWEROPS_EVIDENCE_DIR="/absolute/path/to/new-receiving-output" \
node docs/verification/selected-flight-edit/browser-receiving.mjs "$PWD"
```

Use a Node runtime providing the built-in WebSocket and fetch APIs; the recorded run used Node 26.3.0. Chrome defaults to the standard macOS application path if `TOWEROPS_CHROMIUM` is unset. The receiver reads `docs/verification/selected-flight-edit/receiving-candidate.json` by default; `TOWEROPS_SOURCE_MANIFEST` can provide an explicit alternative. It writes the netlog and receipt under the selected evidence directory, starts its own ephemeral loopback server, and uses a fresh browser profile and disposable browser context.

The initial dependency installation materializes the pinned Pyodide 0.27.7 assets. During the browser challenge, the application and Python runtime are served from loopback. The evidence pins the tested source rather than an eventual publication commit; a publisher must verify these leaves on the final full repository tree and satisfy the repository's normal hosted integration gates.

## Evidence files

`browser-receipt.json` records the actual checkpoints, worlds, audit observations, source hashes, served assets, requests, and exceptions. `browser.log` is the final portable process output. `native-vitest.log` and `native-build.log` are independent native command logs. `desktop-preview.png` and `mobile-preview.png` show the accepted preview layout. `manifest.json` records byte lengths and SHA-256 values for the evidence files and the exact executed script. Transfer packet files are scratch transport intermediates and are excluded from publication.

