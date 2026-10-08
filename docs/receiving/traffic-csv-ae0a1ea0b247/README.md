# Synthetic traffic CSV receiving

Contribution: TowerOps issue52; central scope HAMON140 comment6062707452.

The converter is five source/test/example/documentation leaves, with only an additive README section modifying an existing path. The native parse_world, WorldState, planner, approval and actuation sources remain unchanged. This is a new input workflow for synthetic research traffic, not an operational assurance claim.

Discovery and actual execution used native base `53aa5048b6585aa08592d5513cfcf555a8bba018`. Receiving parent `687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8` integrates the separately owned playback work. All three execution dependencies, original planner test/conftest, root README and workflow remain byte-identical; no new run is inferred from this source-only receiving comparison.

The initial real native baseline admitted equivalent JSON and refused CSV at JSON parsing. Its receiver wrongly expected a conflict beyond the default five-minute horizon and stopped at that assertion; original driver/result, actual diagnostic and the one-line expectation correction are preserved. The corrected original-source control passes. That is a receiver mistake, not a product failure.

The author ran all 12 focused converter groups, then the combined native planner/converter suite: **34 tests and 43 subtests passed**. Ruff passed after a sole parameter-annotation diagnostic was corrected. The command tests use actual subprocesses, native parsing/hashes/planning and synthetic files. They cover complete stdin/file delivery, order/BOM/quoting, exact type/signed-zero semantics, empty worlds, refusal without a valid prefix, native bounds, input preservation and flush failure. No browser run is claimed.

The independent reviewer froze its spreadsheet/expected native world before candidate disclosure. Its unchanged driver passed **four groups / seven actual child processes**: reordered BOM/CRLF/quoted cells and exact native types; byte-identical reordered stdin; unchanged planner with independently expected hash `fddfc5a2429219fbfec71a7804874b13677615aea5fc42068854b140fe5c0a20`; four late-row failures with no stdout and unchanged source files. Its exact archive SHA256 is `48da44d641b1f09adb569f05be47f3fb079990a43916b97660c9c6b18b9aec3b`; all original fixtures, driver, expectation, source, output and review are retained inside. No implementation defect or additional broad suite was reported.

The native PR records full-tree overlay, hosted CI and actual merge separately. No installed program, provider, live aircraft, account, UI owner scope or workflow configuration is changed.

The first hosted full-repository lint run found import-format/unused-import diagnostics in the historical baseline receiver, which is retained verbatim rather than rewritten. Its exact original bytes now reside in `baseline/original-driver.py.txt` as a historical source transcript; run `python baseline/original-driver.py.txt` to reproduce the original assertion stop, or copy the transcript and apply the retained one-line correction for the accepted baseline control. This packaging correction changes no product or test source and no lint/workflow configuration. `packaging-correction.json` retains the exact failed native job and diagnostics.
