# Preserve Python audit hashes at scientific-notation boundaries

Valid simulated approvals can produce a Python-valid audit that the browser marks broken. With a real native planned advisory at clock `0`, approval at `0.000001`, acknowledgement at `0.000002`, and application at `0.000003`, native `ControlRoom.apply` advances the world from version 7 to 8 and writes all four success events. Python hashes `"approved_at":1e-06`; the old TypeScript verifier hashes `"approved_at":0.000001`. These different bytes invalidate the same otherwise intact audit.

A transaction following the UI's ordinary `+0.2/+0.4/+0.5` offsets from an accepted clock `-0.199999` reproduces the small-fraction mismatch. At clock `1e16`, Python emits `1e+16` while TypeScript previously emitted `10000000000000000.0`; world and advisory hashes also diverge. A large fractional clock `1e15+0.25` serves as an unchanged-format control.

## Change

Only `web/airspace/src/core.ts` numeric serialization changes. For finite values outside the `seq`/`version` integer-key convention, it takes the shortest digits from `toExponential()` without a precision argument. It emits scientific form for decimal exponents below -4 or at least 16, with an explicit sign and at least two exponent digits, matching Python float `repr`. Ordinary fixed decimal output, integer-float `.0`, signed zero, and nonfinite refusal retain their existing behavior.

The native Python formatter and gates do not change. This contribution receives the separate frozen timestamp guard in `python-worker.ts` (SHA-256 `54882f2f3f4b351f17fec31f6f75cc21e9446da6486ab911ac69a3d0e7bb52db`) and preserves its bytes. The core overlay must be qualified with that guard present.

The production core SHA-256 is `4f705e060ec70735c2687c7f27ccefb4f070a699352a974b4436ebf693b615ac`; the new permanent test SHA-256 is `86b0eb813c03fecb7c188f6bb77d76f4b77cea8fe37c2d282cf602dafc27f235`. Receiving base is native main `e522e53246986327b7903f3c404abf8a04ab5f1d` plus the declared guard. Every input and overlay is pinned in the archive.

## Qualification

| Check | Baseline | Candidate |
| --- | --- | --- |
| Original four admitted-transaction probe, normal and optimized Python | 1 pass / 3 fail | 4 pass / 0 fail |
| Permanent new regression, normal and optimized Python | 1 pass / 4 fail | 5 pass / 0 fail within combined suite |
| Complete native web suite plus the frozen guard regression | — | 15 pass / 0 fail in both modes |
| Native prepare-Python, TypeScript and Vite build | — | Pass |

The four transactions use actual native planning and application, with the normal JavaScript JSON transport between calls. The checks compare each signed event's complete canonical bytes and the world/advisory hashes, then verify the actual TypeScript audit and reject a modified signed approver payload.

The fifth permanent regression compares twelve explicit positive/negative cutoff, signed-zero, subnormal and maximum-finite samples with actual Python `canonical_bytes`; it also checks exact JSON roundtrip, integer keys, and preserved nonfinite refusal. There are no skipped tests. Original failures and the original probe remain unchanged in the archive.

## Replay

In the native checkout, receive the frozen timestamp guard and apply these two code/test files. Use the repository's existing dependencies:

```sh
cd web/airspace
npm test
PYTHONOPTIMIZE=1 TOWEROPS_TEST_OPTIMIZE=1 npm test
npm run build
```

The five new tests are in `tests/python-float-parity.test.mjs`; they require an existing Python interpreter, selected by `TOWEROPS_PYTHON` when needed. The 15-case recorded suite also includes the separate production worker's three-case `python-audit-interop.test.mjs` regression, pinned in `native-checkout-pins.json`.

For the original isolated probe, extract `evidence.tar.gz` and use an existing TypeScript package:

```sh
PARITY_TYPESCRIPT=/absolute/TowerOps/web/airspace/node_modules/typescript PARITY_VARIANT=baseline node probe_valid_transactions.mjs
PARITY_TYPESCRIPT=/absolute/TowerOps/web/airspace/node_modules/typescript PARITY_VARIANT=candidate node probe_valid_transactions.mjs
```

The baseline intentionally reports three failures. `PARITY_OPTIMIZE=1` selects optimized Python for this probe. The exact receiving checkout was built from `git archive`, with explicit verified overlays and private output/cache paths.

The underlying format choice is supported by CPython's `format_float_short` in [pystrtod.c](https://github.com/python/cpython/blob/main/Python/pystrtod.c) and the no-precision [ECMAScript toExponential algorithm](https://tc39.es/ecma262/2024/multipage/numbers-and-dates.html#sec-number.prototype.toexponential). Qualification executes native source and the actual TypeScript verifier in Node; it does not claim a loaded browser/Pyodide session or live deployment.
