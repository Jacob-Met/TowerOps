# TowerOps offline proximity reviewer

This source-only browser review is a companion to the saved-world proximity ranker, not a new aviation safety gate. A synthetic scenario researcher provides a complete native WorldState JSON; the existing `plan_world.parse_world` admits it, `SafetyPolicy._pair_conflict` decides native conflict status and `proximity_report.py` computes read-only closest-approach diagnostics. `proximity_html.py` renders those results to **one self-contained HTML document**, with no imports, live aircraft, provider requests or network calls.

```bash
python3 proximity_html.py saved-world.json > proximity-review.html
python3 proximity_html.py saved-world.json --horizon-min 10 --limit 120 > proximity-review.html
python3 proximity_html.py - < saved-world.json > proximity-review.html
```

Open the HTML in a regular web browser. Search by callsign, filter native conflicts vs non-conflicts, sort pairs by closest-time/identity, and select a pair to inspect the separate horizontal and vertical CPA times and separations. The timeline and bars are explicitly **diagnostic**: they are neither safety decisions nor flight guidance. All selectors are local to the page and make no requests.

`--limit` is 1–1770; the main tool default of 20 applies. The report states when saved rows are truncated, while retaining the full native conflict count. Output is created only on stdout; no source file is changed. The `>` redirection is a normal user-selected operation and *can replace an existing HTML file*; choose a new destination filename if preservation matters. Bad input emits no HTML, exits 2 and writes a diagnostic to stderr. For complete native parser/policy inputs and bounds, see `PROXIMITY_REPORT.md`.

## Optional native consumer browser receiving

From a complete TowerOps checkout with the Playwright Python package and a
supported Chromium installation:

```bash
python3 tools/verify_proximity_browser.py
```

The script exercises the *actual native report renderer and browser DOM* on a
held synthetic four-aircraft world, asserting conflict counts, search, sorting,
filtering, pair inspection, both separation-shortfall bars, a 390px mobile
viewport, zero page errors and zero network requests. It writes no files and
emits one machine-readable JSON receipt on success. Playwright is optional and
is not added to the repository's required dependencies. An installed-browser
pass is separate from independent review or operational aviation assurance.

## Local qualification (component-only)

On 2026-10-19 using a local native-compatible fixture for missing `towerops.py`/`plan_world.py` modules, not a fresh remote checkout:

```bash
PYTHONPATH=_native_test_shim:. python -m pytest -q \
  tests/test_proximity_report.py tests/test_proximity_properties.py tests/test_proximity_html.py
# 17 passed
```

In headless Chromium, `page.set_content()` rendered the resulting stand-alone HTML. It showed the correct 6 pair rows and 1 native-conflict label, filtered 1 conflict/5 other pairs, searched, selected a different pair, switched sorting, displayed an empty-filter state, and passed a 390 px mobile layout check. No page errors or network requests were observed. Browser file navigation and loopback HTTP navigation were blocked by the *container's browser policy*; this is not evidence the HTML can be opened from `file://` on every real machine. The preview and screenshot are included as review artifacts in the bundle. No mainline or production receiving has occurred.

**Status:** source published for review in GitHub PR #148; not independently native-qualified or merged. The standalone HTML sample and screenshots are provided in the conversation artifact. No runtime safety assurance or operational aviation claim is made.
