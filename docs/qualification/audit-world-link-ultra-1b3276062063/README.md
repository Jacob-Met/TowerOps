# Saved-actuation world-link replay qualification

The product change is limited to requiring usable screened/before-world identities for a recorded actuation, followed by exact equality. It intentionally tightens completeness of acted histories. It preserves nonactuated histories and opaque nonblank labels; it makes no new hexadecimal grammar, after-world, motion, approval-authentication or actuation claim.

## Exact source

- Baseline: `3715876cb45d051a50873a0c93aa4067f494da6b`, tree `f26fede247b68504443bf69fc113f7db90515958`.
- Claim: TowerOps issue #87.
- Original witness packet: `8505472a30fdcd01188c1e617e139533edbf9f52`.
- Frozen candidate packet: `6c41b81734c9b40dd8590064dc507f45df19e848`.
- Additional author evidence: `158f02d022310d5c45fe99ebc4c8b5bd97a96dee`.
- Independent expectation freeze: `a50786a5146c8c2cf3059655df6256b5d9ab2acb`; it predates candidate exposure to the independent reviewer, not private candidate generation.

`source-scope-proof.json` contains the full two-hunk source diff. The producer, adapter, prior tests, CLI loading/error handling and report classes are unchanged.

## Actual author execution

Cloud CPython 3.12.14 executed exact source in memory. All ten new unittest methods pass, including their subcases, alongside thirteen original parameterless test functions. The same new suite against the unchanged baseline produces 25 failed subchecks and no errors; its original tests still pass. The original ten-case witness separately preserves the four missing/null identities falsely reported clean by the baseline.

The checks include the unchanged decision-trace adapter and actual `main(argv)` with captured stdin/stdout/stderr. The harness's effect guard recorded no filesystem, process or network attempts during receiving. These are in-process API and CLI-entry checks, not an OS-child CLI, filesystem, browser or installed-estate run.

Three inherited filesystem/subprocess CLI tests were not executed. Ruff and pytest are absent from this environment; neither was installed, and no full-repository/lint pass is asserted. No GitHub Actions were used.

## Evidence custody

Original evidence bytes are retained. Historical harness templates contain injected-source placeholders and compact instrumentation; they are stored as `.py.txt` with an explicit original-path mapping in `EVIDENCE_PATHS.json`. The maintained product tests remain ordinary discoverable Python in `tests/test_audit_world_linkage.py`.

## Independent receiving and scope review

The unchanged independently frozen 22-group receiver was applied to both versions. The baseline matched 8 of the 22 expectations; fourteen incomplete histories were falsely clean. The candidate matches all 22 expectations through direct replay, the unchanged adapter, and captured-stdin main: 22 calls per surface per version. Candidate CLI entry returns 0 for five groups and 1 for seventeen, with empty stderr. Complete outputs, counters, input immutability, advisory isolation and the existing mismatch diagnostic are retained in the independent packets. This is in-process execution, not an OS-child or browser claim.

The separate static reviewer confirmed exact forward/reverse reconstruction of the two-hunk change, ordinary generic logic without frozen-fixture coupling, and preservation of all source outside that boundary. Its two exact leaves are under `independent-static/`.

The final source composition and ordinary no-Actions integration are separate from these executed checks. Existing consumer deployment must not be inferred from an unrun browser or installed-source gate.

Independent acceptance packet: `f86481b9dee7fd973300befa1aa760b311202e55`. Static review packet: `32ee57317f164063ee7c06b82cd4b8f1f9faff4a`. Both are archived without changing their contents.
