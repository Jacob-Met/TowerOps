# First hosted native receiving and minimal correction

This stage retains [ordinary push run37812639867](https://github.com/Jacob-Met/TowerOps/actions/runs/37812639867) on exact published head `1a71f19dfbc1eb89c05baecd2e2f49bc6e6e0613`. Ubuntu24.04 / Python3.12.15 executed170 tests: **169 passed, one failed**. The unchanged declared adapter imported successfully. This original run remains a failure, not a relabeled pass.

## The real failure

The new CLI receiving test supplied the original producer argument `--horizontal-nm 6`. That producer correctly preserves JSON integer6. The comparison printed the exact saved difference `5.0 -> 6`; the receiving assertion incorrectly required literal `6.0`. It stopped before that method's subsequent JSON invocation. The seven other real-file/CLI methods and all16 comparison API methods passed.

The corrected test explicitly asserts that the original producer's saved value is an integer equal to6 and requires `5.0 -> 6\n`, so a coerced float is not accidentally accepted by a prefix match. Neither producer nor consumer behavior changes.

## Ruff findings and scope

The run also reported five Ruff findings: two import-order findings, one explicitly parenthesized string-concatenation requirement, a redundant `float | int` test annotation and the equivalent `capture_output=True` subprocess style. The narrow successor addresses exactly those items and the oracle above.

The native [AST proof](style-and-oracle-proof.json) confirms the entire product non-import AST is identical and the import multiset is unchanged. The full16-method API test class AST is also identical. Product successor SHA256 is `2042f344a71cdbcebbe97ad7e31fdcdb359be3282a8e4427b728cc1afe6d76c0`; tests are `ca234b1f2c4045acefcec181afacbf143d4a95ea4081ff29bdfe0dc6da584468`. Guide and README bodies are unchanged.

[Decoded test log](test.log.txt), [decoded Ruff log](lint.log.txt) and [job metadata](jobs.json) preserve the actual native failure/output and source bindings. Logs are retained exactly as returned by the normal GitHub decoded-job-log connector; no archived ZIP-byte identity is asserted.

At this checkpoint corrected hosted gates, independent behavioral receiving and integration remain pending. Mac static review accepted the original product source; its successor addendum and root's independently frozen native producer oracles remain separate gates.

## GitHub creation throttle

The source branch was created normally before the draft-PR request. PR creation then returned secondary content403 at2026-10-08T16:59:30Z, with no Retry-After or reset value exposed by the connector. The request and response are retained. There was no PR, alternate account/route or immediate creation retry. A conservative cooldown to17:29Z was reserved while source review and read-only native execution continued.
