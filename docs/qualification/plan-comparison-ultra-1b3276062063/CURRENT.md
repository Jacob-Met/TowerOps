# Saved-plan comparison qualification — current checkpoint

The product contribution is the native terminal/API consumer described in
[COMPARE_PLANS.md](../../../COMPARE_PLANS.md), owned under
[TowerOps #56](https://github.com/Jacob-Met/TowerOps/issues/56).
The original [README](README.md), source pins, baseline receipts and failed-run
records are historical checkpoints and remain unchanged.

## Source and independent review

The original published source is commit
`1a71f19dfbc1eb89c05baecd2e2f49bc6e6e0613`.
The corrected comparison module is SHA256
`2042f344a71cdbcebbe97ad7e31fdcdb359be3282a8e4427b728cc1afe6d76c0`
(Git blob `536b29c8a322b77aecf8a9551977ca9c092b02f4`).
Only an import move and parentheses around previously adjacent f-strings
changed in the product. Native AST comparison proves identical non-import
product logic and an identical import multiset. All 16 original API test
methods are also AST-identical.

The [independent static review](independent-static/REVIEW.md) accepts both the
original product and that exact formatting successor. Its author independently
reconstructed the successor from the original and verified its byte hashes;
the guide remains unchanged. This is source acceptance, not execution evidence.

The composition records in [successor-source.json](successor-source.json)
bind the current published main and unchanged native producer dependencies.
Incoming scenario-owner web source and evidence are preserved. There are no
planner, safety, audit, TypeScript, CSV, Undo, dependency or workflow edits.

## Preserved first hosted run and correction

[Run 37812639867](https://github.com/Jacob-Met/TowerOps/actions/runs/37812639867)
executed the actual Python 3.12.15 command/file tests on Ubuntu:
169 passed and one test failed. The actual native producer preserves the
command-line policy value `6` as an integer. The consumer correctly printed
`5.0 -> 6`; the receiving test wrongly expected `5.0 -> 6.0`.
The correction checks the producer's exact integer type/value and the full
output line, including its newline. It does not coerce product numbers.

Seven other actual CLI tests and all 16 API methods passed in that run.
The failed method had not yet reached its JSON assertion, so its complete
success is not claimed. Five reported Ruff style findings are corrected.
The full connector-decoded logs, job metadata, original PR-creation refusal,
and exact native source/test diff and AST proof remain together under
[first-hosted-run](first-hosted-run/README.md).

## Independent behavioral and CLI gates

Root froze comparison oracles from the exact original native producer before
candidate exposure. Its 27 API cases passed against the original published
module with unchanged fixtures and no filesystem, process, network, planning,
screening or actuation effects. That execution used cloud Python 3.12.14.
The unsuccessful Mac API request and the first metadata-probe refusal are
separate execution history; neither is reported as a Mac receiving pass.

The [immutable independent packet](../plan-compare-ultra-1b3276062063/independent/REVIEW.md)
and [ordinary pytest integration](../plan-compare-ultra-1b3276062063/independent/INTEGRATION.md)
retain all 27 API vectors and 22 actual CLI processes. The complete receipt and
a compressed archive of exact raw stdout/stderr are exposed in the normal job log. The corrected source still requires the normal hosted
test and Ruff gates before source integration. No pending receiving check
is converted into a pass by this checkpoint.

## Capacity and receiving boundary

Both original Mac file-bootstrap attempts stopped before workspace creation:
one at shell ENOSPC and one at the unchanged 512 MiB reserve guard.
Subsequent Mac API requests may have a transport timeout without an observed
process result. No Mac file/CLI, installed runtime, browser, Windows hub
delivery, live aircraft or user report mutation is claimed.

The existing ordinary repository workflow is the receiving path for the
actual Linux command/file controls. No alternate filesystem, reserve reduction,
other-owner cleanup, new service, custom runner or workflow bypass is used.
