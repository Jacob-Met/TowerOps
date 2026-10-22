# Agent Operations Handbook — TowerOps

Short, repo-specific operating notes for agents working on `Jacob-Met/TowerOps`.
Docs-only; no behavior change. Lessons are dated snapshots — verify against live
repo state before acting on a stale one.

## Canonical operating rules

The estate's canonical agent-operating rules live in the `github_landing` skill
(`~/workspace/skills/github-landing/SKILL.md` in the agent workspace). Summary:

- Verify the exact branch tip SHA immediately before each shared mutation;
  re-check in the push turn itself (collision checks go stale in minutes).
- Read back after every push/merge/comment; back off once on 429/403.
- Merges only for independently reviewed, CI-green PRs: pin the head with the
  `sha` body param on PUT /merge, and run the rebase-freshness gate.
- Never force-push, rewrite history, or delete branches.
- Holds: never write Mission Control's `queue/`; never touch
  `HELDOUT_SEALED.md`; respect active lane/queue owners' branches and surfaces.

## Dated repo-specific lessons (newest first)

- **2026-10-05 — gh-push-branch is a REBASE tool.** It is never a
  fast-forward push: it silently rebased the PR #3 (towerops-next) branch and
  resolved `towerops.py` / `README.md` / `.gitignore` to stale pre-#13/#16/#17
  versions, reverting later safety-policy and CI-badge work. After ANY
  gh-push-branch push, diff the pushed tree against the intended local
  pre-push tree before treating the push as clean; fix-forward via the git
  database API (no force-push).
- **2026-10-05 — Pin survey parser bug.** The "0 of 151 pinned" survey figure
  was a parser bug (it dropped every `uses:` line with a trailing comment);
  the corrected figure is 22% pinned outside hamon, and TowerOps is fully
  pinned. Open at handbook time: PR #9 (CI: pin pytest in the composite
  workflow install step) — Jacob's disposition.
- **2026-10-05 — CLI output parsing.** `gh-pat-repos` output lines carry BOTH
  a `- ` bullet prefix and a ` [private]`/`[public]` bracket suffix — strip
  both before building API paths. `gh-pat-api` returns rc=0 with EMPTY stdout
  on malformed paths: empty body + rc=0 means malformed request, not an API
  outage.
- **2026-10-04 — Comment-review form.** Submit reviews with the inline form
  `{"event":"COMMENT","body":"..."}` — submitting with a heredoc body
  silently produces a PENDING empty review (TowerOps PR #15, review id
  5405156371), and submitting the pending review with bare
  `{"event":"COMMENT"}` returns HTTP 422. Inline body returns HTTP 200
  COMMENTED.
- **2026-10-03 — PAT identity.** The PAT authenticates as Jacob-Met himself: a
  formal GitHub PR APPROVE on a PR he authored returns HTTP 422 ("Can not
  approve your own pull request") — independent-review verdicts must be
  posted as comment reviews, not formal approvals.
