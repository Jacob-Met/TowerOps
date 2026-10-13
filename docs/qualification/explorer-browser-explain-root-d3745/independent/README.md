# TowerOps — explain a saved mismatch in the browser

This worked project opens a saved synthetic export, identifies literal field differences from its local deterministic reproduction, and keeps the explanation attached to the file you selected. It does not infer a cause, establish provenance, or grant real-world authority.

## Open the actual feature

Use Python 3.12 or newer with its standard library. This receiving used Linux Python 3.14.4 and Firefox 157. From this qualification directory (or the extracted worked packet directory containing `candidate-source/`), run:

```sh
cd candidate-source
python3 explorer.py serve --port 8765
```

Open the loopback address printed by the server. If that port is occupied, choose another unused `--port`; leave other services alone. Ctrl+C in the launching terminal closes this server. No pip installation is needed for ordinary use.

Under **Replay exported JSON**, choose [B.json](fixtures/B.json). Wait for MISMATCH, then click **Explain this mismatch**. Ordinary replay does not automatically request explanations. The details open with one difference: `/after/version`, expected number 2 and actual number 3. Collapse and expand the details without requesting a new comparison.

Choose [C.json](fixtures/C.json) to see a type change, a missing field, and a literal Unicode key containing a slash and tilde. Click the explanation action again. Scroll within the page to the complete expected/actual values. The [actual complete panel](visual-C-v2/C-details-complete-panel.png) and [scrolled literal row](visual-C-v2/C-literal-row-scrolled.png) show this real product layout.

Choose [D.json](fixtures/D.json) for forty extra authored fields. The UI displays the first 32 ordered differences and says that more exist. The number is a presentation limit, not a claim that only 32 fields differ. Choose unchanged [A.json](fixtures/A.json) to return to MATCH; the mismatch explanation is retired.

The files are synthetic. A is the exact saved approved export from the earlier accepted selected-file browser course. B, C and D are clearly authored copies. They are useful controls, not real traffic or externally signed records.

## Read the differences

Each path is a JSON Pointer: `~1` represents a slash and `~0` a tilde. Each row labels the local reproduction as **Expected** and the selected saved export as **Actual**. A present value has its complete parsed JSON envelope, including its type and value. `{"present":false}` means the field is absent; it is distinct from a present null, empty string, false or zero.

For C, the expected ordered rows are:

| Path | Kind | Expected | Actual |
| --- | --- | --- | --- |
| `/after/version` | type | number 2 | boolean true |
| `/description` | missing | the original description string | absent |
| `/literal~1~0雪` | unexpected | absent | the complete authored object |

The third object's markup-looking string remains literal text. It is not interpreted as HTML. Its Unicode, quoted text, newline escape, null and array values remain visible in the full envelope. The explanation reports differences in parsed values; it does not preserve or compare original JSON whitespace.

## Current file and recovery

Selecting another file or clearing the file input immediately clears and closes the prior explanation. A response already in flight may finish, but it cannot restore old details or change the new selection's presentation. The button is disabled while the current explanation loads.

If a current explanation request fails, the existing replay verdict and displayed run remain intact. Correct the local cause and explicitly click the enabled explanation action to retry that same selection. This does not rerun a real-world operation. Running or exporting the displayed scenario remains a separate action.

The receiving course deliberately supplied one local relay HTTP 503 after saving the real production response, then retried the same C selection successfully. This fault was in the receiver; it is not a built-in product feature or a claim that the production handler failed.

## What actually ran

The original-first functional course used the actual Python production Handler and published browser assets through a transparent loopback relay. It forwarded the correct backend Host/Origin, retained every real backend body, supplied the one disclosed HTTP 503, and held the remainder of one otherwise exact response after flushing its headers and first byte. No successful response body was substituted.

The original fd0c5e829d89c9e88ac310ed237b74588fddfd09 course passed all 15 behavior/preservation comparisons: B produced MISMATCH, the explanation action was absent, and the additive endpoint returned 404. Its raw receipt remains accepted=false because the receiver sampled one socket in its Set immediately after the relay's close callback. The separate [closure audit](original-closure-audit.json) later verified the receiver, Python and Firefox PIDs absent, both exact ports unbound, and all 13 raw streams and inputs unchanged. It does not rewrite the original observation as zero sockets.

