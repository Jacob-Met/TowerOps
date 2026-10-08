# Validate the numeric aircraft candidate without relying on a peer

## Source and ownership

This native correction starts from TowerOps main
`e522e53246986327b7903f3c404abf8a04ab5f1d`. The subsequent main
`d99d238f7da62d74852e07fc90da406f87c2d371` has the same `towerops.py` Git blob,
`97f79799414266ce74ae723fbb9ccbb653969a7a`. The selected source files were
verified against the GitHub tree and blob contents, including the executable
mode of `explorer.py`. The complete initial tree contained no `AGENTS.md`.

The native worker owns only `towerops.py` within `SafetyPolicy.advisory_safe`,
`tests/test_advisory_numeric_candidate.py`, and this receipt. The current
[selected-flight editing claim, issue #32](https://github.com/Jacob-Met/TowerOps/issues/32),
expressly excludes the Python planner and safety gate and the TypeScript core
algorithms. Its selected-flight UI paths are outside this correction. The
parent receiver owns the corresponding TypeScript work and publication;
independent browser receiving work uses a separate tree.

Sources:

- [Pinned native gate](https://github.com/Jacob-Met/TowerOps/blob/d99d238f7da62d74852e07fc90da406f87c2d371/towerops.py)
- [Existing paired nonfinite regressions](https://github.com/Jacob-Met/TowerOps/blob/d99d238f7da62d74852e07fc90da406f87c2d371/tests/test_nonfinite_failclosed.py)
- [Browser worker that invokes the native gate](https://github.com/Jacob-Met/TowerOps/blob/d99d238f7da62d74852e07fc90da406f87c2d371/web/airspace/src/python-worker.ts)

## Reproduced failure

Create a fresh world containing one aircraft, `ALONE`, at `(0, 0, 10000)` with
zero rates. Bind an advisory to that exact world's hash, set its horizontal
velocity to `(NaN, 0)`, and supply matching approval and acknowledgement inside
the advisory's valid time window. On the original source:

- `SafetyPolicy.advisory_safe` returns `True`.
- `ControlRoom.apply` returns version 2 with a `NaN` velocity.
- The audit contains `screen_pass`, `approval`, `ack`, and
  `simulated_actuation`; its hash chain verifies.

NaN comparisons do not exceed a numeric bound. The existing pairwise guard
rejects unknown fields, but a singleton has no other aircraft to compare
against. Unknown retained position or altitude can pass for the same reason.
Malformed scalar commands can also escape as a `TypeError` before a rejection
is audited.

## Native correction

Seven added lines reuse the existing `_finite_number` predicate:

1. Validate all three commanded rates before performing magnitude or climb
   comparisons.
2. Validate the target's retained position and altitude after target lookup.

The resulting candidate is therefore checked even when no pairwise separation
calculation occurs. Failure returns through the existing `unsafe_advisory`
rejection path. The native regression exercises complete application with valid
approval and acknowledgement, checks that the original world hash is unchanged,
and verifies that the only audit event is the rejection and its chain is valid.

Only fields present in the resulting candidate must pass these guards. Finite
commands can still replace unknown previous velocity and climb rates; this
existing recovery behavior is tested both with a singleton and with a distant
peer. The change preserves separation geometry, speed and climb limits, time
checks, binding hashes, and the approval/readback protocol.

## Verification

All checks ran on Python 3.12.14. The original existing suite passes: 61 tests
and 84 unittest subtests with pytest 9.1.1. The 30 new cases against unchanged
native source produce **18 failures and 12 passes**: 16 malformed candidates
are actuated, and two malformed commands raise `TypeError` instead of an audited
gate rejection.

With the correction:

| Check | Result |
| --- | --- |
| Complete suite, CI-pinned pytest 8.3.5 | 91 passed |
| Complete suite, pytest 9.1.1 | 91 passed, 84 subtests passed |
| Whole-repository Ruff, CI-pinned 0.16.10 | All checks passed |
| `python tools/generate_airspace_reference.py --check` | Four real-source scenarios unchanged |
| `python demo.py` | Exit 0; conflict resolved; audit valid |
| `git diff --check` | Passed |

The regression cases cover all three commanded-rate and retained-position
axes with NaN and both infinities, representative boolean/string/null fields,
valid stationary commands, exact positive and negative speed/climb boundaries,
replacement of unknown previous rates, and an unknown target. Existing paired
geometry, planner, HTTP explorer, and audit replay tests remain in the full
suite. Browser reference data was checked without regeneration.

The native commands are reproducible with the dependencies pinned by
`.github/workflows/ci.yml`:

```bash
python -m pytest -q
python -m ruff check .
python tools/generate_airspace_reference.py --check
python demo.py
```

Local test execution disabled third-party pytest plugin autoload and disposable
caches and used an isolated dependency directory. No dependency or workflow
change is part of this correction.

The frozen corrected `towerops.py` has Git blob
`3f541e5f0f3a05dac9d12c96e75d3d69ef3377d1` and SHA-256
`6c0634e2ff02f38ff99a0983d5a3564b877553cf2f426e0da269cbd5a48c7874`.
The parent receiver combines this native correction with its TypeScript and
actual browser receiving evidence before publication. This receipt records the
native change and its local qualification.
