# TowerOps local synthetic scenario explorer

Research simulation only; fixture identities are not real authority. No live feeds, model/Strands calls, SDK dependency, real clearances, or aviation safety claim. Existing `towerops.py` is byte-for-byte unchanged from public baseline `e8fa18e`.

## First run

Python 3.12+ and a modern browser; **no pip install is needed for the app**.

```sh
python explorer.py serve --port 8765
```

Open http://127.0.0.1:8765 . Choose **Approval + acknowledgement**, leave the two simulated-fixture boxes checked, and Run. The projected conflict changes true→false after simulated actuation. Scrub projected minutes to compare constant-velocity paths. Gate times are synthetic seconds, separate from projected minutes.

Choose **Missing acknowledgement** and Run without reloading: rejection `ack_missing`, unchanged world, no actuation event. The displayed result and download always represent the last completed run, not an unrun selection. Withholding checkboxes cannot supply missing fixtures or bypass engine gates.

Other fixed cases: missing approval, acknowledgement dated after dispatch cutoff (`ack_late`), stale observation, changed world hash, acknowledgement for wrong advisory, expired proposal. Every refusal retains the exact pre-gate world. Fixed identities are `FIXTURE-A`, `FIXTURE-B`, `FIXTURE-CONTROLLER-NOT-AUTHORITY`.

## Export and replay

Export JSON after a run. Select that file under **Replay exported JSON**: the backend reexecutes its fixed scenario and fixture switches and compares the entire result. It accepts equivalent finite JSON numbers (1001 versus 1001.0), never boolean→number coercion. Change `after.version` in a copy and replay: MISMATCH. Malformed formats/unknown scenarios are rejected. Uploaded files are not saved or used as arbitrary engine input.

The replay status belongs to the currently selected file. Selecting another export retires earlier file reads and replay responses, including their errors; clearing the input clears the status. An already-sent request may still finish, but cannot replace the newer verdict. Replay does not change the displayed scenario result or its JSON export.

Replay is reproducibility under this local engine, not authenticity. The hash chain is not a signature or external custody anchor; someone can construct another valid fixed-fixture export. No replay result grants real authority.

CLI (shell redirection saves real engine output):

```sh
python explorer.py run approved > approved.json
python explorer.py run missing_ack > missing_ack.json
python explorer.py run approved --without-approval
python explorer.py replay approved.json
```

Replay exits 0 for match, 1 for mismatch, 2 for malformed input.

## Tests

Standard-library engine/control + real HTTP suite:

```sh
python -m unittest -v test_explorer
```

It exercises all eight cases × four fixture-switch combinations, exact no-actuation retention, full-export edits, JS numeric roundtrip, real HTTP run/replay, and invalid requests. No fabricated provider outputs.

Focused Explorer replay-selection lifecycle tests (Node.js 20+; built-in modules only):

```sh
node tests/test_explorer_replay_selection.cjs
```

These controlled DOM/fetch tests cover superseded reads, responses, JSON bodies and errors, same-file reselection, clearing, current refusals and explicit recovery. They do not replace actual browser receiving.

Optional actual browser acceptance:

```sh
python -m pip install playwright
python -m playwright install chromium
# Linux images without browser libraries only:
python -m playwright install-deps chromium
python browser_acceptance.py
```

Chromium exercises all eight UI cases at desktop 1280×900 and mobile 390×844, sliders/SVG geometry, downloads, original replay, tampered replay, withheld controls, no horizontal overflow/page errors. Browser dependencies are test-only, not app dependencies. Logs/screenshots live in local `evidence/` when that directory exists.

## HTTP scope

Bound to 127.0.0.1 only. Static routes `/`, `/app.js`, `/style.css`; GET `/api/scenarios`; POST `/api/run` with JSON `{ "scenario": "approved", "include_approval": true, "include_ack": true }`; POST `/api/replay` with a whole exported result. Fixed inputs only, 256KiB body cap, same-origin Host/Origin checks. This is a local development server, not a remotely deployed service. Ctrl+C stops it; no estate services are touched.

## Getting the code

