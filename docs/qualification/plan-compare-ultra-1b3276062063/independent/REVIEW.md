# Independent saved-policy comparison receiving

## Frozen before candidate exposure

The root reviewer fetched the existing producer modules directly from their immutable Git blobs, authored synthetic worlds and comparison expectations, and executed the unchanged producers with native Mac Python3.13.7. The fixture packet was frozen at `2026-10-08T17:13:23.133055+00:00`. Candidate source was first exposed at `2026-10-08 17:21:55 UTC`.

The native baseline uses the documented three-aircraft world with world SHA256 `ae8ce380ecdddcef10cedfcdd46fcd601d9b6bdef5d33f90c4f531c2a5ed7150`. The5NM policy has66 alternatives from74 candidates. The6NM policy has62 alternatives, with62 retained identities,4 left-only identities and54 changed absolute saved ranks. The3NM policy changes a policy value while preserving all66 original body identities in order. A0.1-minute horizon produces the original empty no-conflict report.

The frozen27 cases cover those comparisons, byte-format and aircraft-order variation, saved-rank rotation, a changed full advisory body with the same maneuver setpoints, exact policy numeric types, an empty world, changed clocks/worlds including integer/float and signed-zero identity, malformed bodies/hashes/status/counts/flags, duplicate JSON keys/advisory identities, non-finite numbers, invalid UTF-8 and the4MiB bound. Fixture expectations are materialized before candidate loading. The complete fixture packet SHA256 is `617776a8e17779c24b09405e483490b8df4f078d9e1f67e4d96757e407e7ae82`.

The CLI harness additionally covers text output, missing and directory input, direct and dangling symlinks, a FIFO and Linux output-device failure. Together with15 selected complete-report vectors this is22 actual process invocations. All input byte hashes are checked again afterward. At packet creation these CLI processes remain prepared but unexecuted.

## Actual API receiving

The exact published candidate `compare_plans.py` Git blob `5a078563e5fe0c588f63aafb5a8cfd709ab341fd`, SHA256 `6130e332cea63f42e34aaf86fe50c72ac6c6212372368409914ba3e6c554ba75`, passed all27 frozen API cases on cloud-local Python3.12.14 at `2026-10-08T17:31:13.830369+00:00`. The original fixture builder and producer blobs regenerated the exact frozen fixture packet; its full SHA256 was checked before candidate loading.

An audit hook recorded zero filesystem/process/network effect attempts during candidate receiving. Explicit sentinels recorded zero planning, screening, actuation or native audit calls. Full report/body hashes, policy values, membership, original ranks, source-byte identity, world numeric representation and refusal outcomes matched. The actual receipt is `CLOUD_API_RECEIVING.json`, SHA256 `667a3954198b808e73873ede3154c1b7b2824d553568b1cb51b4c9ba276beb76`.

This is cloud API acceptance, not a native Mac CLI or hosted GitHub file-boundary result. The source coordinator separately has the source review and AST-equivalent formatting successor. The hosted receiving records the exact module SHA256 actually executed.

## Negative orchestration evidence retained

A later Mac candidate API request timed out without a PID or output; its result is unknown. It is not reported as an executed failure or a pass. No retry was made.

The first cloud attempt reached receipt construction but `platform.platform()` attempted a subprocess-related metadata probe and was stopped by the no-effect audit hook. The original traceback is preserved. The corrected orchestration uses `sys.platform` and `os.uname().machine`; it changes no candidate code, frozen fixture or harness oracle. The corrected run above has its own complete receipt. An earlier fixture-filename typo in the not-yet-executed CLI harness was corrected before the native pre-candidate freeze; the final frozen hash is the one in `PRE_CANDIDATE.json`.

## Hosted receiving

Keep all sibling files together. From the repository root, run:

```sh
python3 -B docs/qualification/plan-compare-ultra-1b3276062063/independent/independent_compare.py --source compare_plans.py --fixtures docs/qualification/plan-compare-ultra-1b3276062063/independent/fixtures.json.zlib.b64 --work "$RUNNER_TEMP/towerops-independent-comparison"
```

The work path must be new. The harness writes `RECEIVING.json` plus exact stdout/stderr per CLI process. Its exit status is nonzero if any API or CLI case fails. Preserve the actual receipt. Any artifact collector must lstat-skip the intentionally authored FIFO and symlinks; do not dereference them or read them as ordinary files. The compressed fixture text restores exact authored bytes and has no pickle or executable payload.
