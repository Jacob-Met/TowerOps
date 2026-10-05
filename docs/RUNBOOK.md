# TowerOps operator runbook

> **Scope:** research simulation only. TowerOps is a synthetic air-traffic-control
> decision-support research demo, not operational ATC software, not aviation
> certification, and not connected to live aircraft or surveillance data.

## What TowerOps does

TowerOps simulates a control loop where an agent **proposes** maneuvers and
deterministic code **decides** whether they are admissible:

```text
synthetic world state → conflict prediction → agent proposal boundary
→ deterministic safety + freshness gate → human approval → acknowledgement
→ simulated state transition → hash-chained audit
```

The components live in `towerops.py`:

| Component | Role |
|---|---|
| `Aircraft` / `WorldState` | Immutable synthetic state. `world_hash` binds advisories to the exact state they were planned against. Duplicate `aircraft_id`s are rejected at construction. |
| `SafetyPolicy` | Separation thresholds and advisory bounds; projects constant-velocity pairs over a horizon and reports conflicts. Non-finite (NaN/inf) fields fail closed: the pair counts as conflicting. |
| `AdvisoryPlanner` | Deterministic synthetic planner that emits at most one advisory for the lexicographically-last aircraft in a conflicted state. Tries lateral-only, climb, speed, then combined maneuvers; every candidate must pass `advisory_safe`. |
| `ControlRoom` | The gate. `screen_batch` validates freshness/timing/world-hash/safety; `apply` additionally requires a matching `"approve"` approval and an `"accepted"` ack inside their timing windows, then performs the simulated transition and audits it. |
| `AuditLog` | Append-only hash chain (`prev_hash` linkage). `AuditLog.verify(events)` replays the chain and returns `True` only if sequence numbers, links, and hashes all check out. |
| `strands_adapter.py` | Proposal-only Strands tool boundary. It cannot apply, authorize, or bypass anything in `towerops.py`. |

The model proposes; deterministic code decides.

## Run it locally

Requires **Python 3.12+**.

```bash
git clone https://github.com/Jacob-Met/TowerOps.git
cd TowerOps
```

### Deterministic demo (no extra dependencies)

```bash
python demo.py
```

The demo builds two synthetic aircraft on a converging path (`TWR218` and
`TWR419`), plans one bounded advisory, applies fixture approval and
acknowledgement, performs the simulated transition, and prints the full result
plus audit chain as JSON. It exits non-zero unless its own invariants hold:
conflict present before, conflict resolved after, audit chain verifies, and a
`simulated_actuation` event exists.

### Test suite

```bash
python -m pytest -q
```

Expected at main tip: **32 passed**. Suites cover the audit chain, determinism,
fail-closed behavior (including non-finite inputs), planner behavior, and state
validation.

### Strands agent path (optional)

The Strands proposal layer is only needed if you want to run the agent side:

```bash
pip install -r requirements.txt   # pins strands-agents==1.55.1
```

The demo and tests do not import Strands and run without it. `strands_adapter.py`
exposes a single tool, `submit_synthetic_advisory`, which returns a structured
proposal marked `proposal_only` — submitting through the agent never applies an
advisory. Anything that reaches the aircraft model still goes through
`ControlRoom` screening, approval, and acknowledgement.

## Configuration

All tuning lives in `SafetyPolicy` (defaults shown; pass your own to
`ControlRoom(policy=...)` or `AdvisoryPlanner(policy=...)`):

| Field | Default | Meaning |
|---|---|---|
| `min_horizontal_nm` | `5.0` | Minimum horizontal separation (nautical miles) |
| `min_vertical_ft` | `1000.0` | Minimum vertical separation (feet) |
| `horizon_min` | `5.0` | Look-ahead window for projected conflicts |
| `sample_step_min` | `0.5` | Sampling step (plumbing; interval math is analytic) |
| `max_state_age_sec` | `10.0` | State older than this vs. `now` is rejected as stale |
| `max_speed_nm_min` | `6.0` | Advisory ground-speed bound (hypot of vx/vy) |
| `max_climb_ft_min` | `3000.0` | Advisory climb-rate bound (absolute) |

Two deliberate fail-closed choices: duplicate `aircraft_id`s raise `ValueError`
at `WorldState` construction (they would silently break id-based operations and
could let a colliding advisory pass), and any non-finite state field makes the
pair count as conflicting rather than safe.

Time semantics: `observed_at`, `issued_at`, `expires_at`, `approved_at`,
`acknowledged_at`, and `now` share one synthetic clock (seconds in the demo).
The planner fixes `expires_at = issued_at + 8.0`; the demo's fixture approval
and ack land within that window.

## Common operations

### Screen a batch of advisories (no actuation)

```python
from towerops import ControlRoom, SafetyPolicy
room = ControlRoom(SafetyPolicy())
hashes = room.screen_batch(state, advisories, now)
```

