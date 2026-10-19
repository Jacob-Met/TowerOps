"""Optional, source-pinned Chromium receiving for TowerOps offline proximity UI.

Run from a full checkout: python3 tools/verify_proximity_browser.py
Requires Playwright Python and installed Chromium. Never talks to a real airspace
system and emits a simple review receipt to stdout; writes no files.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# This file lives inside tools/ in the real checkout, while the initial source
# bundle keeps it alongside the other local files until repository publication.
if not (ROOT / "proximity_html.py").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from proximity_html import render_html
from proximity_report import report_proximity


def _flight(id_: str, x: float, y: float, alt: float, vx: float, vy: float):
    return {"aircraft_id": id_, "x_nm": x, "y_nm": y, "altitude_ft": alt,
            "vx_nm_min": vx, "vy_nm_min": vy, "climb_ft_min": 0}


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("error: Playwright Python not installed; cannot claim browser receiving", file=sys.stderr)
        return 2
    raw = (json.dumps({"version": 12, "observed_at": 1000,
                       "aircraft": [
                           _flight("A1", -5, 0, 10000, 1, 0),
                           _flight("B2", 5, 0, 10000, -1, 0),
                           _flight("C3", 5, 7, 10000, -1, 0),
                           _flight("D4", -10, -10, 14000, 1, 1),
                       ]}, separators=(",", ":")) + "\n").encode()
    report = report_proximity(raw, limit=6)
    assert report["total_pair_count"] == 6 and report["native_conflict_pair_count"] == 1
    requests: list[str] = []
    errors: list[str] = []
    with sync_playwright() as pw:
        executable = shutil.which("chromium") or shutil.which("google-chrome")
        args = ["--no-sandbox"] if sys.platform.startswith("linux") else []
        launch = {"headless": True, "args": args}
        if executable:
            launch["executable_path"] = executable
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1365, "height": 900})
        page.on("request", lambda req: requests.append(req.url))
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        # No file:// or localhost navigation. This works in sandboxes that
        # prohibit URL navigation and additionally proves self-contained UI.
        page.set_content(render_html(report), wait_until="domcontentloaded")
        page.locator("#rows button").first.wait_for()
        assert page.title() == "TowerOps | Proximity Review"
        assert page.locator("#rows tr").count() == 6
        assert page.locator("#conflicts").inner_text() == "1"
        assert page.locator("#total").inner_text() == "6"
        assert page.locator("#selected").inner_text().replace(" ", "") == "A1/B2"
        assert page.locator("#horizontal-bar").evaluate("el => el.parentElement.classList.contains('under')")
        assert page.locator("#vertical-bar").evaluate("el => el.parentElement.classList.contains('under')")
        page.locator("#filter").select_option("conflict")
        assert page.locator("#rows tr").count() == 1
        page.locator("#filter").select_option("clear")
        assert page.locator("#rows tr").count() == 5
        page.locator("#search").fill("D4")
        assert page.locator("#rows tr").count() == 3
        page.locator("#rows button").last.click()
        assert "D4" in page.locator("#selected").inner_text()
        assert not page.locator("#horizontal-bar").evaluate("el => el.parentElement.classList.contains('under')")
        assert not page.locator("#vertical-bar").evaluate("el => el.parentElement.classList.contains('under')")
        page.locator("#order").select_option("time")
        assert page.locator("#rows tr").count() == 3
        page.locator("#search").fill("NO_MATCH")
        assert page.locator("#rows tr").count() == 0
        assert page.locator("#empty").is_visible()
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("request", lambda req: requests.append(req.url))
        mobile.on("pageerror", lambda exc: errors.append(str(exc)))
        mobile.set_content(render_html(report), wait_until="domcontentloaded")
        mobile.locator("#rows button").first.wait_for()
        assert mobile.locator("#rows tr").count() == 6
        assert mobile.evaluate("document.documentElement.scrollWidth") <= 390
        browser.close()
    assert not errors, f"Browser JavaScript errors: {errors}"
    assert not requests, f"Unexpected external request(s): {requests}"
    print(json.dumps({
        "format": "towerops.proximity-browser-receiving.v1",
        "simulation_only": True,
        "world_hash": report["world_hash"],
        "test": "native-report-to-DOM-and-filters",
        "browser": "chromium",
        "viewports_px": [1365, 390],
        "pairs": 6,
        "native_conflict_pairs": 1,
        "browser_errors": len(errors),
        "network_requests": len(requests),
        "result": "passed",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
