# Whole-number approval/readback timestamps

## Receiving change

The Airspace Lab's real Python worker could produce a valid audit chain which the
existing browser verifier displayed as broken. With an imported world clock of
`0.8`, the UI's approval time is `1`; JSON serialization sends it as an integer.
Python hashed `approved_at: 1`, while the browser's existing float-field contract
hashes `approved_at: 1.0`. Clock `0.6` exposes the same problem at readback time.
The successful simulator transition and the incorrect audit display were distinct
outcomes; the retained baseline exercises both.

`web/airspace/src/python-worker.ts` now restores an exact JSON integer to a float
only for `approved_at` or `acknowledged_at`. This matches the float fields declared
by the native `Approval` and `Ack` dataclasses and the existing state/advisory
conversion. Boolean, string, null and existing float inputs retain their types,
so the native gate continues to reject malformed times. The Python canonical
encoder, TypeScript verifier, policy, planner, UI and Worker client are unchanged.

## Exact source

- Upstream repository: `Jacob-Met/TowerOps`.
- Receiving base: `e522e53246986327b7903f3c404abf8a04ab5f1d`, read from the live
  `main` branch before implementation and present as this checkout's baseline.
- Original worker Git blob: `ca8698b11d0f7b810f84e00dea538b09079f7b08`.
- Candidate worker SHA-256:
  `54882f2f3f4b351f17fec31f6f75cc21e9446da6486ab911ac69a3d0e7bb52db`.
- Native Python: `towerops.py`; browser consumer: `web/airspace/src/audit.ts`
  and `web/airspace/src/core.ts`. Their exact identities are in the source manifest.
- No `AGENTS.md` exists in the recovered repository tree.

The only production implementation change is the worker timestamp boundary.
The additional `.mjs` test invokes the exact embedded `browser_request` function
with native Python, then verifies its resulting events using the actual browser
`AuditLog` implementation. It does not simulate the planner or reconstruct the
worker function. `.mjs` avoids introducing Node type dependencies into the
browser's TypeScript build.

## Verification

Run from `web/airspace`:

```sh
npm test
npm run build
```

The interoperability test requires Python 3 on `PATH`. Set `TOWEROPS_PYTHON` to an
existing Python executable when its command is not `python3`. The tests use the
existing fictional crossing scenario, an isolated process, and no network.

| Qualification | Result |
|---|---|
| Original worker, clocks `1000`, `0.8`, `0.6` | 1 passed, 2 failed |
| Candidate full Vitest suite | 10 passed, 0 skipped |
| Candidate TypeScript/Vite build at 2026-10-08 17:28 UTC | Passed; 14 modules transformed |
| Independent receiving, original worker | 3 passed, 4 failed per Python mode |
| Independent receiving, guarded candidate | 7 passed, 0 skipped per Python mode |

Independent receiving used normal and optimized Python. It covers approval-only,
readback-only, simultaneous and zero integer timestamps; malformed timestamp
refusals; missing, early and late readback; successive real actuation transactions
carrying the exact native audit JSON forward; Unicode payloads; and five tamper
mutations checked by both native Python and the browser verifier. Its separate
packet is identified by the manifest and retained by the integrating worker.

The initial TypeScript version of the authored regression harness lacked Node
type declarations under the existing project configuration. The final `.mjs`
harness resolves that build issue without a dependency change. A later attempt
to capture another build in shared temporary storage failed with `ENOSPC` while
copying the Pyodide runtime; `candidate-build.txt` preserves that environment
failure. It does not replace the earlier successful build or indicate a source
regression. No further build or browser-runtime installation was attempted.

## Ownership and limits

Contributor: `estate-68094585a1c2/production`. This is an isolated source change,
not a native task lease, service change, deployment or aviation assurance.
TowerOps #32 retains the selected-flight editor and its UI hooks. Contributor
`ff300ccd4fe0` retains the separate `python.ts` Worker retry/client change.

No installed local browser executable was available, so this packet does not
claim a rendered browser interaction or a Pyodide runtime execution. It qualifies
the actual shipped Python bridge and browser verifier in native test processes,
plus compilation of the real production bundle. The separate scientific-notation
number-serialization issue belongs to a subsequent independently qualified
`core.ts` contribution; this timestamp-boundary patch does not claim to fix it.

GitHub content creation was refused by the existing connector's secondary rate
limit during this cohort's work. The frozen patch is prepared for application to
the exact receiving base. No remote branch, PR, merge or deployment is claimed.
