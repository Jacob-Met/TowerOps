# Native custom-world CLI receiving — e82707f2bc62

This contribution exposes the existing native planner to a saved raw WorldState through `plan_world.py`. The product contract and runnable examples are in [PLAN_WORLD.md](../../../PLAN_WORLD.md). Ownership is recorded in [issue #49](https://github.com/Jacob-Met/TowerOps/issues/49).

## Original opportunity and completed author receiving

Current source was pinned to `093f88b29d6e1ede778f967528c7e010b7689ab1`, tree `4a87643d57cabf81e570b21c119f00b43f79448e`. The existing `explorer.py run` command rejects a custom JSON file as a scenario name (exit 2). On the exact same three-flight world, the real native helper evaluates 74 candidates and admits 66 individually screened alternatives. The new CLI returns all 66 bodies and hashes in the same order, including the same original first proposal.

The final focused author suite passes **22/22 methods with zero errors or skips** on Python 3.12.14. It invokes actual native modules and actual processes for files and stdin, changed policy and clock, conflict-free and no-admitted-option outcomes, refusal exits, resource/type/schema handling, unchanged read-only input, and a real `/dev/full` output failure. This is a completed review path; no simulated actuation is performed.

The first suite run passed 21 methods and failed one expectation: it treated explicit API `now=None` as invalid even though `None` is the documented default-clock sentinel. The corrected receiving source exempts only that sentinel and adds a command-line `--now null` refusal control. All original invalid world-field controls remain. **Production code did not change.** The original failed test, log and source freeze remain in the archive.

## Source and evidence custody

[source-receipt.json](source-receipt.json) lists every owned file, all four unchanged hydrated native modules, the input and native results, and exact source/test hashes. [author-evidence.zip](author-evidence.zip) preserves the original custom world, native opportunity, complete first CLI output, both complete test logs and receipts, both source freezes, and the original failed test source. Each archive member was compared with its source bytes after creation.

Local source files were unchanged through each run. Whole-repository/current-parent preservation is an integration requirement; the local focused receipt does not claim to inspect unhydrated source files.

## Exact lint successor and remaining hosted boundary

The retained exact Ruff 0.16.10 initially found two redundant numeric parameter annotations in the author source/test and three style findings in the independent test. The author successor changes only those two future annotations; all nonannotation AST nodes, runtime numeric handling, fixtures and assertions remain identical. The accepted 22-case execution stays bound to original production `3efe3d7e` and author test `65255ee4`. The published production successor is `8e826a10`; no additional local behavioral execution is claimed for it. Original source/test bytes, failed lint output and the equivalence proof are included in the archive.

The independent packet preserves its original four-case blind execution and its separate lint successor. Exact Ruff now passes on all three final Python files with their source bytes unchanged. Two additional bounded argument controls on the original source both refuse a 4,001-character nested nonnumeric `--now` argument with exit 2 and no traceback, including one native `-S` execution; these controls prompted no production change.

An ordinary isolated dependency installation for pytest 8.3.5 and Ruff 0.16.10 had reached the wheel download but failed with ENOSPC. The later lint run used the already installed exact retained Ruff, not a substitute. Existing hosted Python, adapter and Airspace Lab gates still qualify the final source/current-parent composition; no workflow was changed. Final hosted results belong in the PR's source-bound receipt.

This command consumes raw world JSON with its explicitly documented numerical envelope. It does not alter the native model, browser formats, Worker, policy implementation, planner menu, approval/readback gate or live audit. Browser scenario-file, playback/Reset and safe-version ownership remains separate. Evidence covers synthetic native behavior only, with no live service, operational aviation assurance or deployment claim.
