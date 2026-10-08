# One-step traffic Undo: source and receiving evidence

This packet accompanies issue [#51](https://github.com/Jacob-Met/TowerOps/issues/51). An accidental committed traffic edit can be recovered once while its exact world, policy, clock and scenario context remains applicable. Undo restores the prior aircraft and selection as a new revision, clears pending proposals and approvals, and retains the raw JSON draft and audit history.

## Current source qualification

The seven-file implementation and maintained browser gate were frozen at [`8c1ba62144c36834e47e8a9e327f59ae1214c40f`](https://github.com/Jacob-Met/TowerOps/commit/8c1ba62144c36834e47e8a9e327f59ae1214c40f), directly on main `5b3015567a01017245c5f715c1bce65e20a06138`. Its reconstructed tree is `2a35c148480763570f6d9e0c8448d678cebb8c4a`: all 454 unrelated existing leaves and their modes remain exact. The four changed existing paths are the workbench entry point, HTML, README and Airspace workflow. The three additions are the Undo helper, its 21 pure tests and the browser receiver.

The merged playback, Reset, radar and repaired playback test source is preserved. The separate saved-scenario and native CSV authors retain their branches and integration authority. Complete source pins and preservation counts are in [source-receipt.json](source-receipt.json).

The root agent independently read and authenticated all seven frozen files and the full current-base diff. It accepted the bounded source scope, one-step applicability logic, ten native browser groups and insert-only workflow extension. This is source and evidence review; the hosted browser run remains a separate receiving gate.

## Historical native evidence

[Native history archive](native-history.tar.gz) contains 53 regular members, including a complete 52-file manifest. The archive was produced in memory from the original private Mac files, then independently decoded and checked in cloud memory: every member name, size and SHA256 matches the manifest. No other worker's files were changed.

| Stage | Exact source | Recorded result |
| --- | --- | --- |
| Original native baseline | `093f88b29d6e1ede778f967528c7e010b7689ab1` | 133 Vitest tests, ordinary TypeScript/Vite build and four-scenario reference gate passed. |
| Historical Undo candidate | `53aa5048b6585aa08592d5513cfcf555a8bba018` plus the four archived candidate files | 154 tests passed: 133 prior tests and 21 Undo tests. Ordinary build and exact-main preservation checks passed. |
| Five Mac browser attempts | Original baseline/build or the explicitly recorded exact-byte transport diagnostic | Navigation/transport failures occurred before product assertions. Their original failed reports and available raw streams are retained. They establish no missing-Undo counterexample or successful browser behavior. |
| Native Python fixture control | Exact archived worker bootstrap and `towerops.py` hashes | The fixture admits a real proposal, four-event apply and a second proposal. This qualifies the browser fixture's native inputs, not a browser execution. |

The historical helper, pure-test and HTML bytes remain the same in the current composition. Current `main.ts` additionally carries the owners' newer playback and radar source. Historical 154-test results must not be presented as tests of that later composition.

Archive SHA256: `e0b4cd1ef9f1ac3a9b9a1cc3c7d061bb4bb8414f312ea9a8bff0c91506efdb8c`.

Manifest SHA256: `abe79c92f71078bb48aa1482284d24f45b70b703a9c7f8a28653aa97daad3d04`.

## Maintained browser receiving gate

The existing Airspace workflow keeps its current action, toolchain, dependency, prior-gate and deployment steps. Two added steps run the maintained receiver using its already installed Chromium and retain compact evidence.

For a pull request whose actual base lacks the Undo helper, the gate builds that authentic base and executes the unchanged original three method bodies. It requires one specific missing-Undo failure after a real successful removal, plus two passing preservation controls. The original report stays `status: failed`; a separate `expectedMissingUndoMatched: true` is required. A transport, startup, cleanup, source-mutation or other assertion failure cannot satisfy that expectation.

The candidate runs ten native CDP groups covering exact recovery, all supported edit paths, failed/no-op preservation, open-edit blocking, policy round trips, actual playback advancement, load/Reset context changes, and a real Python proposal/approval with exact downloaded audit and raw-draft preservation. Reports bind actual Git HEAD/tree, receiver bytes, source/build bytes, browser identity, input observations and profile cleanup. Screenshots and native trace bytes are retained in the `towerops-traffic-undo-browser` Actions artifact.

At this packet's creation, those hosted baseline/candidate executions are pending. Their eventual run, head, tree, results and artifact hashes must be read and recorded before source acceptance for merge. No merge, deployed application behavior or estate-wide completion is claimed by this historical packet.
