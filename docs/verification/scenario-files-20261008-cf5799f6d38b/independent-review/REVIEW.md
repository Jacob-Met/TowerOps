# Independent TowerOps scenario-file receiving review

## Disposition

The final source tree **d6b4a1ec5757144f848e1d6ce851a766a7413f2c**, composed over **09b96e31d2867af5b7a9738406d0431cf1010090**, passes the six independently authored browser groups and the unchanged pending-verification counterexample. There is no remaining blocker within this review's file-import, approval, selected-flight-edit, and audit-display scope.

The reviewer copied and independently built exact source bytes into private receiving directories, used fresh Chrome profiles and actual file chooser/download events, and exercised the bundled real CPython planner and ControlRoom gate. The final source's 136 manifest entries were checked against their Git tree and bytes; all 129 entries outside the seven feature paths preserve the current parent. Product source and dependency trees were not edited by the reviewer.

This is source receiving evidence. It does not establish installation, publication, a live serving revision, or a measured operational benefit. No real accounts, provider APIs, or production data were used.

## Two actual source findings and their closure

1. **Completed verification belongs to the discarded trace.** On tree 9d4d1320, a real plan, approval, and readback produce four audit events. Verify chain displays "HASH CHAIN VALID - 4 EVENTS". Choosing and explicitly loading a saved scenario empties the trace and clears the proposal/approval, but leaves that old verdict visible. This fails in both original and corrected-oracle browser runs. Tree 91131fb adds a synchronous verdict clear and passes the same display control.

2. **Pending verification crosses explicit scenario apply.** On trees 91131fb and the current-parent composition 317ddf06, the reviewer held the completion of exactly one genuine WebCrypto digest from an old four-event verification. The saved scenario was explicitly loaded while that result was pending. Loading correctly cleared the display; releasing the genuine result allowed all four actual hashes to finish, then repainted "HASH CHAIN VALID - 0 EVENTS" into the replacement scenario. No source, hash value, result, or audit event was substituted. Tree d6b4 captures the original AuditLog, events array, and count, and publishes the completion only if these still match. The unchanged counterexample now passes: all four old hashes complete and the replacement verdict remains blank.

The original source, intermediate source, raw failing receipts, and failed screenshots are retained. The source patches and source manifests reconstruct each reviewed candidate from its recorded Git parent without copying full source or dependency trees.

## Independent behavior controls

The unchanged final six-group receiver covers:

- The same world under stale, future, and fresh saved clocks reaches the actual CPython apply gate. Stale state (now=1012.75, observed at 1000) is refused with stale_state; future state (now=995) is refused with future_state; the fresh control (now=1002) applies and advances the world version from 1 to 2. Rejected controls preserve the world and saved scenario.
- Explicit scenario apply clears the previous proposal, approval, trace, and already completed verification display.
- Downloaded/imported bytes preserve all saved policy fields, clock, rate, aircraft ordering, selected aircraft, and negative zero. A subsequent selected-flight edit changes only the selected aircraft and advances the world version; the unedited aircraft and its signed zeros remain exact.
- Approving a proposal after reviewing a file invalidates the stale file review without erasing the valid approval. The stale load cannot apply and the existing native readback still succeeds.
- A delayed real File.text completion cannot publish an old file review after native readback changes the world.
- Starting a selected-flight edit invalidates a file review. Canceling the edit restores the user's draft fields and retains the current valid proposal/approval; stale file review remains disabled.

The seventh group is the unchanged real-digest completion-order counterexample described above. Final receipts report zero page JavaScript errors and zero requests from the app to external hosts. A local denying proxy observes and rejects Chrome background traffic; these blocked background attempts are separate from application requests.

## Result history and retained receiver corrections

| Source / run | Six-group result | Pending-digest result | Interpretation |
| --- | --- | --- | --- |
| 9d4d1320 / browser-v1 | 4 pass, 2 fail | Not run | One genuine stale-display finding and one incorrect review oracle |
| 9d4d1320 / browser-v2 | 5 pass, 1 fail | Not run | Corrected native freshness oracle; stale display still fails |
| 91131fb / browser-r2-v2 | No completed groups | Not run | Reviewer process stopped on its rejecting proxy's unhandled ECONNRESET |
| 91131fb / browser-r2-v2b | 6 pass | Fail | Synchronous display clear works; pending verification still crosses apply |
| 317ddf06 / browser-current-v2b | 6 pass | Fail | Current audit/numeric dependencies do not close the completion race |
| d6b4a1ec / browser-current-r2-v2b | 6 pass | Pass | Both demonstrated source findings closed |

The first clock oracle incorrectly assumed that AdvisoryPlanner.plan enforces world freshness. Reading the actual source located freshness at ControlRoom.apply. Receiver v2 changes that one group to exercise real approval/readback and records stale, future, and fresh outcomes; its five other predicates are unchanged. The original oracle failure remains in the packet and is not labeled a source regression.

Receiver v2b differs from v2 only by an error listener on the local rejecting CONNECT proxy's socket. The initial r2 v2 crash has no completed group receipt and is not counted as a product failure or success. Its exact process output is retained. No product source changed to repair either receiving issue.

## Replaying

The recorded runtime is native Node 26.3.0 and Chrome 154.0.8037.98 on the authorized Mac. The receiving package versions and private paths are in runtime-receipt.json. Bootstrap scripts show the exact manifest, tree, full-byte verification, dependency symlink, and independent build used for each source.

For a reconstructed and built final source, run with a fresh output directory:

    env NODE_PATH=/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules \
      REVIEW_SOURCE_TREE=d6b4a1ec5757144f848e1d6ce851a766a7413f2c \
      node review-v2b.mjs SOURCE NEW_SIX_GROUP_OUTPUT

    env NODE_PATH=/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules \
      REVIEW_SOURCE_TREE=d6b4a1ec5757144f848e1d6ce851a766a7413f2c \
      node pending-verification.mjs SOURCE NEW_PENDING_OUTPUT

The receiver serves only the built local source, uses a fresh profile, observes requests passively, and rejects background nonlocal requests. It does not use request interception, change the application, replace the Python worker, or bypass approval/readback. In the two delayed-completion tests, original file contents and original digest values are delivered unchanged after the controlled barrier.

## Packet layout and limits

- source-manifest*.json: exact source-tree metadata and byte/Git-blob pins for all four reviewed revisions.
- source-patches/: narrow seven-feature-file patches against each recorded parent.
- bootstrap*.py and bootstrap*-receipt.json: independently copied source, build, and composition checks.
- review*.mjs and pending-verification.mjs: exact receiver revisions and unchanged counterexample.
- receipts/: unmodified browser receipts, including old failures.
- screenshots/: failure-state screenshots for the original oracle, completed-verdict finding, and pending-verdict finding.
- process-output.json: exact UTF-8 stdout/stderr of every retained build and browser process, with file byte counts and SHA256 hashes.
- test-files.json: exact authored fixture and downloaded JSON bytes, with byte hashes; browser profiles and caches are excluded.
- final-source-readback.json and runtime-receipt.json: final receiving/source observations and runtime identity.
- review-manifest.json: all publication file byte counts, Git blob IDs, and SHA256 values.

The owner also reports broader authored test/build results in its own packet. Those are separate from these independently authored seven receiving groups and are not added to this review's count.
