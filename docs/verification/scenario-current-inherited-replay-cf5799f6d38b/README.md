# Inherited independent scenario controls on the current composition

The existing independent alternatives and raw-draft receivers both pass unchanged on source tree **8cd8023a2f676b2faa17d5d5120e3ae3e4fd54f4** and its normal 16-file build, over current main **687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8**. This packet records a replay of **four inherited controls**. It introduces **zero new browser predicates**, product changes or test changes.

| Exact inherited receiver | Actual first-run result |
| --- | --- |
| Alternatives, SHA256 f1ff675481cb14a30868f6c106bde719aefdb26144688cce3828a299cebbcf0c | 2/2; process exit 0; 4.892 seconds |
| Raw draft, SHA256 8ab4f56d0f8e0a62f80b72f799268d9e1ee43012dd5e336f6bf5033930db1997 | 2/2; process exit 0; 3.167 seconds |

Both runs have empty stderr, zero page errors and zero external application requests. The alternatives receiver confirms requests for actual towerops.py, advisory_options.py and the Pyodide WASM asset. Both receiver files remain byte-exact against the originals in the frozen repository.

## What the inherited controls establish

The alternatives controls choose and approve a real native option, then explicitly load an identical scenario. File review preserves the approval; Load clears the selected proposal, approval and previous selectable alternatives while keeping every saved scenario value unchanged. A fresh native review still offers a usable proposal requiring new approval. The second control loads a changed world version and verifies that its previous alternatives are also invalidated.

The raw-draft controls review scenario B, author a valid and distinct world C, save live A, then apply B while preserving literal C and honest load feedback. They review A, explicitly export live B without canceling that pending review, then apply A with pristine feedback. Actual Save downloads and the live register establish which world is active.

The second raw-draft control performs the genuine File.text read of a chosen scenario and holds only delivery of its resolved text. A successful same-value raw Load invalidates that pending read. Releasing the genuine result cannot reopen the stale review; the final actual download stays identical to the normalized initial scenario.

## Source and runtime custody

The root's nominated source/build manifest SHA256 is **c7a2fd2cee35e79b69fb74a520b15de0b2d697756ea60ac9b2ad68cbd86a2301**. Independent preparation verifies its 1,017 source files by byte count, SHA256, Git blob and executable mode, and all 16 build assets by byte count and SHA256. Those checks pass before execution and after each receiver. The receiver copies and their original repository files remain exact. Inputs are rebound through separate manifests in this packet; the JavaScript receiver bytes are unchanged.

The originals are retained in the composed repository under:

- docs/verification/scenario-alternatives-independent-cf5799f6d38b/independent_alternative_reset.mjs
- docs/verification/scenario-raw-draft-pr48-replay-cf5799f6d38b/independent_raw_draft.mjs

Both runs use the existing Node 26.3.0, Puppeteer 25.12.0 and Chrome 154.0.8037.98 on the authorized Mac. Each has a new own output directory and disposable profile. The exact built page is served read-only on loopback. The receivers retain their existing deny-external proxy and, for the specific pending-read control, the documented File.text completion hold. Browser background proxy attempts are preserved separately from application requests. This is local receiving, not public Pages or account qualification.

No dependencies, source worktrees or build assets were copied or installed. Only the two completed profiles created by these runs were removed after their browser processes exited, with the cleanup recorded. Downloads, fixtures, logs and images remain exact. The separate frozen 19-file playback/radar packet and prepared public Pages receiver were not changed.

## Compact evidence

qualification-summary.json has every executed command, result, receiver pin and source/build readback. preparation-receipt.json gives the exact original-to-copy receiver mapping.

receiving-archive.json.gz preserves every raw output, actual download, chosen fixture, input manifest and exact executed receiving/setup script. UTF-8 text is decoded from bytes and re-encoded without newline conversion; the manifest verifies byte count, SHA256 and Git blob for each member. Python setup drivers are explicit .py.txt transcripts of the executed bytes and do not add discovered Python modules or lint exceptions. The three original PNGs are unedited and were visually inspected.

Run `node restore-replay.cjs receiving-archive.json.gz archive-manifest.json NEW_DIRECTORY` to verify and restore the exact archive members. Replay then uses the unchanged commands in qualification-summary.json with paths rebound to an independently reconstructed source/build and its matching manifests. No prior receiving result or source packet is overwritten.

These controls were each executed once on this nominated composition. Subsequent publication assembly, full project gates and actual normal Pages deployment remain separate boundaries.
