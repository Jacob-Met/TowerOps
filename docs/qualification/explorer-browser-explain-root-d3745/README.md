# Explain the current saved-file mismatch in the Synthetic Explorer

This increment makes the already adopted literal replay explanation available beside the current browser verdict. After a selected export completes with MISMATCH, **Explain this mismatch** compares that captured parsed value with the local synthetic reproduction. It does not replace the displayed scenario or its export.

## Use the maintained application

From the repository root, with Python 3.12 or later:

```sh
python3 -B explorer.py serve --port 8765
```

Open the printed loopback URL. Run **Approval + acknowledgement**, export the result, and keep that original. In a separate copy, change `after.version` from 2 to 3. Select that copy under **Replay exported JSON**, wait for MISMATCH, then choose **Explain this mismatch**. The field comparison identifies `/after/version`, expected number 2 and actual number 3. Expand or collapse **Field differences** without sending another comparison.

Each row shows a JSON Pointer, a difference kind and complete expected/actual JSON envelopes. `present:false` means absence; a present null includes `present:true,type:"null",value:null`. Values are literal parsed JSON. Source formatting and numeric spelling are not preserved. Up to 32 ordered rows are shown; a separate notice says when another difference was observed. These differences do not infer a cause or authenticate an export.

Changing or clearing the selected file retires old details and pending responses. A current comparison failure preserves its mismatch verdict and permits an explicit retry. Match, invalid input and pending ordinary replay do not offer an old-file explanation. An already sent request may finish after retirement. The ordinary run display and export remain independent.

See [the application guide](../../../EXPLORER.md) for the existing synthetic-model and HTTP limits.

## Exact source boundary

The authored base is `6991198cde605b683331290c8c898ac5dbec6643`, tree `bf63ce7b3ac761bf02c9184747575f989a2876ab`. The reviewed 12-file source packet is 99,606 bytes with SHA-256 `bc4450944a7aa7170e963af8f98e912283f17ae0df22b72f86f399ab9ef1b171`.

The publication uses an explicit eight-path source allowlist: `explorer.py`, `web/app.js`, `web/index.html`, `web/style.css`, `EXPLORER.md`, the narrowly adapted existing replay-selection test and two new explanation tests. Six existing paths change and two test modules are added. The four unchanged packet closure files—`replay_explain.py`, `scenarios.py`, `towerops.py` and `test_explorer.py`—remain inherited repository files.

The additive `/api/replay/explain` dispatch reuses the unchanged helper through the existing local request admission. Ordinary replay, run, CLI, body cap and request framing are preserved. The browser captures the accepted selection, renders text nodes and complete side envelopes, and guards success, failure and final control restoration against a retired selection.

The old Node selection test excludes only the newly introduced replay widgets from its unrelated-display snapshot. Its original selected-file, stale-response, refusal and recovery assertions remain intact.

## Recorded qualification

These are distinct courses, not one aggregate suite:

| Course | Recorded result and scope |
| --- | --- |
| Author native controls | Five commands, 31 passing test executions: four HTTP methods normal and four with true child optimization, five new Node methods, ten retained selection methods and eight legacy methods. All 12 source bodies/modes preserved. |
| Original actual browser | Fifteen behavior comparisons passed: real MISMATCH, no explanation action and actual endpoint 404. The raw receiver receipt remains `accepted:false` because its socket Set was sampled at one just after relay close. A separate later read-only audit records closed processes/listeners and unchanged artifacts. |
| Candidate actual browser | Frozen v2 receiver, 85 comparisons, 18 HTTP requests and 13 POSTs; browser and backend exit 0, relay closed with zero sockets. Exact literal fields, explicit failure/retry, 32-row notice, delayed old-result retirement, clear and user collapse/expand were observed. |
| Separate saved-C layout opening | Ten checks and two direct-production POSTs; full three-row panel visually inspected at 1440×1100, all six value sides wrap within their columns and the final literal row is scroll-reachable. No horizontal page overflow observed. This post-exposure opening is separate from the frozen behavior course. |
| Independent source/receiving review | Anvil authenticated all ten original source bodies against the complete connected base tree, read the scoped production/test changes and recomputed all 100 original/candidate comparisons. All 46 raw streams and source/control/fixture/screenshot identities were independently checked without replay. |

The browser course runs the actual Python Handler behind a loopback relay that captures backend bytes. The relay supplies exactly one disclosed HTTP 503 after a valid backend result and delays one otherwise exact explanation after headers and its first body byte. It forwards local Host/Origin for that controlled route. This does not qualify every raw request-framing case or a remote deployment.

The source was frozen and unpublished when consumed. Later source publication is an additional binding; it does not rewrite the recorded execution identity. Original v1, revised v2, the raw false receipt and the later closure audit remain separate. V2 changes only version references and bounded waiting for actual socket-close events after the relay close callback.

The retained B/C screenshots show the mismatch, action, completed status and open details counts. Their row values are below the fixed viewport; complete typed and literal values are evidenced by DOM/HTTP receipt observations. A later separate saved-C visual opening captures the scrolled viewport, full panel and final literal row. Its v1 observer failed on unsupported Firefox BiDi `request.postData` before capture; that failure remains retained. V2 uses supported POST path/status and exact selected File text, and records ten passing checks, wrapping and scroll reachability. This later observation does not rewrite the earlier 85-check result. File selection uses the browser API; clearing is an authored DOM change. Network claims concern page requests, not an OS-wide audit. No model/provider operation, stored upload or live aircraft control occurs.

## Publication admission

Original author evidence and Loom's original independent descriptor remain separate authorities. The source subset comes from the original frozen packet through an explicit eight-path list. Supporting guides and reviews are separately admitted under this qualification prefix. No substring matching selects source roles.

The maintained `prepare_git_objects.py`, `receive_source.py` and `validate_publication_layout.py` are pinned together at `Jacob-Met/estate-push-tools@c00eadc94f81d2e8608a6e8a23bcfa9b201646a6`; their bodies match the previously reviewed gate. The plan must pass the exact source/support/original-descriptor union before Git tree, commit or ref publication. Fresh complete-base preservation and ordinary review remain separate gates. No GitHub Actions are requested.

An initial cloud-only attempt to write a small source authority hit ENOSPC and left a zero-byte file; it was never admitted. Assembly moved to Anvil's newly verified exclusive native stage. Original author and consumer stages are read-only inputs. Historical receipts are not rewritten.
