# Use a saved request without replacing the displayed result

This is Anvil's independent original-first receiving evidence for TowerOps issue 138. The original source at `202782f29f3a0ed1411e67a7744f9e63f26926f1` passed **24/24 expected original observations**: replay worked and the new action was absent. A separately copied, reviewed but unpublished candidate passed **78/78 observations** with the unchanged frozen V2 receiver. This is one original browser course and one candidate browser course, plus three original CLI exports used as fixed inputs. No original or candidate browser course was repeated.

## Try the received behavior

From this evidence directory, enter the received candidate projection and start its local foreground server:

```sh
cd candidate
python3 explorer.py serve --port 0
```

Open the printed loopback URL. Choose **Approval + acknowledgement**, clear both fixture switches and click **Run synthetic case**. Export this displayed result if desired. In **Replay exported JSON**, choose the supplied `original-fixtures/B.json` from the evidence directory. Its request is **Missing acknowledgement**, with both request switches true. The scenario still withholds its acknowledgement fixture; the action copies the saved request booleans, not the effective fixtures.

After the current replay succeeds, click **Use request settings**. The scenario, both switches and description change, while the displayed result, its projection, export and replay verdict stay unchanged. The visible message explicitly asks you to use **Run synthetic case** to produce a new result. Clicking Run is the separate action that creates that new synthetic result. Press Ctrl+C in the terminal to stop the server.

`original-fixtures/C-mismatch.json` is the original Changed world binding export with only its label deliberately changed. It produces a literal MISMATCH yet still permits copying its admitted request. The accompanying `malformed.json` is deliberately invalid. New, pending, rejected or cleared file selections retire the settings action; controls already copied into the form are not undone. A late completion belonging to a cleared selection cannot restore the action. No live data, provider/model invocation, real-world clearance or installed-service operation is part of this evidence.

## What actually ran

| Course | Observations | HTTP | POST | Saved downloads |
|---|---:|---:|---:|---:|
| Original V2 | 24/24 | 7 | 2 | 2 |
| Candidate V2 | 78/78 | 16 | 7 | 3 |

The candidate ran from 2026-10-14T01:13:04.971Z to 01:13:11.444Z. The wrapper PID 520942 completed with exit 0. Its Node receiver 521009, Python backend 521016 and Firefox 521033 were subsequently confirmed absent. Context and browser closed normally, Firefox and backend exited 0, relay sockets drained to zero and both owned listeners were closed. No page errors, external requests or failed requests were recorded. The original course has its own unchanged closure and receipt.

Both courses used native ThinkPad Python 3.14.4, Node 22.22.1, Puppeteer 25.12.0 and Firefox 157.0. They launched an isolated real production Handler and recorded its exact bytes through a loopback relay. The only authored response delays were one genuine replay body after its headers and first byte, and one complete catalog response before headers. The receiver waited for the held response's unique public `requestfinished` witness before comparing the cleared state. GET `/favicon.ico` returned an ordinary 404; it is retained and is not described as a browser request failure.

The browser exercised MATCH and MISMATCH copying, request/effective-fixture distinction, nonzero projected times 2.3 and 4.1, exact display/export preservation, explicit subsequent Run, malformed selection refusal, pending and cleared selection retirement, obsolete completion refusal and replay-before-catalog readiness. Apply generated no HTTP request. There were exactly two explicit `/api/run` requests in the candidate course. The delayed-catalog page applied settings without running anything.

The candidate's first two actual downloads are byte-identical 4,296-byte A exports (SHA256 `177905514098eb15d079d4dcd887e925386de7c3aa387e80fedaee388bc1eb61`). Its third is the 4,946-byte B result (SHA256 `17f8d04417744939fc606c34259bb5ffb756b02f4db7153b7781fab9894ea147`), downloaded after copying C. The original two A downloads match the same A hash. Firefox's collision filenames are preserved in raw receipts and mapped explicitly to portable `-after-replay` and `-after-settings` publication names; there is no renamed-copy execution claim.

## Source and history

The original eight-file projection is authenticated against the complete baseline tree `90c81370fb3215943a8b64a4264f8e362a05d479`. The candidate was offered as an unpublished isolated change based on that commit, after root's full source review. Its app.js is 11,206 bytes / SHA256 `c01d9444d27634345127b3cff455b80cd00bfc36d579ed082fc92546bfff196c`; index.html is 4,063 bytes / SHA256 `e988e82953be3f9897d1c035d12a5f0128da188b3e777ca24eaae5e98446b45d`. The complete eight-body identities and original source paths are in `candidate-offer-v1.json` and the received spec. The spec deliberately has null publication commit/tree fields. Later publication must bind the same bytes without rewriting this execution history.

The V1 receiver was frozen and peer-reviewed before candidate exposure, then retained unexecuted. Forge found that a zero-minute snapshot would not detect an unintended reset to zero. V2 added only nonzero projection setup and its checks, plus version references. Both versions, exact patch, criteria and freeze records are retained. V2 was accepted before the original course and before any candidate body exposure. The original fixture producer ran only once; both browser courses used its same five preserved inputs. Candidate admission, private transfer custody and raw audits establish exact bytes and native modes before and after.

`original-course-review-v1.json`, `saved-course-audit-v1.json` and `visual-review-v1.json` are read-only follow-up observations. The saved-course audit recomputes all 102 comparison predicates and checks all 36 raw relay/backend streams, five downloads and three PNG identities. It does not add a product run. The full receipts retain actual/expected values, request and response text, source/control/fixture inventories and closure. No source mutation or installed command change was made by these receiving courses.

## Inspect or deliberately repeat the receiving process

Start with `criteria-v1.json`, `receiver-freeze-v2.json`, the two raw receipts and `visual-review-v1.json`. All captured responses, requests, downloads and screenshots are separate exact payloads. The receiver reads absolute paths from its supplied data-only spec and requires a new, absent output directory. The retained native commands were:

```sh
/usr/bin/node /home/jacob/hamon/receiving/anvil-d3745-towerops-settings/receive-settings-v2.cjs /home/jacob/hamon/receiving/anvil-d3745-towerops-settings/original-spec-v1.json /home/jacob/hamon/receiving/anvil-d3745-towerops-settings/original-browser-v2 original
/usr/bin/node /home/jacob/hamon/receiving/anvil-d3745-towerops-settings/receive-settings-v2.cjs /home/jacob/hamon/receiving/anvil-d3745-towerops-settings/candidate-spec-v1.json /home/jacob/hamon/receiving/anvil-d3745-towerops-settings/candidate-browser-v2 candidate
```

Those original output directories already exist. These lines document execution, not a command to overwrite evidence. A fresh environment requires its own explicit spec, admitted runtime/browser dependencies and new output path; none of the extracted-copy receiving commands was rerun for publication. The simple source launch above uses the retained eight-file runtime projection. No broad legacy suite, mobile layout course, live service or later installed release is claimed.
