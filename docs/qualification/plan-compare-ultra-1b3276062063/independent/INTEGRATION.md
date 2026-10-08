# Running the frozen independent review in ordinary CI

The eight supplied review leaves in this directory remain byte-for-byte
unchanged. Their SHA256 values are checked before execution by the ordinary
pytest-discovered function in `tests/test_compare_plans.py`.

That function invokes `independent_compare.py` in a fresh temporary child.
The frozen reviewer determines all27 API outcomes and22 actual CLI outcomes;
a timeout, missing receipt, nonzero exit or failed outcome fails the test.
The consumer's executed source SHA256 and unchanged-source result are checked.
No workflow, fixture, oracle or planner implementation is changed.

The regular `python -m pytest -q` job exposes two delimited records through
pytest's capture-control fixture:

- `TOWEROPS_INDEPENDENT_RECEIVING_JSON_BEGIN/END` contains the complete actual
  `RECEIVING.json` (or an explicit unavailable marker if the harness failed
  before producing it).
- `TOWEROPS_INDEPENDENT_RAW_ARCHIVE_BEGIN/END` contains one JSON envelope with
  stdlib zlib-compressed base64 JSON, both compressed and uncompressed SHA256
  values, and exact stdout/stderr/receipt file bytes represented as base64
  with individual lengths and hashes. This preserves raw process evidence
  without requiring an artifact-upload step or printing terminal controls.

Only direct regular files at the work root named `RECEIVING.json` or ending
in `.stdout`/`.stderr` are collected. The authored fixture directory, FIFO
and symlinks are not traversed or read by the collector. The harness separately
checks the complete authored fixture hashes after execution.

The directory-local Ruff configuration excludes only the two immutable
reviewer Python archives. Their historical style is retained as evidence;
product source and the maintained test wrapper remain fully linted. The
actual frozen receiving script still executes and must pass in CI.

At this checkpoint the ordinary corrected hosted run is pending. The sibling
review and earlier API receipt state exactly which executions already occurred.
