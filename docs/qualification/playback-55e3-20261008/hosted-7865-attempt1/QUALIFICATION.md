# Hosted receiving: 7865 artifact identity mismatch

The single receiving attempt stopped at the served document's SHA-256 check. **Chrome was not launched and no hosted playback case ran.** This is a delivery identity mismatch against the selected artifact, not a playback regression or a successful hosted qualification.

## Exact deployment basis

The input binds merge `7865ffeda311b711b13f2d04fedeeef5c432017e`, tree `878ecf58ab8a99c77331aa99ff1278b902f3aa75`, and all 60 qualified native source blobs. Actions run `37798915263`, attempt 1, completed its build job `113385586679` and deploy job `113386069706` successfully. The deploy payload selected `github-pages` artifact `11560420141` and returned `http://jacobmetoyer.com/TowerOps/`.

The parent obtained the exact artifact through authenticated first-party file materialization after preserving a denied direct CDN request. The ZIP is 6,449,591 bytes, SHA-256 `516bbc7a96dc242c023bf2d7cb221e5e5ecab8fe79d6c93e2a0167cf204642a5`. Its inner tar is 14,581,760 bytes, SHA-256 `75507f6ab70dfea89af916c8db9dc48139c4278e24b5d33bf04f68ca5024e9e8`. The map contains 17 regular files: 16 app files and `.nojekyll`. The exact input is included in the raw packet, SHA-256 `92dc59d6c2c50731ed3b8380537bb9ac20fd02f72320b635130dc531d1a1d95a`.

## Actual receiving outcome

The receiver made one GET to `http://jacobmetoyer.com/TowerOps/airspace/` at `2026-10-08T16:02:05.664Z`. It received HTTP 200 directly, with no redirect. Both expected and received document sizes were **15,485 bytes**.

| Observation | Value |
| --- | --- |
| Expected artifact document SHA-256 | `5552cd180541440bffe40b13257ad985f9c86a848bbffcad7e4a41d094daae60` |
| Received document SHA-256 | `ea6f785d08a05249dcdcb648f7d8a9fa24c1cbe05a21b618a2aeba151b38ee2e` |
| Last-Modified | `Thu, 08 Oct 2026 15:58:44 GMT` |
| ETag | `"6ac7bdb4-3c7d"` |
| Cache-Control / Age | `max-age=600` / `0` |
| GitHub request ID | `3358:1A9038:D2527:DBC2C:6AC7BE7D` |

The process exited 1 without a timeout. The input, receiver files and local qualified source/build remained exact. No JS, CSS or Python asset request followed the mismatch; there are no browser cases or screenshots. The document was streamed into its size/hash observation; a separate HTML body file was not retained.

The parent had observed newer main `5b3015567a01017245c5f715c1bce65e20a06138` before this request. That makes deployment advancement a possible explanation, but this attempt alone does not identify the returned document with that commit. A matching newer artifact is required for that attribution. No substitute bundle, alternate route or second hosted probe was used for this attempt.

## Receiver and evidence boundaries

The reviewed v2 receiver preserves the actual HTTP metadata, permits only bounded observed redirects on the same host/port without an HTTPS downgrade, and compares served bytes with the actual Actions artifact. It reuses the selected f116 Reset-after-3x and policy-auto-pause-at-2x case bodies unchanged. It moves SHA-256 computation over the same native canvas ImageData bytes into Node so the observer can support an ordinary HTTP origin. Those browser observations were not reached in this attempt. The prior native 147-test/build and desktop/mobile results remain separate qualifications.

`receiving-text.json.gz` contains eight exact raw files: the three executed receiver files, deployment input, browser-stage report, process log, process receipt and hub inventory. `receiving-manifest.json` supplies original paths, lengths, SHA-256 and Git blob hashes. `v1-to-v2.patch` preserves the reviewed HTTP/canvas adaptation; the preceding receiver was not overwritten.

The separate hub inventory was observed at `2026-10-08 15:18:51 UTC`: five DESKTOP-LA7CMTA registrations were Online and ten older registrations were Offline. It used one RDC inventory call and zero hub commands. It establishes inventory reachability only, with no installed source, service state or live registration lease claim.
