# Claims map — every capability claim → file / test

Base: commit `da998e4` (`togishi/synthetic-explorer`). "Test" = covered by an automated check in this repo; "code only" = present in the source but no test in this repo exercises it, so the pack says it only as "the code does X". `check_claims.py` verifies that every file and symbol named here exists.

| # | Claim used in the pack | Where it is implemented | Checked by |
|---|---|---|---|
| 1 | Two fictional aircraft (`FIXTURE-A`, `FIXTURE-B`, 10,000 ft) on converging constant-velocity paths | `scenarios.py` `run_scenario`; `towerops.py` `Aircraft.projected` | `test_explorer.py` `test_all_cases_and_fixture_switches` asserts `before_conflict` is true in every case |
| 2 | Conflict prediction: closed-form unsafe-interval check, 5 nm / 1000 ft / 5 min horizon | `towerops.py` `SafetyPolicy._horizontal_unsafe_interval`, `_linear_abs_unsafe_interval`, `_pair_conflict`, `state_has_conflict` | Indirectly: before/after conflict values asserted in `test_all_cases_and_fixture_switches`. No geometry unit tests in this repo (README: no exhaustive numeric coverage claim) |
| 3 | Advisory proposed by a deterministic planner (FIXTURE-B, vy 2.0 nm/min, 8 s validity) | `towerops.py` `AdvisoryPlanner.plan` | Output read from `python explorer.py run approved` (`advisory.set_vy_nm_min = 2.0`, `aircraft_id = FIXTURE-B`) |
| 4 | Advisory bound to exact world hash; changed world → `world_hash_mismatch` | `towerops.py` `WorldState.world_hash`, `ControlRoom.screen_batch` | `test_all_cases_and_fixture_switches` (case `stale_binding` → `world_hash_mismatch`) |
| 5 | Stale observation rejected (limit 10 s) → `stale_state` | `towerops.py` `ControlRoom._fresh` | same test (case `stale_state`) |
| 6 | Expired proposal rejected (8 s window) → `expired_advisory` | `towerops.py` `screen_batch` | same test (case `expired`) |
| 7 | Explicit approval required → `human_approval_required` (fixture identity `FIXTURE-CONTROLLER-NOT-AUTHORITY`) | `towerops.py` `ControlRoom.apply`; `scenarios.py` | same test (case `missing_approval`) |
| 8 | Acknowledgement required, exact advisory hash: `ack_missing`, `ack_invalid`, `ack_late` | `towerops.py` `ControlRoom.apply` | same test (cases `missing_ack`, `wrong_ack`, `late_ack`); Chromium acceptance asserts success → missing-ack with no reload |
| 9 | Simulated state transition only after every gate passes; any refusal leaves the world unchanged with no `simulated_actuation` event | `towerops.py` `ControlRoom.apply`, `WorldState.replace_aircraft` | `test_all_cases_and_fixture_switches` (`before == after`, zero actuation events on every rejection; version + 1 and `after_conflict` false on success) |
| 10 | Hash-chained audit log (each event hashes the previous); edits detectable against the head | `towerops.py` `AuditLog.append`, `AuditLog.verify` | `test_all_cases_and_fixture_switches` (`AuditLog.verify` true); `test_replay_checks_whole_export` (edited `audit_events` → mismatch) |
| 11 | Export + replay: backend re-executes fixed inputs and compares the whole export; one changed field → MISMATCH; 1001 vs 1001.0 accepted | `scenarios.py` `replay_result`, `json_equivalent`; `explorer.py` `/api/replay` | `test_replay_checks_whole_export`, `test_javascript_numeric_roundtrip`, `test_real_run_export_replay`; Chromium acceptance (original MATCH, tampered MISMATCH, all cases, both viewports) |
| 12 | Strands layer is proposal-only (`effect: proposal_only`); cannot apply or authorize | `strands_adapter.py` `submit_synthetic_advisory`, `build_agent` | **Code only.** Requires the `strands` SDK; not imported by `explorer.py` or any test. The demo does not run it |
| 13 | The explorer makes no model/SDK calls and needs no pip install | `explorer.py` imports only stdlib + `scenarios`, `towerops`; `EXPLORER.md` | `explorer.py` imports (checked by `check_claims.py`); `test_explorer.py` runs stdlib-only |
| 14 | Loopback-only (127.0.0.1), same-origin Host/Origin check, 256 KiB body cap, CSP | `explorer.py` `Handler.local_request`, `MAX_BODY`, `respond` | `test_explorer.py` `test_invalid_requests_fail`, `test_static_assets_and_unknown_routes` |
| 15 | Eight fixed cases (approved + 7 refusals) | `scenarios.py` `SCENARIOS` | `test_all_cases_and_fixture_switches` (8 cases × 4 switch combinations) |
| 16 | UI: projected-time slider (0–5 min), before/after SVG plots, audit timeline, export/replay controls, no horizontal overflow at 390 px | `web/index.html`, `web/app.js`, `web/style.css` | `browser_acceptance.py` (Chromium 1280×900 and 390×844; page errors none) |
| 17 | `towerops.py` unchanged by the explorer commit | commit `da998e4` message; `git diff e8fa18e da998e4 -- towerops.py` is empty | `check_claims.py` |
| 18 | Replay/chain is reproducibility, not authenticity or a signature | `EXPLORER.md` "Export and replay"; `scenarios.py` `replay_result` docstring and `note` | — (stated limitation) |

## Explicitly not claimed
Operational ATC use, aviation certification or safety assurance, live surveillance data, real clearances, exhaustive numeric/geometry coverage (README "Known limits"), signed or externally anchored audit, a model/Strands agent running in the demo, production deployment, or any benchmark/performance number.

## Code-only gate branches (present, not tested here)
`towerops.py` also rejects `invalid_state_time`, `future_state`, `conflicting_recommendations`, `invalid_advisory_time`, `unsafe_advisory`, `invalid_approval_time`, `invalid_ack_time`. No test in this repo triggers them individually; the pack mentions none of them by name except in this table.