The frozen v2 driver changes only its version references and waits for socket close events after the relay close callback. The candidate course passed **85/85 comparisons**, with 18 actual HTTP requests including 13 POSTs. It checked the exact one-field and three-field envelopes, all 32 truncated rows, literal rendering, explicit same-file retry, old-response retirement after a newer MATCH, clearing, and unchanged run/export display. The held response's public requestfinished event was observed before the final stable check. Firefox and Python exited 0, the relay closed, and its final socket count was zero. All eight selected runtime files, controls and four fixtures remained exact.

The candidate receipt is [candidate-v2/receipt.json](candidate-v2/receipt.json), 689,799 bytes, SHA256 `ee3d0afd77da9bd6c6d3c37517956b4ad48ce1928c5f48774ddfcfdead584181`. The [custody audit](consumer-custody.json) separately recomputes those comparisons and binds all 33 candidate raw streams and four candidate screenshots. Original and candidate together retain 46 raw streams.

## Separate layout opening

The original 1440×1100 functional screenshots show the verdict, action, completion status and counts 1, 3 and 32+, plus the final retired MATCH state. Their value rows are below that viewport; the exact complete values in that course are established by DOM and HTTP observations.

A separate, post-exposure direct-production opening selected C and clicked the explanation action without running a new scenario. It passed 10 focused checks and captured the scrolled viewport, complete details panel and final literal row. The three rows are readable at 1440×1100: both columns remain within the page, the long description and literal object string wrap, absence is explicit, and the final row is fully reachable by scrolling. The [layout receipt](visual-C-v2/receipt.json) retains the DOM dimensions, complete envelopes, selected File text, two production POST paths/statuses, and clean browser/backend closure. It is distinct from the 85-check course and is not a mobile or cross-browser layout claim.

The first visual-only receiver used unsupported Firefox BiDi request.postData instrumentation and terminated before screenshots. Its [failure and cleanup record](visual-v1-failure-and-cleanup.json), original driver and versioned correction are preserved. That record proves the specifically identified owned Python process was removed; it does not independently claim full v1 browser closure. The corrected visual observer uses supported POST path/status observations and the actual selected File text. Complete backend/request bodies remain in the earlier functional course. No product files changed.

## Source, custody and reproduction limits

The public contract is [TowerOps issue 132](https://github.com/Jacob-Met/TowerOps/issues/132). The criteria were frozen before the root implementation. Both functional drivers and the original course were frozen/closed before candidate exposure. The exact candidate was then copied to an exclusive owned stage, with its published-style modes preserved. It was unpublished at receiving, based on 6991198cde605b683331290c8c898ac5dbec6643; that historical state remains in [candidate-spec-v1.json](candidate-spec-v1.json). Later publication/adoption is a separate binding, not a relabeling of the run.

The earlier original-source projection was frozen with mode 0644. A separate original-runtime projection preserved the same eight Git bodies and canonical modes, including explorer.py 0755; it was the original execution source. Both are retained, so that preparation history is explicit.

The descriptor preserves native file modes and separately selects Git 100644 or 100755. Browser-generated receipts and PNGs may be native 0664; repository projections normalize them to 100644 without claiming native-mode parity. Source bindings and the MIT [license](LICENSE) accompany the selected eight-file runtime, which is sufficient for ordinary Explorer use but is not the complete repository.

The raw harness/specs retain original absolute native paths and exact self/freeze identities. They are historical receiving evidence, not a promise that an extracted archive can execute those harness commands unchanged. Use the ordinary opening commands above for the worked project. Adapting a harness to another environment requires a separately recorded spec/freeze and a fresh absent output directory, leaving these receipts unchanged.

Page-level request observations do not constitute an OS network audit. The clear operation used an authored DOM value/change event, not native chooser cancellation. This is a bounded Linux Firefox receiving course, not the full test suite, all browsers, aviation safety assurance, or Jacob's subjective acceptance.
