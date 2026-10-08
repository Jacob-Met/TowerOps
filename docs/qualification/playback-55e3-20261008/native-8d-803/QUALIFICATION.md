# Intermediate native receiving: 8d with composed 803 source

This completed native test/build result belongs to exact baseline `8d4933f33a0f5e0673fa9d00002e8b29302a1c53` and candidate main SHA-256 `80333c3dc3f533fdc0b9cfc3f807ce0475a5656c2a294f3b8838028d3bf92b86`. The test remained `fbe02527200a428fae18c6d45b09ef942b9dcfd411d7e8a8bf11c30d5e74a845`. Current 093 advisory-consumer qualification is a separate source cut.

The first baseline build failed in `prepare-python.mjs` with native ENOSPC while copying `python_stdlib.zip`. It stopped before TypeScript or any candidate execution. Its raw log and receipt remain unchanged in the archive. Available host capacity recovered without deleting files or changing source/config/dependencies.

A separate exact retry then passed the native full Vitest suite: **134 tests across 10 files**. Both baseline and candidate `prepare-python.mjs`, TypeScript and Vite builds passed. All 53 baseline and 54 candidate source pins, the installed dependency lock, the preserved baseline build and prior C4 source/build were verified unchanged. The two owned candidate files were the composed main and the unchanged fbe test.

The subsequent RDC launcher write returned a path-validation timeout, and its launch request returned a timeout without a process identity. A bounded same-device readback found both the intended launcher entrypoint and aggregate browser receipt absent. No replacement 8d browser launch was made after the current-main change. **This cut has no browser qualification.** The completed C4 desktop/mobile observations remain attached to the earlier source.

`receiving-text.json.gz` contains nine exact native files as gzip-compressed JSON, with base64 file contents and original paths/hashes. `receiving-manifest.json` lists those entries without embedded contents. They include both native attempts, full test/build logs, baseline/candidate source maps and the unchanged accepted f116 browser driver. `rdc-timeouts.json` preserves the raw connector errors, fresh selected-device status and exact absent-entrypoint/absent-aggregate readbacks.

This was an isolated Mac qualification workspace. No main-hub installation, deployed service or user browser session is established by these receipts.
