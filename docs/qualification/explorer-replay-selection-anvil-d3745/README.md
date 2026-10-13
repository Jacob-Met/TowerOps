# Explorer replay status follows the selected file

The local synthetic Explorer now keeps the replay verdict with the file currently selected under **Replay exported JSON**. Selecting another file retires older asynchronous reads and response handling. Clearing the file input clears the status. Already-sent requests may complete, but they cannot replace the current verdict or error. Replay leaves the displayed scenario and its export unchanged.

## Use

From a TowerOps checkout containing this change, use Python 3.12+:

```sh
python3 explorer.py serve --port 8765
```

Open the printed loopback URL, run a synthetic case, and export its JSON. Select that file for replay. The existing MATCH, MISMATCH and rejection messages retain their meanings. When changing selections quickly, only the most recently selected file may update the replay status. These remain local deterministic fixed-fixture results, with no live traffic or authority claim.

The [Explorer guide](../../../EXPLORER.md) describes the supported scenarios, export format and ordinary CLI. The focused regression needs Node.js 20+ and built-in modules only:

```sh
node tests/test_explorer_replay_selection.cjs
```

## Exact reviewed change

The three source leaves are `web/app.js`, `tests/test_explorer_replay_selection.cjs`, and `EXPLORER.md`. The integration base is `c7714bbe09c37ead994780af53078df11c99925b`, tree `1614130c0adce082b065e4f59cc5fd359e90083d`. The replay-handler replacement and adjacent selection identity are the only app change; reversing that span restores the entire original app. The run/render/export/scenario bodies, Python engine and server are preserved.

[Root's source review](peer/root-source-review.json) accepted the complete three-file change. [Source binding](author/source-binding.json) and [the complete diff](author/source.patch) preserve the original frozen identities. [Issue126](https://github.com/Jacob-Met/TowerOps/issues/126) records the ownership fence.

## Actual qualification and honest receiving limits

The original full-script Node course ran before the candidate existed: **3 passing controls and 7 expected failures**. Its [exact receipt](author/original-receipt.json) and [complete stdout](author/original.stdout) are retained. The candidate then passed **10/10** with the unchanged test, and syntax checking passed. The [complete candidate receipt](author/candidate-receipt.json) preserves command results and all source before/after identities.

These are controlled DOM, file and fetch lifecycle tests on the native ThinkPad. They cover stale reads, errors, HTTP/JSON completion, same-file reselection, clearing, current refusal and explicit recovery. They are not actual browser or real-network receiving. Root's independent review did not replay the tests. A separate original-first browser course remains pending with Loom; no browser acceptance is asserted here.

The native route became unavailable after qualification. Twenty-four of the original twenty-six selected source/evidence bodies were recovered exactly and are published. **Two bodies remain on the unavailable native device:** `source-receipt.json` (3,149 bytes) and `author/candidate-1.stdout` (2,154 bytes). Their original paths, SHA256 digests and Git identities remain in the unchanged [original author authority](author-inputs.json) and [custody record](custody-recovery.json). The complete candidate JSON receipt supports the recorded passing result; the missing stdout has not been fabricated or regenerated.

The [available evidence descriptor](available-evidence-inputs.json) explicitly selects the twenty-one available original supporting records plus the exact root review. Its rows were fixed before preparation of the Git object plan. The source allowlist is independently the original three source records; current publication documents are separately admitted support.

Raw historical records retain unpublished-at-execution metadata, native paths and permissions. The source scripts and staged baseline projection are audit evidence, not a portable installer. Use the ordinary repository commands above. Original author notes remain unchanged and describe their then-pending receiving state. The earlier metadata-only E2BIG refusal changed no source or test course.

The maintained `estate-push-tools` planner and publication-layout validator at `d05c6da415d387fc3787a9655e054d01fb13288c` receive this explicit selection before Git tree/commit/ref creation. Their selected-blob report does not authenticate caller-supplied origin metadata or replace complete current-parent preservation review. No GitHub Actions execution is requested.
