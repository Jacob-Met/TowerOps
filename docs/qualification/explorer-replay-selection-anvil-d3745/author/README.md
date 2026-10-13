# Explorer replay-selection receiving

This change keeps the local synthetic Explorer's replay status with the file currently selected in **Replay exported JSON**. A later selection retires earlier asynchronous file reads and response handling. Clearing the file input clears the status. Already-sent requests may complete; they cannot replace the current verdict.

The three contributed source leaves are `web/app.js`, `tests/test_explorer_replay_selection.cjs`, and `EXPLORER.md`. Removing the replacement replay handler and its adjacent selection identity reconstructs the entire original app byte-for-byte. The run, render, scenario load, plotting and export bodies remain exact. The Python engine, fixed scenarios, HTTP server, Airspace Lab and inherited tests are unchanged.

## Use and focused verification

From a complete TowerOps checkout, start the supported local Explorer:

```sh
python3 explorer.py serve --port 8765
```

Open the printed loopback URL, run a synthetic case and export it. Select that saved JSON under **Replay exported JSON**. A complete unchanged export should report MATCH; a supported export with edited result fields should report MISMATCH. Malformed input or a failed read/request reports rejection. These are local deterministic replay results, with no authenticity, live-traffic or approval claim.

The maintained regression test needs Node.js 20+ and built-in modules only:

```sh
node tests/test_explorer_replay_selection.cjs
```

For an explicitly supplied alternate app file, pass its path as the one positional argument. The author used this to receive the unchanged original source before creating a candidate.

## Retained author sequence

The original source is pinned to commit `c7714bbe09c37ead994780af53078df11c99925b`. Eight received source/document leaves were matched to that complete Git tree by byte length, Git blob identity and file mode. Native identity was hamon-thinkpad, jacob UID 1000, through Remote Desktop Commander device `cadafaf3-4d0b-4c4f-a0d3-34a95d2cec90`.

The original full-script Node course ran before candidate creation: **3 passing controls and 7 expected failures**, with no cancelled or skipped tests. The failures cover superseded file reads, read errors, HTTP responses, JSON bodies and transport errors, selection clearing, and reselection of the same File object. Three controls preserve current MATCH/MISMATCH, current refusal and explicit corrected retry behavior. These are controlled DOM/fetch lifecycle observations, not a real-browser or real-network result.

The unchanged ten-method test then passed **10/10** on the candidate, and `node --check web/app.js` exited 0. The candidate source inventory and all original inputs were unchanged by execution. The original failure streams, both actual commands, return codes and candidate inventory remain in their raw receipts. There is no combined backend, full-repository, Airspace, installed-service or external-use claim.

The two staging scripts preserve the actual executed Python bodies. They contain exclusive-stage guards and absolute receiving paths and are audit evidence, not a portable installer. The maintained Node test is the ordinary portable test entry.

A first metadata-only source-binding launch was refused by the process interface with `spawn E2BIG` before process creation because it embedded both large staging scripts. Those scripts were subsequently written separately and the smaller binding check ran. Neither the product source nor either test course was changed or replayed as a consequence.

## Publication boundaries

The source allowlist has exactly three leaves; supporting author records are enumerated independently. A complementary browser receiver, its original descriptor and any later publication or main-composition binding remain distinct from the author course above. Raw execution receipts retain their unpublished-at-execution identity.

No GitHub Actions execution is requested. Both inherited workflows were read before the issue reservation; the standing no-Actions constraint governs publication and integration.
