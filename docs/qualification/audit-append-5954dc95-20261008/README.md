# Audit append ordering and payload ownership

Concurrent `AuditLog.append` calls selected the same sequence and previous hash before awaiting WebCrypto. The original event also kept the caller's payload object. A later caller edit could therefore change an already recorded approval or acknowledgement without updating its hash.

The maintained TypeScript `applyAdvisory` flow is a concrete consumer: it records approval and acknowledgement objects supplied by its caller. The new regression executes the real planner, screening, approval, acknowledgement and simulated actuation, then reuses those caller objects and checks the complete original event history.

## Change

The append producer snapshots the payload at invocation, checks the existing canonical representation and queues hashing/publication per log. It checks that the intended history still exists before hashing and before publication. A failed payload or digest publishes no event, consumes no sequence and does not prevent subsequent work.

`append` still returns the event hash. Verification and the original canonical metadata for imported Python prefixes are unchanged. Direct edits through the public `events` array can still invalidate a chain; this change does not repair or authenticate such edits.

Only `web/airspace/src/audit.ts`, the new `web/airspace/tests/audit-append.test.ts`, and this unique qualification directory belong to the contribution. Python, GUI, planner, gate, actuation, wire format, dependencies and workflows are unchanged.

## Executed native qualification

Execution used DESKTOP-LA7CMTA, Node v24.21.0, the unchanged project dependency lock (Vitest 4.1.11, TypeScript 5.7.3, Vite 8.3.3) and Python 3.13.15 for existing interoperability cases.

| Receiving stage | Original | Candidate |
| --- | --- | --- |
| Frozen Node/WebCrypto producer checks | 5 failed, 6 passed | 11 passed |
| New maintained Vitest regressions | 6 failed, 2 passed | All 8 passed within the full suite |
| Full frontend Vitest suite with UTF-8 Python pipes | Not rerun as a full original suite | 234 passed, 0 failed, 0 pending |
| Ordinary Python asset preparation, TypeScript and Vite build | Not run on original | Passed |

The new tests cover invocation ordering, nested payload snapshots while queued and after completion, signed zero, invalid payload and digest recovery, imported Python-prefix bookkeeping, history replacement before/during hashing, and the actual advisory consumer.

All 75 captured input hashes were unchanged through the final run. The only tracked modification was audit.ts; the focused regression was the only untracked product file.

### Preserved receiving failures

The first full candidate run remains **233 passed / 1 failed**. Its existing decision-trace Unicode test declares UTF-8 subprocess transport, but native Python used cp1252 on its pipes. An exact replay of that test's producer and the shipped Python bridge showed replacement-character corruption and a rejected chain. With process-local `PYTHONUTF8=1`, the same bytes remained valid and the unchanged full suite passed. No test body, candidate source or production configuration was changed to obtain this result.

The initial setup also stopped at its revision guard when the clone received a newer documentation commit. Explicit comparison proved the relevant source/lock blobs unchanged before the setup pin advanced. The first oversized single evidence packet is retained as a packaging failure; its complete contents were sealed into two lossless parts.

## Source identity and publication fit

- Original source snapshot: `89529c5459b1c3d52448e197de2b2f7fe8b6d128`.
- Full native project qualification: `a11c30497896455de3e74c21e530787dc7982bca`, containing only five additional release documents over that snapshot.
- Publication parent: `0291a40a82d8981047349b6dc6b68137a71a45fd`. The saved-policy comparison changes no tested code, frontend tests/configuration, dependency lock or Python interoperability module; its separate source and evidence are preserved.
- Original audit blob: `abb707db69d866ff762f8bc2c40fde81fc3b7d3b`.
- Candidate audit SHA-256: `024a2c2905ca190e95914ea8e42dab4880ee453e6391b0a058969b40a1e47737`.
- Maintained test SHA-256: `ded38989892ae714f2b2110189a5434ed292974a9fcdb831e4f2879c7505c882`.

[Source claim](https://github.com/Jacob-Met/hamon/issues/143#issuecomment-6066906564) and [complete native source/receiving journal](https://app.notion.com/p/3f3aedcdf4a58172be7dc895d9ae488e) retain attribution and the current owner boundaries.

## Complete evidence and replay

The journal attaches `tower-audit-receiving-manifest.json` and both `tower-audit-receiving-part-N.json` files. They contain 106 complete text files: captured project source/tests, original and candidate producer inputs, all native runners, failed/successful receipts, raw logs and the encoding diagnostic. Every embedded file was decoded and hashed before sealing, and all three attachments were downloaded and compared exactly with the sealed native originals.

Two existing PNG captures remain byte-pinned repository references; no new browser receiving is asserted. The manifest identifies every included path, byte count and SHA-256. Each part has independently checked gzip and decoded-payload hashes. Preserve the originals and restore into a fresh owned directory after validating all paths and hashes.

For normal receiving on a checkout of the reviewed source, use the unchanged project commands:

```text
cd web/airspace
npm ci
npm test
npm run build
```

On Windows, give the maintained Python subprocess oracle a supported interpreter through `TOWEROPS_PYTHON` and UTF-8 pipes through process-local `PYTHONUTF8=1`. The exact archived drivers retain their original LA7 interpreter path and source pins; any receiving-path adaptation belongs in a separate copy and receipt.

The native stage remains:
```text
C:\Users\minec\AppData\Local\Hamon\workspaces\chatgpt-5954dc95-tower-audit
```

This receipt qualifies the TypeScript producer and its TypeScript consumer. Hosted CI, source integration and any normal main-push static publication are recorded separately on the PR and journal. It makes no browser, installed-service, live-traffic or estate-wide completion claim.