Everything needed is in this repository (standard library only for the app). Either clone the branch, or apply the patch to a clean checkout of baseline `e8fa18e` (`main`):

```sh
git apply towerops-explorer-all.patch   # from a clean clone of main
python -m unittest -q                   # 8 tests
python explorer.py serve --port 8765
```

A transfer zip of the same files (`towerops-explorer.zip`) runs the same way after extraction; compare its SHA-256 with the delivery report if you move it between machines.

## Explain an Explorer replay mismatch

Use the optional detailed report to locate differences in one saved export:

```sh
python3 explorer.py replay approved.json --explain
```

The ordinary reply fields stay present. The report adds `difference_limit: 32`,
`differences` and `differences_truncated`. Each row names an RFC6901 JSON Pointer
(`~0` means a literal tilde and `~1` a literal slash), a missing/unexpected/type/value
kind, and literal expected/actual sides. A side with `present: false` is absent;
`present: true, type: "null", value: null` is an explicit null. Object keys are
visited in sorted order and array indices in increasing order. A type difference
reports that subtree once. Values are complete, not shortened.

For the documented edited `after.version` copy, a row identifies `/after/version`.
Finite numerically equal integers and floats remain equal; booleans do not become
numbers. The first 32 differences are returned. `differences_truncated: true`
means at least one more was found, not a total count. Paths describe differences
from the fixed local reproduction; they do not infer why an export changed or
authenticate it. The existing reproducibility/authority caveats still apply.

Explain mode reads one regular UTF-8 file, bounded to 262,144 bytes at the actual
read. It refuses malformed, excessively deep or nonfinite JSON, including overflow
numbers, before report output. It follows the existing fixture request admission;
it does not accept arbitrary engine input. It neither writes the input nor opens
an output file. Concurrent file writers and adversarial directory changes are not
excluded. Keep the original when redirecting stdout: a shell may truncate its
destination before this command starts.

Exit 0 is a delivered matching report, 1 a delivered mismatch report, and 2 a
refusal or stdout write/flush failure. The complete JSON is prepared first, but
bytes already written cannot be rolled back on output failure. Default replay
without `--explain`, its original decoding and exits, and the browser HTTP reply
remain unchanged.

Focused standard-library tests:

```sh
python3 -m unittest discover -s tests -p 'test_replay_explain.py' -v
```

## Inspect field differences in the browser

After selecting a saved export that reports MISMATCH, choose **Explain this
mismatch**. The existing replay verdict stays visible while a separate field
comparison loads. Expand or collapse **Field differences** to read each JSON
Pointer, difference kind, and complete expected/actual JSON envelope. Expected
is the local synthetic reproduction; actual is the selected saved export.
An envelope with present:false is absent, distinct from a present null.

The browser requests details only after this explicit action. It compares the
parsed value already accepted for that selection, without rereading the file
or replacing the displayed scenario and its export. Values are rendered as
literal text. JSON formatting, original numeric spelling and exact input bytes
are not preserved by the browser's parse/serialize step. The existing numerical
equivalence, 32-difference cap and explicit more-found indication are unchanged.

Selecting another file or clearing the chooser immediately retires old details,
including unfinished comparison responses and errors. A current comparison
failure leaves the replay verdict intact and enables an explicit retry.
A match, invalid input or pending ordinary replay has no old-file explanation
available. This action describes differing fields; it makes no causal inference.

The additive POST /api/replay/explain route admits a complete exported result
through the existing local HTTP boundary and calls the unchanged
replay_explain.explain_replay helper. It returns the same explanation object as
the optional CLI, within the existing HTTP body limit. The ordinary /api/replay
route, fixed scenario model and engine remain unchanged. Nothing is stored.

Focused route and presentation controls:

~~~sh
python3 -B -m unittest discover -s tests -p 'test_explorer_explanation_http.py' -v
node tests/test_explorer_explanation.cjs
~~~

The existing replay-selection control excludes only these newly added replay
widgets from its unrelated-display snapshot. Its original selected-file,
stale-response, refusal and recovery assertions remain intact.