Returns the admitted advisory hashes and appends a `screen_pass` audit event.
Raises `GateRejected` (a `RuntimeError` with a `.reason` string) on the first
failed check — see the failure table below. Also rejects multiple *distinct*
advisory hashes for the same aircraft (`conflicting_recommendations`).

### Apply an advisory end-to-end

```python
from towerops import Ack, Approval
approval = Approval(advisory.advisory_hash, "approve", approved_at, "controller-id")
ack = Ack(advisory.advisory_hash, "accepted", acknowledged_at)
new_state = room.apply(state, advisory, approval, ack, now)
```

Order of gates inside `apply`: screen → approval present, bound to the same
advisory hash, decision `"approve"`, timing within `[issued_at, expires_at]` and
`<= now` → ack present, bound to the same hash, status `"accepted"`, timing
`>= approved_at`/`issued_at` and `<= expires_at`/`now` → simulated transition.
Each accepted step is audited (`screen_pass`, `approval`, `ack`,
`simulated_actuation`).

### Plan from a conflicted state

```python
from towerops import AdvisoryPlanner
planner = AdvisoryPlanner(policy)
advisories = planner.plan(state, now)   # [] if no conflict, else [one advisory]
```

Returns `[]` when the state is already conflict-free or when no bounded
candidate passes the gate — an empty plan is a legitimate outcome, not an error.

### Replay an audit chain

```python
from towerops import AuditLog
assert AuditLog.verify(room.audit.events)
```

Genesis link is `"0" * 64` (`ZERO_HASH`). Event hashing is
`sha256(prev_hash_ascii + "\n" + canonical_json(event))`; canonical JSON is
sorted keys, compact separators, UTF-8. Any reordering, edit, or deletion
fails verification.

### Unsafe comparison baseline

`baseline_apply_unchecked(state, advisory, now)` exists as the no-gate baseline
for tests/demos of what the gate prevents. Never use it as an operator path.

## Failure modes and recovery

`ControlRoom` raises `GateRejected`; inspect `.reason`:

| Reason | Cause | Recovery |
|---|---|---|
| `invalid_state_time` | `observed_at` or `now` not finite | Fix the clock plumbing |
| `future_state` | `observed_at > now` | Wait for / supply a state at or before now |
| `stale_state` | `now - observed_at > max_state_age_sec` (10 s default) | Refresh the world state and re-plan |
| `conflicting_recommendations` | >1 distinct advisory hash for one aircraft in a batch | Dedupe to a single proposal per aircraft |
| `invalid_advisory_time` | Issued/expired timestamps not finite, or `issued_at` outside `[observed_at, now]`, or `expires_at < issued_at` | Re-issue with a sane window |
| `world_hash_mismatch` | Advisory bound to a different state | Re-plan against the current `world_hash` |
| `expired_advisory` | `now > expires_at` | Request a fresh advisory (planner window is 8 time units) |
| `unsafe_advisory` | Fails projected-separation check, or exceeds `max_speed_nm_min` / `max_climb_ft_min` | Propose within bounds; check the conflict geometry |
| `human_approval_required` | Approval missing, hash-mismatched, or decision != `"approve"` | Obtain an explicit approval bound to the advisory hash |
| `invalid_approval_time` | Approval time not finite, or outside `[issued_at, expires_at]`, or `> now` | Re-approve within the window |
| `ack_missing` / `ack_invalid` | Ack absent, or hash/status (`accepted`) wrong | Get a proper readback/ack for the same advisory |
| `invalid_ack_time` / `ack_late` | Ack timestamps inconsistent or after expiry | Re-acknowledge within the window |

Construction-time errors (not `GateRejected`): duplicate `aircraft_id` →
`ValueError` from `WorldState`; unknown id in `state.get(...)` → `KeyError`.
Note the demo's own guard: if any of its end-to-end invariants fail it prints
`FAIL: demo invariants violated: [...]` and exits 1 — that means the code's
contract broke, not the scenario.

Every rejection is itself appended to the audit log (`reject` event), so a
denied operation is still evidence, not silence.

## CI and the audit-chain story

CI (`.github/workflows/ci.yml`) runs `pytest -q` on Python 3.12 for every push
and pull request, with SHA-pinned checkout and setup-python actions and pytest
as the only installed dependency. The regression suite this protects is the
same story the demo tells: the audit log is a hash chain whose head can be
replayed and verified by anyone with the events, `AuditLog.verify` fails the
build on any tamper or breakage, and fail-closed tests pin the behaviors the
gate must never lose — stale/future states rejected, conflicting
recommendations rejected, NaN/inf state treated as conflicting, duplicate
aircraft ids rejected at construction, and approvals/acks bound by hash and
timing. A green build means the deterministic gate and its evidence trail still
behave exactly as documented.

## Known limits

Hackathon research prototype. Geometry and timing are evaluated on synthetic
finite cases; the repo claims no operational aviation safety, no exhaustive
numeric coverage, no live ATC integration, and no production deployment. The
demo uses fixture identities for approval/readback with no real-world
authority.
