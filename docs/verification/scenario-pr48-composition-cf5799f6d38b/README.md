# Scenario files on the maintained PR48 and PR50 source

This companion preserves the scenario feature on the maintained advisory-options implementation, including the narrow correction that clears old alternatives whenever a saved scenario is explicitly applied. It then carries that same Airspace source through the CLI-only PR50 merge at `53aa5048b6585aa08592d5513cfcf555a8bba018`. It adds receiving evidence; it does not change the seven qualified product files.

## Source custody

| Layer | Exact tree | Meaning |
| --- | --- | --- |
| Published historical scenario checkpoint | `464299ede19b44fdd1d0d8d8590c9a34e4896df5` | PR47 commit `e8f8fe37e31067c8dbd789577544525afca5e009`; its 328 evidence files remain byte- and mode-identical. |
| Initial PR48 composition | `f4bc1ce05953dde6a33cea8588033fea9e18c5c4` | 251 source leaves and 16 build assets. The maintained controls pass, while the independent same-value scenario-load control demonstrates stale alternatives. |
| Corrected PR48 product source | `74ca2a2c29e09eb3c9d0c8b896eb81afcc418993` | The separate two-file successor clears alternative state on each explicit scenario replacement. |
| Root full publication qualification | `cde965df1dc4a18a94443c386e48686dd6280073` | 579 source leaves, including all 328 historical evidence files. Normal project build assets are identical to the independently received successor. |
| PR50 composition baseline | `8c11186b1a3f6391879fb0aef14738487f09dc2a` | 589 source leaves over main `53aa5048`; all seven product paths, 328 historical evidence files and 254 unrelated base paths retain their exact modes, types and Git blobs. |

The final publication tree includes the new companion evidence on the last row. Its exact tree, file manifest and normal Ruff result are provided with the frozen publication handoff. The assembly stops at the named PR50 base.

The earlier source-only 188 frontend / 108 native qualifications remain historical receipts. They are not relabeled as results for either full publication tree.

## Receiving results

| Receiving boundary | Initial composition | Corrected product or full publication |
| --- | --- | --- |
| Maintained PR48 receiver, unchanged ten predicates | 10/10 | 10/10 |
| Independently authored alternative lifecycle controls | 1/2; same-value explicit scenario Apply could revive an old alternative | 2/2 |
| Earlier independent raw-draft controls, unchanged replay | Not a new baseline run | 2/2; inherited coverage, not two new predicates |
| Root regression receivers | Earlier versions remain preserved in historical evidence | All 53 existing controls pass across nine receiving families |
| Root normal project gates on 579 leaves | Not applicable | 201 frontend tests, 120 native tests, zero skips; all 19 commands exit 0 |
| PR50 composition native/build gates on 589 leaves | Not applicable | 145 native tests pass, one explicit macOS `/dev/full` skip, zero failures/errors; normal Ruff, reference check and production build exit 0 |

The PR50 replay does not rerun frontend or browser predicates: all 16 production assets are byte-identical to the previously received build, and the PR50 delta is outside Airspace. Its `WorldPlanProcessReceiving.test_output_io_failure_does_not_claim_a_successful_review` control requires the native full-output device (`/dev/full`) and was explicitly skipped on macOS; this is preserved as a coverage limit, separately from the earlier 120-test result. The exact native/build packet is indexed by [its original manifest](provenance/pr50-original-manifest.json).

The stale-alternative counterexample did **not** show an approval bypass: the old approval was cleared and Readback remained disabled. The corrected source also prevents the old selection from reviving a pending proposal without another alternatives review. The maintained ten predicates alone did not cover this lifecycle boundary; the separate independent packet retains both the failure and the unchanged successful replay.

See the exact maintained, alternatives and inherited raw-draft packets:

- [Maintained PR48 receiving](../scenario-pr48-maintained-cf5799f6d38b/README.md)
- [Independent alternatives review](../scenario-alternatives-independent-cf5799f6d38b/REVIEW.md)
- [Inherited raw-draft replay](../scenario-raw-draft-pr48-replay-cf5799f6d38b/REVIEW.md)
- [PR50 native/build qualification](../scenario-pr50-native-receiving-cf5799f6d38b/README.md)
- [Root full-publication results](root/qualification/gates-summary.json)
- [Root normal-build identity comparison](root/qualification/build-identity-comparison.json)

