"""Optional real Chromium acceptance (pip install playwright; playwright install chromium)."""
import json
import os
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from explorer import Handler, ThreadingHTTPServer
from scenarios import SCENARIOS


def main():
    scratch = os.environ.get("TMPDIR", str(Path(__file__).parent / ".browser-scratch"))
    Path(scratch).mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = scratch
    tempfile.tempdir = scratch
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    reports = []
    try:
        with tempfile.TemporaryDirectory(prefix="towerops-browser-") as directory, sync_playwright() as p:
            browser = p.chromium.launch()
            for width, height in ((1280, 900), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height}, accept_downloads=True)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.wait_for_function("() => document.querySelector('#scenario').options.length === 8")
                assert not page.locator("#export").is_enabled()
                for case in SCENARIOS:
                    page.select_option("#scenario", case)
                    with page.expect_response("**/api/run") as response:
                        page.click("#run")
                    data = response.value.json()
                    page.wait_for_function("() => document.querySelector('#status').textContent.startsWith('Result:')")
                    assert page.locator("#result").is_visible()
                    assert page.locator("#timeline li").count() == len(data["audit_events"])
                    if case == "approved":
                        assert "Fixture accepted" in page.locator("#outcome").inner_text()
                    else:
                        assert "Rejected" in page.locator("#outcome").inner_text()
                        assert data["rejection_reason"] in page.locator("#reason").inner_text()
                    page.locator("#minute").fill("5")
                    page.locator("#minute").dispatch_event("input")
                    assert page.locator("#minute-label").inner_text() == "5.0 min", page.locator("#minute-label").inner_text()
                    assert page.locator("#before circle").count() == 2
                    assert page.locator("#after circle").count() == 2
                    before_lines = page.locator("#before line").evaluate_all("nodes => nodes.map(n => n.outerHTML)")
                    after_lines = page.locator("#after line").evaluate_all("nodes => nodes.map(n => n.outerHTML)")
                    assert (before_lines == after_lines) == (case != "approved")
                    with page.expect_download() as download:
                        page.click("#export")
                    path = Path(directory) / f"{width}-{case}.json"
                    download.value.save_as(path)
                    exported = json.loads(path.read_text())
                    assert exported == data
                    assert download.value.suggested_filename == f"towerops-{case}.json"
                    page.set_input_files("#replay-file", str(path))
                    page.wait_for_function("() => document.querySelector('#replay-status').textContent.startsWith('Replay MATCH:')")
                    exported["after"]["version"] += 1
                    tampered = Path(directory) / f"tampered-{width}-{case}.json"
                    tampered.write_text(json.dumps(exported))
                    page.set_input_files("#replay-file", str(tampered))
                    page.wait_for_function("() => document.querySelector('#replay-status').textContent.startsWith('Replay MISMATCH:')")
                    reports.append({"viewport": [width,height], "scenario": case, "outcome": data["outcome"], "export_replay": "match", "tampered_replay": "mismatch"})
                # GPT acceptance contribution: no reload from success to missing-ack.
                page.select_option("#scenario", "approved")
                with page.expect_response("**/api/run") as response:
                    page.click("#run")
                accepted = response.value.json()
                page.wait_for_function("() => document.querySelector('#outcome').textContent.includes('Fixture accepted')")
                assert accepted["after_conflict"] is False
                page.select_option("#scenario", "missing_ack")
                with page.expect_response("**/api/run") as response:
                    page.click("#run")
                rejected = response.value.json()
                page.wait_for_function("() => document.querySelector('#reason').textContent.includes('ack_missing')")
                assert rejected["after"] == rejected["before"]
                assert rejected["after"]["version"] == 1
                assert rejected["after"] != accepted["after"]
                assert "simulated_actuation" not in page.locator("#timeline").inner_text()
                assert page.locator("#before line").evaluate_all("nodes => nodes.map(n => n.outerHTML)") == page.locator("#after line").evaluate_all("nodes => nodes.map(n => n.outerHTML)")
                with page.expect_download() as download:
                    page.click("#export")
                regression = Path(directory) / f"gpt-missing-ack-{width}.json"
                download.value.save_as(regression)
                assert json.loads(regression.read_text()) == rejected
                page.set_input_files("#replay-file", str(regression))
                page.wait_for_function("() => document.querySelector('#replay-status').textContent.startsWith('Replay MATCH:')")
                page.select_option("#scenario", "approved")
                page.uncheck("#approval")
                with page.expect_response("**/api/run") as response:
                    page.click("#run")
                assert response.value.json()["rejection_reason"] == "human_approval_required"
                page.wait_for_function("() => document.querySelector('#reason').textContent.includes('human_approval_required')")
                page.check("#approval")
                page.uncheck("#ack")
                with page.expect_response("**/api/run") as response:
                    page.click("#run")
                assert response.value.json()["rejection_reason"] == "ack_missing"
                page.wait_for_function("() => document.querySelector('#reason').textContent.includes('ack_missing')")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                # Screenshot is optional evidence, saved only if local evidence directory exists.
                evidence = Path(__file__).parent / "evidence"
                if evidence.exists():
                    page.screenshot(path=str(evidence / f"browser-{width}.png"), full_page=True)
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    print(json.dumps({"browser": "Chromium", "cases": reports, "fixture_controls": "passed on both viewports", "overflow": "none", "page_errors": []}, indent=2))


if __name__ == "__main__":
    main()
