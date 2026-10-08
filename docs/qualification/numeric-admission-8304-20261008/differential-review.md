# Independent TowerOps candidate-state differential

Observed 2026-10-08 at 09:23:14 UTC. Both candidates passed all 14 cases. There was no newly introduced parity or admission regression in this bounded matrix. All 56 baseline/candidate evaluations preserved the input world. This is a policy-level review; it does not repeat the writers' complete gate, actuation, browser, or full-suite tests.

| Case | Python baseline → candidate | TypeScript baseline → candidate |
| --- | --- | --- |
| Finite diagonal at speed 6 and climb 3000 | Accept → accept | Accept → accept |
| Finite replacement with distant peer | Accept → accept | Accept → accept |
| NaN commanded velocity, singleton | Accept → reject | Accept → reject |
| Boolean commanded velocity, singleton | Accept → reject | Accept → reject |
| Null commanded climb, singleton | TypeError → reject | Accept → reject |
| String retained altitude, singleton | Accept → reject | Accept → reject |
| Boolean retained y, singleton | Accept → reject | Accept → reject |
| NaN retained x, singleton | Accept → reject | Hash error → same hash error |
| Replace old NaN/+Infinity/−Infinity motion, safe peer | Accept → accept | Hash error → same hash error |
| Replace old NaN/+Infinity/−Infinity motion, conflicting peer | Reject → reject | Hash error → same hash error |
| Replace old true/"0"/null motion, safe peer | Accept → accept | Accept → accept |
| Replace old true/"0"/null motion, conflicting peer | Reject → reject | Reject → reject |
| Malformed untouched peer altitude | Reject → reject | Reject → reject |
| NaN commanded velocity with distant peer | Reject → reject | Reject → reject |

The peer-sensitive cases independently check that candidate replacement repairs only the target's overwritten motion fields, still checks actual candidate separation, and never repairs an untouched malformed peer. The original singleton versus two-aircraft NaN behavior reproduces why pairwise checking alone left a gap.

Each runtime generated its own world hash. The TypeScript hash error is the unchanged `TowerOps state must be finite` rejection from `core.ts`, which occurs before candidate admission for old nonfinite state. It is a preexisting encoding limitation and is not counted as numeric-policy equivalence. Hash formatting and timestamp interoperability remain with the owner in hamon issue #140 comment6056309821. Completed TowerOps issue #32 UI spans were excluded.

## Exact sources and reproduction

Python 3.12.14; Node 24.19.0; TypeScript 5.7.3 syntax-only in-memory transpilation. No project source, service, native state, or shared record was changed.

| Source | SHA-256 |
| --- | --- |
| Python baseline (`74593888a7b6b1d63b3acc2dbde678a4a9d2d0b7:towerops.py`, local source snapshot) | `8abe33edea5a7bdcdf6e6f81d31168c485f5a29229aa8d14c3310ae08728745e` |
| Python candidate (`production/towerops/towerops.py`) | `6c0634e2ff02f38ff99a0983d5a3564b877553cf2f426e0da269cbd5a48c7874` |
| TS baseline (`/dev/shm/hamon-8304-towerops-ts/baseline/planner.ts`) | `04e38fc3b87fae9d4531e6867ad2bf81dfdf48fb86053aab7d4f83266b21652f` |
| TS candidate (`/dev/shm/hamon-8304-towerops-ts/web/airspace/src/planner.ts`) | `5a8139b8fe31ffe51f7a7af3273ef84c776dccbc85954a075a8476515a2f0c74` |
| Shared TS `core.ts` | `99855c0bea2f6c04df3fc972aeb885df09015d0d071b4ab3bdeaeefedaf1d147` |
| Matrix `cases.json` | `8ab840d80308afbc5190ece6e278c45140f3e87845ab2ba7ada0b2a5b1d9a50a` |

Run from `/workspace/scratch/8304a40f6f50/work/towerops-differential`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 python_matrix.py
node typescript_matrix.mjs
```

Raw results are `python-results.json` and `typescript-results.json`; both retain the outcome, error, and input-immutability assertion for every case and both revisions. There is no newly introduced counterexample to route back for a repair.
