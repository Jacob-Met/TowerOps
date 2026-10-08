# Independent native WorldState planner receiving

This packet receives TowerOps #49 against original commit `093f88b29d6e1ede778f967528c7e010b7689ab1`. The reviewer first read only the immutable native model/options APIs and `PLAN_WORLD.md`, then froze four semantic cases, four exact input byte sequences and the full native oracles. Only after that freeze did the reviewer inspect `plan_world.py` to implement access to its report fields.

The identical four-method test fails on the baseline's missing command and passes on the frozen candidate, with no errors, skips or receiver corrections. Eleven actual CLI processes on the candidate complete as seven successful reviews, two native clock refusals and two input/output refusals. The source, input files and working-directory contents are checked before and after every child process.

## What the independent cases establish

A custom four-aircraft world contains two unrelated encounters and case-distinct `A`/`a` and `B`/`b` identifiers. With an explicit clock and policy it produces 148 native candidates and 136 individually admitted alternatives. The complete ordered proposal bodies and hashes match the original native helper, and the first choice matches `AdvisoryPlanner`. The first proposal leaves the unrelated pair in conflict and still cannot pass native application without approval. No approval/readback fixture or actuation is created by the command.

The same input through a literal `./-` file and stdin produces identical output bytes. Reformatting only JSON changes the input byte SHA while preserving the native world and all alternatives. Canonical comparisons preserve integer/float representation and signed zero. A shorter requested horizon correctly returns `no_conflict`; an empty world still undergoes future/stale clock checks. A coincident pair returns `no_admitted_option` with 62 examined candidates and no invented maneuver.

A generated planning report cannot be consumed as raw world input. An actual pipe with its read end closed triggers clean output failure. These are real subprocess and operating-system interactions, without a substitute planner, gate or stream mock.

## Source and evidence

- Candidate `plan_world.py`: SHA256 `6c001f4b39658a3a89fba3f458bcae46fe9577425274f16d17082cd83a40265e`.
- Receiver: SHA256 `1afa3ef344900661cb17b0912e17578675af078e762005d5f1b6917f23171fc5`; Git blob `9247c0bea10a72ab00e7c828874919dc12876300`.
- Blind protocol: SHA256 `ca943b55637ca02405f4f7376b0825b3f05cbe28b55380469d2da9f4231be533`.

The JSON receipt binds source, protocol, test, logs and output counts. `raw-evidence.zip` retains the original baseline failure, both source receipts, all input fixtures, full 136-option native oracle, actual CLI stdout documents, and command logs. Every archived file was read back and verified against its SHA256.

This is stdlib/Python 3.12 acceptance of a synthetic research simulator. Final current-parent composition and the existing repository lint/hosted gates remain with the author and receiving parent. No browser, provider, deployment or operational aviation result is claimed.

The portable test uses the imported `towerops` module to locate the real source. Ordinary unittest discovery uses a disposable temporary directory; the optional `TOWEROPS_RECEIVING_OUTPUT` variable retains per-case evidence when deliberately set. It has no absolute-path default or separate fixture dependency.

## Required lint-only successor

The original executed test, logs, source references and complete raw evidence remain unchanged. Before publication, retained Ruff required import ordering, an ordered dictionary literal in the fixture helper and `capture_output=True` in the ordinary subprocess branch. These changes are recorded in a separate successor; all four test-method ASTs are unchanged, and narrow AST normalization proves the two helper transformations preserve their statements and assertions.

Published receiver: Git blob `2cab5b89008adf3ef0ba4200f2a073330d77fe1d`, SHA256 `9735fb2605e232cd079685aca0f016c6995f8cb4043a1b864ac63dd34bcad4ed`. The author also changed only a numeric parameter annotation in `plan_world.py`: current Git blob `8e826a10cc2f9425de26727dce07851497174bba`, SHA256 `62dc9be45f9973318846e8452826112e120b93b9f4507d9198a625ef0682c92e`. Integer values are still admitted and preserved at runtime.

No semantic matrix was rerun for these changes. The original 4/4 receiving remains bound to its original two hashes; the existing full hosted gate must qualify the final source/test composition. The successor ZIP preserves every original member byte-for-byte and adds the exact lint successor, patch and proof.
