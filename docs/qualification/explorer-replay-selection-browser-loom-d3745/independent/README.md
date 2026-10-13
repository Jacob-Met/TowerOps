# TowerOps replay selection — actual browser receiving

The replay verdict now belongs to the most recently selected file. A slow reply for an earlier file cannot overwrite a newer file's verdict. Clearing the file input retires the pending presentation and leaves the verdict blank. The displayed simulation and its export remain separate from replaying a saved file.

This supplement contains two usable saved fixtures, exact source copies, the original and candidate receipts, six retained screenshots, and the frozen receiver. It complements the [earlier source/Node opening packet](https://docs.google.com/document/d/1WM2VMQqntAXst8adCA0fg6cduYY0R1mqxYMPi9YLhNs/edit); that immutable packet's browser-pending and missing-body disclosures remain historical facts.

## Open the worked example

From this directory, with Python 3.12 or newer, start the normal local Explorer:

~~~sh
python3 -B candidate-source/explorer.py serve --port 8765
~~~

Open http://127.0.0.1:8765 and choose the approval-and-acknowledgement scenario, then Run. Under the saved-export replay file input, select either of these files:

- [export-A.json](candidate-v2/fixtures/export-A.json) is the exact native approved export. Replay reports MATCH.
- [export-B.json](candidate-v2/fixtures/export-B.json) is a deliberately changed local control. It differs in parsed content only by incrementing A's after.version by one. Replay reports MISMATCH.

Select B after A to inspect the current selected-file verdict. The automated course below deliberately delayed A to establish the race; an ordinary local selection may complete too quickly to reproduce that overlap. Cancelling a file chooser is not necessarily a clear-selection change. The receiving course cleared the input value and dispatched an ordinary change event explicitly; it does not claim a separate native chooser clear interaction or a new Clear button.

Stop the local server with Ctrl-C when finished. The files and UI describe a synthetic research simulation: fixture identities, approval and acknowledgement are local test inputs, not real authorization, provenance proof, an aviation assurance claim or live aircraft control.

For a direct native replay without opening the UI, run:

~~~sh
python3 -B candidate-source/explorer.py replay candidate-v2/fixtures/export-A.json
python3 -B candidate-source/explorer.py replay candidate-v2/fixtures/export-B.json
~~~

A returns JSON with matches=true and exit 0. The deliberately changed B returns matches=false and exit 1; that exit is the expected control result.

## What the actual browser established

The two courses used headless Firefox 157 on hamon-thinkpad, with Node 22.22.1, Puppeteer 25.12.0 and Python 3.14.4. Each source variant ran three real unchanged native CLI commands: export approved, replay A, replay B. Their stdout and stderr are retained separately under each course's streams directory. The browser loaded exact HTML/JavaScript/CSS source copies and selected the two actual files through its public file-input interface.

An authored loopback HTTP server served those exact assets and the actual CLI-produced run/replay bodies. It flushed JSON headers and the first body byte for the old A reply, holding the remainder until the newer verdict or explicit clear was observed. A public browser requestfinished event for that labeled response then proved completion before the final two-frame plus 150 ms observation. This exercises the frontend with controlled transport backed by the real native CLI; it is not a qualification of the production Python HTTP server's framing.

| Course | Original observed result | Candidate observed result |
|---|---|---|
| Select A, hold its reply; select B and observe MISMATCH; finish old A | The file input still names B, but old A replaces its verdict with MATCH | B's MISMATCH remains |
| Select A and hold its reply; explicitly clear input; finish old A | Replaying remains immediately after clear; old A later writes MATCH | Blank immediately and after old A completes |

The candidate [raw receipt](candidate-v2/receipt.json) has 23 passing comparisons, no failed comparisons and accepted=true. Its final statuses, request counts, unchanged full run display, unchanged export availability, exact source/control/fixture identities and clean closure all agree. The newer-file course made one run POST and two replay POSTs; the clear course made one run POST and one replay POST. Each old-response completion was observed exactly once. Both original and candidate browser/server processes closed with zero recorded remaining sockets.

See the three representative images in [visual-review.json](visual-review.json):

- [Original: old A overwrote B's verdict](original-v1/newer-file-after-release.png).
- [Candidate: B's MISMATCH remains](candidate-v2/newer-file-after-release.png).
- [Candidate: cleared input remains blank](candidate-v2/cleared-file-after-release.png).

All six captured images remain in the two course directories. The candidate newer-file images before and after old A's completion are byte-identical. These are retained 1280 × 1000 captures; no additional rendering, mobile, accessibility or broad browser-compatibility claim is made.

## Original failure and corrections remain visible

The [original v1 receipt](original-v1/receipt.json) remains byte-for-byte accepted=false. It contains 23 comparisons with three intended product behavior failures and two additional logger classification failures. The intended failures are newer-file.final-status, cleared-file.immediate-status and cleared-file.final-status.

The two extra flags came from an identical inline data:font/woff2;base64 resource, one observed on each page, being classified by v1 as an external origin. The [separate audit](original-inline-classification-audit.json) retains both full URLs, verifies their identical 1,180-byte WOFF2 bodies, recomputes all comparisons and authenticates the raw streams and retained files. Root independently decoded those URLs and accepted the original behavior without rerunning it or rewriting its receipt.

The [v2 patch](receiver-v1-to-v2.patch) only versions the receiver/freeze references and retains data-protocol observations in inline_requests. Every other URL outside the exact loopback origin still fails the external-request check. Status, request count, response completion, preservation and closure assertions are unchanged. Candidate pages have no recorded remote-origin request, page error or failed request. This is a page-observation claim, not an OS-level network audit.

The [original mode note](original-mode-adaptation-note.json) corrects an initial staging annotation: the original copier set explorer.py to 0644 although its published Git mode is 100755. Original specs and receipts accurately retain the actual 0644 mode. Both courses invoked it explicitly with Python, so no executable-bit behavior was tested. Candidate explorer.py retains 0755. Original files, staging receipt and raw course have not been relabeled as canonical-mode or direct-launch parity.

## Exact source and receiving order

The original source is [c7714bbe09c37ead994780af53078df11c99925b](https://github.com/Jacob-Met/TowerOps/commit/c7714bbe09c37ead994780af53078df11c99925b), tree 1614130c0adce082b065e4f59cc5fd359e90083d. The candidate is [67cc9807c096f3e4b6f7b1155008294415f31d23](https://github.com/Jacob-Met/TowerOps/commit/67cc9807c096f3e4b6f7b1155008294415f31d23), ordinarily adopted through [PR127](https://github.com/Jacob-Met/TowerOps/pull/127) as [8a87ad1331d7e7100367dde583d59560836f9eb8](https://github.com/Jacob-Met/TowerOps/commit/8a87ad1331d7e7100367dde583d59560836f9eb8). Head and adoption share tree ffacbb9ace1a360d0aeca2bdb33b70e0c0422418.

[source-binding.json](source-binding.json) binds the exact eight selected source files per variant to the published Git leaves, including the original mode adaptation. The candidate projection is a runnable Explorer subset, not a whole-repository checkout. LICENSE is retained unchanged. The authored fixture/control/evidence files have their own identities and are not upstream product source.

Criteria and v1 driver were frozen from the public contract and original source before candidate implementation exposure or browser execution. The original course completed before candidate receiving. V2 was frozen after the original logger issue was understood; candidate source identity metadata was known, but its implementation remained unread and unexecuted at that point. Root accepted the original behavior audit and narrow v2 change before releasing the candidate source for the single candidate course. The exact original freeze, v2 freeze, failed receipt and successful receipt preserve this sequence.

The original raw receipt is 120,014 bytes, SHA256 5c28983527d227348a2cea476e0dc6a917ce0fbe7c5c2774c161dfc20b3e485f. Candidate raw receipt is 117,788 bytes, SHA256 b55d3c4fe12dedb0e95c8058b49530c0d47fd49b2a9061912ce3f53b78e54a38.

## Optional receiver replay

The normal-use commands above need only Python and the source subset. Replaying the authored browser course additionally requires compatible Node, Puppeteer and Firefox installations. The retained specs name the original machine's absolute paths and must not be used blindly on another machine.

Make an adapted copy of candidate-spec.json with absolute source_path entries pointing to your extracted candidate-source files, and set python, browser_module and browser_executable to your verified runtime paths. Preserve the admitted bytes, SHA256 and source modes. Keep the receiver, criteria.json and freeze-v2.json adjacent and unchanged. Choose an absent absolute output directory:

~~~sh
node receive-replay-selection-v2.cjs /absolute/adapted-candidate-spec.json /absolute/new-replay-output candidate
~~~

The driver creates only that new output and its fixtures, streams, profile and screenshots; it refuses an existing output directory. Such an adapted execution would be a new result. This delivery did not replay the extracted package or rerun the original course after correction. Broader file-text failures, server errors, cancellation, different browser engines and all author Node controls remain outside these two actual browser courses. The earlier Node qualification is a separate accepted result.
