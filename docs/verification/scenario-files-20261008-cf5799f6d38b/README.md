# TowerOps reusable scenario files — current source and native receiving

The current candidate adds local scenario download and reviewed import to the existing Airspace Lab. It restores traffic, all seven policy parameters, simulation clock, time scale and selected aircraft together. Choosing or canceling a file leaves the simulation and its decisions intact; explicit apply clears the preceding decision trace and its verification display, pauses traffic, and requires a new native planner/approval/readback cycle.

## Current source

| Item | Exact pin |
| --- | --- |
| Repository | `Jacob-Met/TowerOps` |
| Current main parent | `09b96e31d2867af5b7a9738406d0431cf1010090` |
| Current main tree | `4d22827647c0b2e37d11921aa5273f7a358bcdde` |
| Qualified current source tree | `d6b4a1ec5757144f848e1d6ce851a766a7413f2c` |
| Current source-manifest SHA256 | `50b09d63b2bec39ae6556e35e1347dd169558cffe7b16e8531c4d5fdbf76e1ef` |
| Source inventory | 136 tracked files; seven feature paths; 129 other main files unchanged |

The seven feature files are three additions—scenario-file.ts, scenario-ui.ts and their format tests—and four existing browser files: main.ts, index.html, style.css and README.md. Six are identical to the separately received verdict-reset successor `91131fb20fd40fd7281201f3626638cffac3f532`. The seventh, main.ts, also guards the asynchronous Verify chain completion against replacement or change of its audit trace. The preceding current-main composition `317ddf06e84c6b08f2e06ce634f5a64b264effd5` is preserved separately; its other 135 tracked files remain identical. Current main's audit-hash interoperability and numeric-admission changes remain intact, including native towerops.py, the TypeScript core/planner, the Python worker, their tests and prior receiving evidence. Dependencies and workflows were not changed.

## Reproduced product gap and behavior

The original exact parent `d99d238f7da62d74852e07fc90da406f87c2d371` exported raw WorldState only. Real-browser receiving placed two stationary synthetic tracks 7 NM apart: the saved 9 NM separation policy showed one conflict; changing the current policy to 3 NM and reloading the same exported world showed zero. Manually restoring 9 NM restored the conflict. The new scenario file keeps the policy and clock needed to reproduce the saved case. That unmodified parent, its actual outputs and its counterexample script remain under history/initial.

The version-1 JSON root has exactly format, version, world, policy, now, time_scale and selected_aircraft_id. Unknown keys, unsupported versions, malformed data, invisible policy changes and files over 256 KiB are refused. The parser preserves finite numeric values, including signed zero, canonical aircraft identity and the selected flight's membership. Policy and speed controls retain their existing bounds. All seven policy values are visible before applying the file. Imported text and file names are rendered literally.

Review is tied to the simulation context that existed when reading began. A changed world, clock, policy, speed, selection, planner result, approval, trace, traffic state or active editor invalidates the pending replacement. Canceled and superseded reads cannot publish their old result. Explicit apply replaces the validated scenario, clears obsolete proposals/approvals/audit events and the previous audit-verification message, and pauses traffic. An in-flight Verify chain result publishes only while its captured AuditLog, event-array identity and event count are still current. The existing raw-world workbench and selected-flight preview/apply workflow remain available.

The saved clock is restored faithfully. The native apply gate remains responsible for stale/future-state admission. No saved approval, audit chain or approval shortcut is accepted from the file.

## Current qualification

| Check | Result |
| --- | --- |
| Frontend Vitest suite, including native Python producer/consumer cases | 138 passed; zero failed or pending |
| Native Python suite | 91 passed; zero failed or skipped |
| TypeScript / Vite production build | Passed |
| Reference generator check and Ruff | Passed |
| Author's actual Chrome receiving | Seven of seven groups passed |
| Independent actual Chrome receiving | Six of six scenario groups and the additional pending-verification control passed |
| Current source after receiving | All 136 files unchanged |

The author browser receiving uses the actual built app, actual downloaded JSON bytes and a real file chooser. It includes two CPython planner → approval → readback cycles, a fresh trace after import, preservation on cancel/error, delayed file reads and context changes, inherited raw-world/editor controls, and keyboard operation at a 390-pixel viewport. Final desktop and phone screenshots are byte-identical to the visually inspected preceding composition; the comparison and SHA256s are recorded. No uncaught application error or external application request occurred.

