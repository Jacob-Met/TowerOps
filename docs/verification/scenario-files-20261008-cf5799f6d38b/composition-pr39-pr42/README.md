# Scenario files composed with encounter exploration and decision trails

The current candidate is Git tree **8ac56fee8a2f65503f8cd118c11d4379a521cfcf**, applied over main commit **9a2468f9bbaa25c0ab92cb12f712170420f9e622** (tree **07cb60b0a501ec3ae66f3e5391f54ff11614f849**). Seven scenario feature paths differ from that main: four existing page integration files and three scenario module/test files. All **145 inherited paths outside those seven** remain byte-for-byte identical; the complete candidate has **152 source files**.

This is a supplement to the original scenario-file qualification packet. Its historical failures, independent real-WebCrypto completion test and prior source versions remain unchanged.

## Deliberate composition

| Seam | Result |
| --- | --- |
| README | Preserve the encounter instructions, saved-decision-trail instructions and full scenario-file instructions. |
| HTML | Preserve all three panels and their original controls. Scenario imports retain explicit review and Apply. |
| Main page | Preserve the encounter constructor/update calls and decision-trail host/native-review hooks. Refresh scenario availability alongside the decision-trail busy state in render. On Run/Pause, refresh both scenario availability and the encounter view immediately. |
| CSS | Preserve the complete encounter block, then the complete scenario block. Decision-trail CSS remains its separate unchanged module. |

The scenario module, UI module and scenario unit tests retain their earlier qualified bytes. The scenario loader still restores aircraft, policy, clock, time scale and selected flight together; clears the current native audit, proposal, approval and old chain verdict; pauses traffic; and reaches encounter refresh through the ordinary render function. The prior async chain-verification identity guard is retained.

No changes were made to encounter calculation/view modules, decision-trail modules, planner, gate, original-byte Python audit transport, Worker implementation or deployment workflow. PR42's newly added Worker operation and workflow gates are inherited from main and received with the scenario feature.

## Receiving results

The frozen current source passed **188 frontend tests**, **108 native Python tests**, Ruff, the checked-in Python reference comparison and the production build.

| Browser receiving | Passing groups |
| --- | ---: |
| Existing scenario author controls | 7 |
| Unchanged independent-authored scenario controls | 6 |
| Unchanged held-real-digest completion control | 1 |
| Unchanged encounter owner's maintained controls | 10 |
| New scenario / encounter interactions | 3 |
| Unchanged decision-trail owner's maintained controls | 11 |
| New scenario / decision-trail interactions | 2 |
| Total | **40** |

The current project's native-Python/Worker oracle and capture predicates also passed. All scenarios and audit histories were synthetic. The tests executed the built app and its bundled real Pyodide/CPython Worker; no replacement planner, approval, audit hash or synthetic Worker reply was used.

The new encounter controls verify that review leaves the existing forecast and approved decision intact; Apply replaces unavailable pair identities, recomputes numerical separation and clamps the cursor to the restored horizon; same-callsign changed geometry recomputes the existing chosen pair; singleton scenarios hide unavailable forecasts; and Run/Pause immediately updates both feature panels on a 320px viewport.

The new decision-trail controls verify that current-trace download becomes exactly **[]** after scenario Apply; reopening a named historical trace does not restore it as the live trace or change the current world; and native trace review invalidates a pending scenario import through the shared busy state while preserving a valid live approval and subsequent native readback.

Author-controlled receivers report no unexpected browser errors or external application requests. The maintained trace test intentionally aborts **audit_replay.py** in its missing-source case and verifies recovery without disabling the native planner; that expected failure remains in its raw receipt. The independently authored predicates were replayed unchanged by the composing worker; this is not a claim of a second independent review of this composition.

## Exact historical reconstructions

The three source patches are complete overlays over publicly retrievable Git commits:

| Base commit | Patch | Resulting source tree |
| --- | --- | --- |
| 5ae808749c8624d9e267d23997beaa3ae5220dbc | history/wire/scenario.patch | 9ed528ac4281d4ec098b4717d909a08869057d40 |
| 9d70db6352875c380d64639be2212f1e71de2d12 | history/encounter/scenario.patch | 0bcf1ca084c9cca0a422b76d8443a8b543d6e923 |
| 9a2468f9bbaa25c0ab92cb12f712170420f9e622 | scenario-on-decision-trace.patch | 8ac56fee8a2f65503f8cd118c11d4379a521cfcf |

Check out the chosen base in a new checkout, apply its patch with **git apply --index**, then compare **git write-tree** with the listed result. This reconstructs every historical version of the four shared files, without capturing an entire dependency tree. The included source manifests and final readback cover actual bytes, not only the Git index.

The earlier encounter composition passed 182 frontend / 91 Python tests, 7+6+1 scenario controls, ten maintained encounter controls, three new interaction controls and the native Worker oracle. Its exact receipts and source manifest are retained under **history/encounter/**.

## Replay

The JSON command receipts record the exact native commands, paths and process exits. The native runtime was Node 26.3.0, Chrome 154.0.8037.98, Python 3.12.8, Puppeteer 25.12.0 and Playwright 1.63.0. Exact package/runtime metadata and source/build hashes are in **current/qualification.json** and **current/build-manifest.json**. Install the project's locked frontend packages in the isolated checkout and run its existing test, reference, lint and build commands before browser receiving.

The three existing scenario scripts and two new interaction scripts accept positional **SOURCE_ROOT NEW_OUTPUT_DIRECTORY** arguments. Supply Puppeteer through **NODE_PATH**; set **REVIEW_SOURCE_TREE** to the actual staged source tree for the two independent-authored scripts. Their original default metadata is historical, so this explicit environment value is required.

Run the maintained encounter receiver from the reconstructed repository root:

~~~sh
python tools/verify_encounter_browser.py --chrome /path/to/chrome --out /new/encounter-evidence
~~~

Run the maintained decision-trail receiver from that same root:

~~~sh
node tools/verify_decision_trace.mjs --chrome /path/to/chrome --playwright /path/to/playwright/driver/package/index.mjs --output /new/trace-evidence
~~~

The Python Playwright installation supplies that JavaScript driver. Set **TOWEROPS_PYTHON** to the chosen native Python interpreter for the trace receiver and current frontend native-bridge tests.

**receivers/run-ci-browser-python.py** runs the unchanged current CI oracle with only the installed Chrome executable selected. **receivers/run-ci-capture.py** runs the existing capture predicates with only the output directory redirected outside the frozen source checkout. Both take **SOURCE_ROOT CHROME_PATH**; the capture wrapper also takes **NEW_OUTPUT_DIRECTORY**. Their logs preserve the exact underlying source hash. They do not change the app or backend behavior.

The maintained encounter receipt names **HEAD** and its tree as source metadata, while the worktree contains the staged overlay. Its full per-file source hashes, the separately recorded staged tree and final readback identify the executed candidate correctly. Those raw inherited metadata fields were not rewritten.

This packet proves native receiving of the exact candidate. It does not claim that this source has merged, passed a later hosted CI run or reached the public Pages route. The existing normal main-push workflow owns publication; delivery is received separately after merge.
