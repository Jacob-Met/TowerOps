# Independent static review: saved TowerOps policy comparison

Reviewer: ultra-1b3276062063-mac
Disposition: ACCEPT for the product source and exact formatting successor described below. No blocking source findings. Behavioral and CLI receiving remain independent gates owned by root.

## Reviewed source

| Input | Exact pin |
| --- | --- |
| Candidate commit | 1a71f19dfbc1eb89c05baecd2e2f49bc6e6e0613 |
| compare_plans.py Git blob | 5a078563e5fe0c588f63aafb5a8cfd709ab341fd |
| Original module SHA256 | 6130e332cea63f42e34aaf86fe50c72ac6c6212372368409914ba3e6c554ba75 |
| COMPARE_PLANS.md Git blob | 9132bf573f9829faae00b8cad20f98d21b047b5e |
| Guide SHA256 | 0e68968187947e2dbbd7878f294e0c08365d182f08c45ef53736fbbaaa5cebcc |
| Producer dependency parent | c9547893ee4a9f4cdfc64dfe555f8f313ba8237a |
| towerops.py Git blob | 3f541e5f0f3a05dac9d12c96e75d3d69ef3377d1 |
| advisory_options.py Git blob | 2cb3bb564559fb2fa2b20d9a215b4cb99badecbd |
| plan_world.py Git blob | 8e826a10cc2f9425de26727dce07851497174bba |

I read the exact published module, guide, and all three native producer dependencies. I did not read the authored comparison tests as an oracle or execute the candidate. Root separately froze producer-grounded behavioral controls before candidate exposure.

## Findings

The consumer admits both complete reports before constructing comparison output. Exact top-level, policy, world and advisory shapes are checked; duplicate JSON fields and non-finite or coerced numbers are refused. Native world parsing supplies the existing domain, identity, aircraft-count and numeric limits. The consumer does not silently accept omitted fields or normalize values through float conversion.

World identity is recomputed through the unchanged WorldState serialization and hash. This canonicalizes aircraft ordering by exact ID while preserving every field, numeric type and signed zero. Canonical world bytes are also compared across the two inputs, so equality does not rely solely on a claimed hash. Review clocks are compared as canonical native JSON bytes; integer and floating representations and signed zero retain their documented distinctions.

Every advisory hash is recomputed from the complete native Advisory body, including world, aircraft, setpoints, issued/expiry times and rationale. The expiry bound includes the producer's reviewed_at + 8.0 result at its maximum admitted clock. Duplicate advisory identities are refused, avoiding ambiguous menu ranks. Matching hashes across reports also require complete canonical body equality. Set membership therefore preserves full native identity rather than matching an aircraft or a rounded maneuver.

Output order follows the saved menus: all left records remain in left order with their optional original right rank, followed by right-only records in right order. Ranks are 1-based original positions. The changed-rank count is an absolute-position comparison, consistent with the guide; it does not imply a re-ranking or policy preference. Policy representation differences remain visible even when the advisory sets are equal.

Reported conflict membership, statuses and candidate counts receive structural checks without replaying planning or safety decisions. The module calls the native world parser and hash implementation, but does not invoke the planner, gate, control room, approval, actuation or CSV/UI machinery. The guide accurately distinguishes internal consistency from authentication, menu completeness and causal claims about a changed policy.

The file reader performs bounded reads of opened regular files, rejects direct symlinks/special files, and preserves input bytes. Its two reads are not an atomic filesystem snapshot; that limitation is explicit. Report SHA256 values bind the bytes actually read, separately from the producer-reported original-input hash. All output is constructed before the first stdout write. Text rendering uses JSON-style escaping, preserving literal metadata without interpreting terminal controls. Output failures can follow a partial write and return failure rather than claiming transactional output; the guide states this.

## Exact formatting successor

The source owner supplied a successor whose only product edits are moving the pathlib import into the sorted import block and parenthesizing two already-adjacent f-strings for the Saved alternatives text. I independently reconstructed exactly those two edits from the accepted 17,358-byte module. Built-in SHA256 over that reconstruction matches the supplied 17,386-byte successor:

- SHA256: 2042f344a71cdbcebbe97ad7e31fdcdb359be3282a8e4427b728cc1afe6d76c0
- Expected Git blob: 536b29c8a322b77aecf8a9551977ca9c092b02f4

All other product bytes remain unchanged. The import move and parentheses do not change the reviewed comparison behavior. This narrow successor is accepted without expanding the review into a new implementation. The guide remains byte-identical.

The source owner's separate test-oracle and lint edits are not represented here as newly executed tests. Root's independent API/CLI results and the ordinary hosted test suite must be recorded on the actual receiving commit. This note claims static source acceptance only.

## Execution and custody

This reviewer made no TowerOps source edits, ran no planner or comparison program, accessed no live aircraft or existing user report, and wrote nothing to the constrained Mac filesystem. Source hashing used built-in cryptographic functions on the already retrieved text in memory. No install, custom runner, service, new approval identity or native receiving pass is implied.