The current native runtime is Node 26.3.0, Chrome 154.0.8037.98 and Puppeteer 25.12.0. Python regression and Vitest producer/consumer subprocesses used Python 3.12.8 with pytest 8.4.2; the hosted workflow separately pins pytest 8.3.5. Ruff is 0.16.10. The unchanged lockfile supplies TypeScript 5.7.3, Vite 8.3.3, Vitest 4.1.11 and Pyodide 0.27.7. Runtime and command receipts record these distinctions rather than implying a hosted CI result.

## Independent finding and receiving history

Independent review of initial tree `9d4d1320fcd59b7a635adb6439ca512650e2df71` found that importing a new scenario cleared the actual audit events but left the old four-event audit-verification text visible. The successor adds one line in loadSavedScenario to clear that display. The original source, original failing review and corrected receiving controls remain preserved. No planner, native gate, audit algorithm or approval format was changed for this finding.

A second independent control held the completion of one real WebCrypto digest from Verify chain across an explicit scenario apply. The verifier finished the discarded four-event trace and repainted a new zero-event verdict. The final successor captures the AuditLog identity, its event-array identity and count in the click handler and only publishes a result if all are unchanged. Genuine hashes and the audit algorithm remain intact; the change prevents an obsolete completion from being attributed to replacement state. The unchanged pending-verification control fails on both the verdict-only successor and its first current-main composition. On final tree d6b4a1ec, all four real old-trace hashes finish while the replacement verdict remains blank. The independent six scenario groups also pass on that exact final source. These paired receipts, source manifests and unchanged counterexample are retained in the independent packet.

The reviewer also investigated stale/future clocks using the actual Python entry points. Its first oracle incorrectly expected planning itself to reject freshness errors. The corrected unchanged-source probe confirmed that ControlRoom.apply performs that admission check: stale and future states are refused without a state transition, while the fresh control applies. This was a receiving-oracle correction; freshness handling required no source change.

The independent receiver also encountered the same rejected CONNECT socket reset before completing any group on its first verdict-successor replay. It preserved that failed process and added a socket error listener in a separately versioned receiver, leaving all six predicates unchanged.

The author's original receiving configurations and their failures are also retained. Puppeteer interception stalled Pyodide on both baseline and candidate; passive observation plus a denying loopback proxy allowed the actual native planner to run. A subsequent source-collector failure occurred only after all seven product groups passed because it treated an untracked dependency symlink as a file. The collector was restricted to the Git index. Finally, the first verdict-successor replay encountered a reset on the receiver's rejected CONNECT socket; a separately versioned receiver now records that socket error. Product predicates and product source did not change for these receiving fixes.

## Reproduction

Use an authorized fresh checkout at the current parent and apply current/candidate.patch from this packet:

```sh
git checkout 09b96e31d2867af5b7a9738406d0431cf1010090
git apply --index /absolute/path/to/this/packet/current/candidate.patch
git write-tree
```

The tree must equal `d6b4a1ec5757144f848e1d6ce851a766a7413f2c`. The complete 136-file current/source-manifest.json provides SHA256, Git blob, byte count and mode for every path. Evidence files are an additional publication delta and are outside that qualified core tree.

```sh
python -m pytest -q
ruff check --no-cache .
python tools/generate_airspace_reference.py --check
cd web/airspace
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run build
```

The reference run reused an exact-lock dependency installation originally produced by npm ci --offline; it did not publish node_modules or modify the lockfile. Set TOWEROPS_PYTHON when the native producer/consumer tests should use a particular Python executable. For actual browser replay, use a separate Puppeteer 25.12.0 installation and a new output directory:

```sh
NODE_PATH=/absolute/path/to/receiving/node_modules \
CHROME_PATH=/absolute/path/to/chrome \
node /absolute/path/to/this/packet/current/scenario-browser-receiving.mjs \
  /absolute/path/to/current-source /absolute/path/to/new-browser-output
```

The receiver serves the existing production build from a loopback listener, uses its own disposable browser profile and a separate proxy that refuses nonlocal background traffic, regenerates authored input fixtures, and closes its own processes. It does not exercise a live traffic feed, real operator, provider, production profile, installed estate rollout or user adoption. Background proxy refusals are recorded separately from application requests.

Current files, final screenshots and actual downloads are under current/. The complete original 27-file author evidence packet is retained under history/initial/. The verdict-only successor and receiving socket failure are under history/verdict-revision/. The first current-main composition and its exact receiving receipts are under history/current-before-completion/. The [independent review](independent-review/REVIEW.md) preserves its own scripts, original failures, run commands and final exact-source results. Captured dependency trees, generated bundles, Git object databases, browser profiles and bulk regenerated fixtures are excluded.
