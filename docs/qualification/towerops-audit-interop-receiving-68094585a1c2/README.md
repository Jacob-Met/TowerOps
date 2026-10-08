# Independent TowerOps audit interoperability review

The guarded timestamp repair passes all seven independent receiving controls in normal and optimized Python. The exact upstream baseline reports three passing controls and four failures in both modes; the failures are native Python-valid audit chains that fail the actual TypeScript browser verifier when an approval or acknowledgement timestamp is integral.

The reviewed production change is `web/airspace/src/python-worker.ts` at SHA-256 `54882f2f3f4b351f17fec31f6f75cc21e9446da6486ab911ac69a3d0e7bb52db`, against native main `e522e53246986327b7903f3c404abf8a04ab5f1d`. No implementation source was edited by this receiver. `source-pins.json` identifies every native input.

## What was independently exercised

- Integral approval only, acknowledgement only, both timestamps, and both zero.
- Boolean, numeric-string, null, list, and object refusal at each of the two timestamp fields, with no state returned and valid rejection audit chains.
- Missing, early, and late readback after an integral approval.
- Two successful applications preserving the exact prior audit JSON and its four-event prefix.
- Fractional timestamps and supplementary-plane Unicode in the signed approver payload.
- Payload, sequence, previous-link, claimed-hash, and order tampering, detected by both real verification implementations.
- Refusal after a successful integral application, extending the existing chain without a second simulated actuation.

The test uses the actual pinned `core.ts` and `audit.ts`, compiled in memory by the existing TypeScript compiler. A small loader resolves their sole local import; it does not replace canonicalization or verification. Python runs the exact embedded worker body against the pinned native `towerops.py`. Fixtures use native dataclasses and the actual `ControlRoom.apply` gate. They are independent synthetic inputs, not copied author fixtures.

During source review, the receiver raised the risk that an unconditional `float(v)` conversion would also convert boolean/string timestamps. The author restricted conversion to exact Python integers before the executable probe. The initial in-memory probe and final tests therefore cover the corrected frozen source; they do not claim a reproduced runtime failure for the earlier unfrozen draft.

## Replay

Extract `evidence.tar.gz` into a private directory. Use Node 24, Python 3.12, and the existing TowerOps TypeScript 5.7.3 dependency. Set `REVIEW_TYPESCRIPT` to the absolute path of that installed TypeScript package; `REVIEW_PYTHON` can select the Python interpreter. From the extracted directory:

```sh
REVIEW_TYPESCRIPT=/absolute/TowerOps/web/airspace/node_modules/typescript REVIEW_VARIANT=candidate node --test --test-reporter=tap review_audit_interop.mjs
REVIEW_TYPESCRIPT=/absolute/TowerOps/web/airspace/node_modules/typescript REVIEW_VARIANT=candidate REVIEW_OPTIMIZE=1 node --test --test-reporter=tap review_audit_interop.mjs
```

Replace `candidate` with `baseline` to reproduce the four expected failures. The test pins both variants before execution. `native_bridge.py` disables no gate, hashes no substitute payload, and uses the existing raw `audit_json` carrier when continuing or verifying a native audit.

These controls qualify the scoped number-restoration boundary and audit behavior, not browser/Pyodide loading or live UI state. General extreme/scientific-notation float parity remains outside this repair. Original baseline failure logs, the frozen source inputs, exact tests, initial refusal probe, final logs, and a machine-readable receipt are all inside the archive.
