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
