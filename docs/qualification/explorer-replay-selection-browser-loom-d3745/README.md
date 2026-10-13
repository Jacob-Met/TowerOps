# Explorer replay selection — later browser receiving and recovered records

The selected-file guard in [PR127](https://github.com/Jacob-Met/TowerOps/pull/127) now has a separate actual Firefox receiving result: the newer file keeps its MISMATCH verdict after an old MATCH response completes, and explicitly clearing the file input keeps the verdict blank. The displayed simulation and its export remain unchanged.

The [practical browser guide](independent/README.md) opens the exact saved A/B fixtures and retained source projection. From the repository root, enter that guide's directory before its commands:

```sh
cd docs/qualification/explorer-replay-selection-browser-loom-d3745/independent
python3 -B candidate-source/explorer.py serve --port 8765
```

This launches the normal local Explorer for new use. It is distinct from the retained controlled-HTTP browser qualification and is not a claim that the extracted packet was replayed.

## Actual receiving result

Loom's original-first course used exact published assets and real native CLI-produced export/replay replies. The original source has three observed presentation failures. Its raw receipt remains `accepted=false`, including two additional inline-font classification flags. The separate audit and narrowly corrected v2 receiver explain those flags without rewriting the original receipt or repeating that browser course. The candidate v2 course has 23 passing comparisons, three actual native CLI commands, two actual Firefox file-selection courses, and clean browser/server closure. Each retained old response has an explicit browser completion witness before the final status observation.

The guide distinguishes the controlled transport from production Python HTTP framing, file-input clearing from cancelling a chooser, and page request observations from an OS-level network audit. Both raw receipts, both driver versions/freezes, exact streams, six screenshots, source copies, fixtures and the original mode-adaptation note remain under `independent/`.

Anvil's [independent review](browser-independent-review.json) records full driver/receipt/guide reading, recomputation of 23 candidate comparisons, exact readback of six raw streams, a 23-file identity audit, and two final screenshot observations. Anvil did not rerun the product, native CLI or browser.

## Two original records recovered after source publication

The original source publication and Node-only packet disclosed that two native-only records were unavailable during a host outage. Those exact original bodies were subsequently recovered through read-only access and matched every byte/hash/Git ID from the unchanged original 26-row authority:

- [source-receipt.json](recovered-original/source-receipt.json)
- [candidate-1.stdout](recovered-original/author/candidate-1.stdout)

[recovered-original/custody-binding.json](recovered-original/custody-binding.json) binds them to their original authority and independently read-back detached Git blobs. No timestamp regeneration, test replay or original-record reconstruction occurred. The earlier source commit, qualification disclosure and [Node-only opening packet](https://docs.google.com/document/d/1WM2VMQqntAXst8adCA0fg6cduYY0R1mqxYMPi9YLhNs/edit) remain unchanged. This directory is the later closure evidence.

## Source identity and publication scope

The browser candidate is `67cc9807c096f3e4b6f7b1155008294415f31d23`, ordinarily adopted as `8a87ad1331d7e7100367dde583d59560836f9eb8`; both identify tree `ffacbb9ace1a360d0aeca2bdb33b70e0c0422418`. The received source projection is pinned to that version. It is not a whole-repository checkout or a qualification of later source changes.

This follow-up changes no production source, test, workflow, historical receipt or earlier packet. Its original 60-payload Loom descriptor is retained verbatim as [independent-publication-inputs.json](independent-publication-inputs.json). Publication requires the independent descriptor and explicit support records to pass the maintained publication-layout validator before Git tree, commit or ref creation. All simulations, approval/acknowledgement inputs and identities are local synthetic fixtures; no live aviation or provider system is involved.
