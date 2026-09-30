# TowerOps — Devpost-style description (draft, not submitted)

> Research simulation only. TowerOps is not operational ATC software, is not aviation-certified, issues no real clearances, and is not connected to live aircraft or surveillance data. All identities and approvals are fixtures. Nothing here has been posted or submitted to any competition.

## Tagline
The model proposes. Deterministic code decides.

## Inspiration
A social-media clip about two aircraft using the same callsign. It raised a broader question: could an agent surface ambiguity, projected conflicts, stale state or a bad readback **without becoming the safety authority itself**? (README "Inspiration")

## What it does
TowerOps is a synthetic decision-support research demo. Two fictional aircraft fly constant-velocity paths that converge. The engine predicts the conflict, produces a bounded advisory, and then makes that advisory earn its way through a chain of deterministic gates before the simulated world is allowed to change:

1. **Freshness and binding:** the advisory is bound to the exact hash of the world it was computed from. A changed world, an observation older than 10 s, or an advisory past its 8 s window is refused (`world_hash_mismatch`, `stale_state`, `expired_advisory`).
2. **Explicit approval:** no approval fixture, or one for a different advisory, is refused (`human_approval_required`).
3. **Acknowledgement/readback:** missing, mismatched or late acknowledgements are refused (`ack_missing`, `ack_invalid`, `ack_late`).
4. **Simulated transition:** only after every gate passes. On success the projected conflict goes from true to false. On any refusal the world is unchanged and no actuation event exists.
5. **Hash-chained audit log:** every step, including refusals, is recorded; each event hashes the one before it.

A local **scenario explorer** lets you run the approved case and seven refusal cases, scrub the projected-time slider to compare the before and after paths, export a result as JSON, and replay it: the backend re-runs the fixed inputs and compares the entire export, so a single edited field reports a mismatch.

## How we built it
- `towerops.py`: the deterministic core (world state, closed-form conflict prediction, `AdvisoryPlanner`, `ControlRoom` gates, `AuditLog`). Unchanged by the explorer commit.
- `strands_adapter.py`: a Strands tool boundary that can only return a structured, `proposal_only` advisory. It cannot apply or authorize anything. (The explorer and its tests do not run it.)
- `scenarios.py`, `explorer.py`, `web/`: fixed scenarios, a loopback-only standard-library HTTP server (same-origin checks, 256 KiB cap, CSP) and a no-dependency browser UI with SVG plots.
- Python 3.12+, standard library only for the app; Playwright/Chromium only for the optional browser acceptance run.

## Challenges
- Making "the model cannot bypass the gate" structural rather than a promise: the gate only sees a typed advisory, an approval and an acknowledgement, each bound by hash.
- Keeping replay honest. A self-consistent hash chain is not a signature, so the replay re-executes fixed inputs and says plainly that it proves reproducibility, not authenticity.
- Number handling across Python and JavaScript (1001 vs 1001.0) without letting booleans or strings slip through as numbers.

## Accomplishments
- 8 automated tests pass (8 cases × 4 fixture-switch combinations, whole-export tamper checks, JS numeric round-trip, real HTTP requests, invalid-request handling).
- A Chromium acceptance run exercises all eight cases at 1280×900 and 390×844, including export, original replay, tampered replay and a success-to-missing-ack sequence without reload, with no page errors and no horizontal overflow.

## What we learned
Separating *proposal* from *admissibility* makes the failure modes inspectable: each refusal has a named reason, a preserved pre-gate world and an audit trail.

## What's next
Unit tests for the geometry edge cases and the currently untested gate branches (`future_state`, `conflicting_recommendations`, `unsafe_advisory`, time-ordering checks); a signed or externally anchored audit head; more than two aircraft; a run of the Strands path with a real model behind the same gate.

## Built with
Python · Strands Agents SDK (adapter) · SHA-256 hash chaining · HTML/SVG/JavaScript · Playwright (tests)

## Limits (please read)
Finite synthetic cases only. No claim of operational aviation safety, exhaustive numeric coverage, live ATC integration or production deployment. Approval and readback identities are fixtures with no real-world authority. Replay demonstrates reproducibility under this engine, not authenticity.

## Try it
```sh
git clone https://github.com/Jacob-Met/TowerOps && cd TowerOps
git checkout togishi/synthetic-explorer
python explorer.py serve --port 8765      # open http://127.0.0.1:8765
python -m unittest -q test_explorer       # 8 tests
```
Every capability above is mapped to a file and test in [claims-map.md](claims-map.md).