Native receiving used the pinned Mac runtime: Node 26.3.0, Chrome 154.0.8037.98, Python 3.12.8, Ruff 0.16.10 and the existing browser dependencies recorded in each packet. The maintained receiver used Playwright 1.63.0; the independently authored browser probes used the recorded Puppeteer runtime. The normal build contains 16 pinned files. These receipts do not assert hosted CI runtime parity or that the scenario feature has already shipped to Pages. Actual normal Pages deployment receiving is a separate post-merge boundary.

## Exact evidence and compact archives

The three original external peer manifests are copied unchanged under [provenance](provenance/). Their 32, 33 and 26 declared files retain their original repository paths and exact bytes/modes. Their own historical Python setup aliases were already explicit before this assembly.

[The root receiving map](provenance/root-receiving-map.json) binds every selected native root file to its published path, byte count, SHA256 and Git blob. Seven unchanged receiving scripts are reused from their exact existing PR47 paths and commit. Three unchanged screenshots and several already preserved patches/pins are also reused by exact blob. No receiver source is silently replaced by a similar file.

The two archive formats retain executed data rather than summarized results:

- [Command transcripts](root/exact-command-transcripts.json) contain all 66 root stdout/stderr files, including empty files. Encode each `content` string directly as UTF-8 without newline conversion, then verify its byte count, SHA256 and Git blob.
- [Browser artifacts](root/exact-browser-artifacts.json) map every actual downloaded file and generated fixture to exact content. Shared content is stored once by Git blob. `utf-8` means `content.encode("utf-8")`; `base64` means standard base64 decoding. `repeat-byte` means `bytes([byte]) * count`. The latter encodes the two executed all-space oversized negative fixtures exactly, avoiding 2.36 MB of repeated spaces. The assembly decoded and hash-checked every entry.
- All raw browser receipts remain standalone and byte-exact. New screenshots remain PNG files. Referenced unchanged screenshots remain at their historical paths.

Dependency trees, temporary Chrome profiles, complete captured worktrees and generated runtime bundles are excluded. Source and build manifests retain their identities.

## Setup failures and archival names

The root's initial ENOSPC observation, setup receipts, private profile cleanup receipt and subsequent successful qualification remain separate. The interrupted read-only fetch did not have a durably captured exit code, and is not described as a successful receiving run. The maintained receiver's incomplete pure-`093f88` checkout remains an unqualified setup attempt.

The final private publication assembly also preserved two setup failures. Its local shared clone initially lacked the staged tree's object reference; adding that reference exposed Git's nested-alternate depth limit for the three unchanged scenario modules. A separate continuation flattened only the private clone's references to already authorized local object stores. It then materialized all 589 leaves successfully and verified the historical, product and unrelated base paths. No peer source, dependency installation or service was changed.

Exact executed setup/qualification drivers are archived with explicit `.py.txt` names. The mappings record their original native names, published names, byte counts, SHA256 and Git blobs. These names are transport labels for historical drivers, not a claim that the files are newly qualified Python modules. The existing six-path historical Ruff policy remains unchanged; this companion introduces no lint exceptions.

## Reproduction

Use the pinned repository commits and trees in the table. The final source and evidence must be composed from main `53aa5048`, the seven exact `74ca2a2c` product leaves, the 328 historical evidence paths from `e8f8fe37`, and this companion's declared additions. Compare the resulting tree with the frozen publication manifest.

The [root command receipt](root/qualification/process-receipt.json) records the exact normal build, frontend/native tests, Ruff, reference check and nine browser invocations. The [receiver map](provenance/root-receiving-map.json) identifies the seven reused scripts by published commit/path and hash. Adapt only temporary checkout/output paths for a new run; retain the receiver bytes and their predicates. Each independent packet documents its own original public controls and isolated output locations.

For the final publication gate, run the repository's normal `ruff check .` command on the actual assembled tree, without additional ignore flags or policy changes. Keep new receiving output outside the source checkout and verify the source/build identities before and after any subsequent browser run.
