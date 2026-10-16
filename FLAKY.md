# FLAKY.md — Flaky-test detection & quarantine ledger (TowerOps pilot, T165)

Flaky tests train everyone to ignore red CI — and ignored red CI is how real
regressions slip through. This file is the repo's single source of truth for
flake detection, quarantine, and clean-bill status.

## How detection works

CI runs `ci/retry_once.py` (workflow `.github/workflows/flaky-guard.yml`):

1. Full suite runs once.
2. Every test that **fails** is re-run **exactly once, in isolation**.
3. A test that passes on retry is recorded as **FLAKY** — it is *not* trusted.
   The wrapper exits `2`, the workflow goes **red**, and a JSON report is
   uploaded as the `flaky-report` artifact (`ci/flaky-report.json`).

Exit codes: `0` = clean · `1` = consistent failure (real bug) ·
`2` = flaky detected (recorded, needs triage).

A flaky detection is never silently greened. Red stays meaningful.

## Quarantine protocol

A test may be quarantined (marked `skip`/`xfail`) **only** when all of these hold:

1. **Evidence.** A retry-once report (or ≥2 independent CI observations)
   naming the exact test node ID.
2. **Tracking issue.** An issue is opened on this repo describing the flake,
   with the evidence linked. The issue number is the quarantine's identity.
3. **Marker in code.** The test gets
   `@pytest.mark.skip(reason="FLAKY quarantined, see #<issue>")`
   (or `xfail(strict=False)` if partial signal is still wanted) —
   never a silent deletion.
4. **Ledger entry** below, filled in completely.

**Lifting a quarantine requires owner/lane sign-off:** the repo owner (or the
lane lead currently responsible for this repo) posts sign-off on the tracking
issue, a PR removes the marker, and the sign-off (who + when) is recorded in
the ledger. No sign-off, no lift — a passing streak alone does not lift it.

**Review cadence:** every quarantined test is re-evaluated at least every
30 days. A quarantine older than 90 days without re-verification must be
re-justified with fresh evidence, or the test is fixed or deleted.

## Clean-bill rule

**20 consecutive full-suite runs with zero failures and zero flakes = clean
bill.** Any failure or flake resets the counter to zero. A clean bill is
recorded here with the run evidence; it does not need an issue.

## Ledger

### Quarantined tests

| Test | First seen | Evidence | Tracking issue | Quarantined | Lift sign-off |
|------|-----------|----------|----------------|-------------|---------------|
| *(none)* | — | — | — | — | — |

### Clean bills

- **2026-10-06/07 — CLEAN BILL (20 consecutive runs).** TowerOps main
  `@ e16867b`. 20 full-suite runs, each `61 passed, 84 subtests passed`,
  zero failures, zero flakes. Runs 1–10: `pytest -q`; run 11:
  `ci/retry_once.py` (exit 0, "all tests passed on first run"); runs 12–20:
  `pytest -q`. Full log: T165 mission receipt
  (`~/workspace/estate/receipts/T165-owner-2026-10-06.md`). Counter resets on
  the next failure or flake.

### Historical observations (not quarantined — insufficient evidence to name a test)

- **2026-10-05 — TowerOps PR #3 CI incident** (branch
  `delivery/audit-replay-verification`, since merged). CI test job:
  fail 17:05 UTC → success 17:07 UTC → fail 17:12 UTC across three rewritten
  pushes (heads `12b6ec9e` / `df5c39e5` / `674958c0`), lint green throughout.
  Flagged as suspected flaky by estate CI watch (run `37346677341`); the
  failing *test name* was not recoverable from available evidence, so no test
  is quarantined on this basis. The retry-once wrapper landed by this pilot
  will identify the test automatically if it recurs.
