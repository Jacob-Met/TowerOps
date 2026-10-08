"""Check native alternatives in a locally built Airspace Lab with Playwright.

All traffic is synthetic and served on loopback. Worker observation preserves
real messages. Only the explicit helper-download failure control substitutes a
network response. Requires the optional runtime used by capture_airspace.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OBSERVE_WORKER = """
window.__towerIO = {requests: [], responses: []};
const OriginalWorker = window.Worker;
window.Worker = class extends OriginalWorker {
  constructor(...args) {
    super(...args);
    this.addEventListener('message', event => window.__towerIO.responses.push(structuredClone(event.data)));
  }
  postMessage(message, ...args) {
    window.__towerIO.requests.push(structuredClone(message));
    return super.postMessage(message, ...args);
  }
};
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def last_exchange(page, operation):
    io = page.evaluate("window.__towerIO")
    request = next(item for item in reversed(io["requests"]) if item["request"]["op"] == operation)
    response = next(item for item in reversed(io["responses"]) if item["id"] == request["id"])
    return request["request"], response


def check(browser, origin, output):
    errors, external = [], []

    def local_only(route):
        if route.request.url.startswith(origin):
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort()

    def open_page(width=1440, height=1000, *, observe=False, fail_helper=False):
        context = browser.new_context(viewport={"width": width, "height": height})
        context.route("**/*", local_only)
        if observe:
            context.add_init_script(OBSERVE_WORKER)
        if fail_helper:
            context.route("**/python/advisory_options.py", lambda route: route.fulfill(status=503, body="authored helper-download failure"))
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin, wait_until="networkidle")
        return context, page

    context, page = open_page(observe=True)
    expect(page.locator("#pair-count")).to_have_text("1")
    expect(page.locator("#audit-status")).to_have_text("0 EVENTS / VALID")
    page.locator("#run-planner").click()
    expect(page.locator("#proposal-state")).to_have_text("PROPOSAL READY", timeout=90000)
    _, original_plan = last_exchange(page, "plan")
    page.locator("#approve").click()
    expect(page.locator("#readback")).to_be_enabled()
    before_world = page.locator("#world-json").input_value()
    page.locator("#review-options").click()
    expect(page.locator("#advisory-options-count")).to_contain_text("ADMITTED", timeout=90000)
    options_request, options_response = last_exchange(page, "options")
    options = options_response["result"]["advisories"]
    assert len(options) > 6
    assert options[0] == original_plan["result"]["advisory"]
    assert page.locator("#world-json").input_value() == before_world
    expect(page.locator("#audit-status")).to_have_text("0 EVENTS / VALID")
    expect(page.locator("#gate-approval i")).to_have_text("APPROVED")
    expect(page.locator("#readback")).to_be_enabled()
    current = page.locator(f'button[data-advisory-hash="{options[0]["advisory_hash"]}"]')
    expect(current).to_be_disabled()
    expect(current).to_have_text("Current proposal")
    assert page.locator("#advisory-options-list > li").count() == 6
    page.locator("#advisory-options-next").click()
    expect(page.locator("#advisory-options-page")).to_have_text(f"Showing 7–12 of {len(options)}")
    page.locator("#advisory-flight-filter").select_option("TWR218")
    displayed = page.locator("#advisory-options-list h3").all_text_contents()
    assert displayed and all("TWR218" in text for text in displayed), displayed
    expect(page.locator("#readback")).to_be_enabled()
    page.locator("#advisory-flight-filter").select_option("")

    selected = options[1]
    row = page.locator(f'li[data-advisory-hash="{selected["advisory_hash"]}"]')
    assert json.loads(row.locator("pre").text_content()) == selected
    row.locator("button").click()
    expect(page.locator("#approve")).to_be_enabled()
    expect(page.locator("#readback")).to_be_disabled()
    expect(page.locator("#gate-approval i")).to_have_text("WAIT")
    expect(page.locator("#gate-ack i")).to_have_text("WAIT")
    assert page.locator("#world-json").input_value() == before_world
    expect(page.locator("#audit-status")).to_have_text("0 EVENTS / VALID")
    page.locator("#advisory-review").screenshot(path=output / "desktop-alternatives.png")
    page.locator("#approve").click()
    page.locator("#readback").click()
    expect(page.locator("#gate-ack i")).to_have_text("ACCEPTED", timeout=90000)
    expect(page.locator("#audit-status")).to_have_text("4 EVENTS / VALID")
    apply_request, apply_response = last_exchange(page, "apply")
    assert apply_request["advisory"] == selected
    assert apply_request["approval"]["advisory_hash"] == selected["advisory_hash"]
    assert apply_request["ack"]["advisory_hash"] == selected["advisory_hash"]
    result = apply_response["result"]
    assert result["valid"] is True and "error" not in result
    target = next(a for a in result["state"]["aircraft"] if a["aircraft_id"] == selected["aircraft_id"])
    assert [target["vx_nm_min"], target["vy_nm_min"], target["climb_ft_min"]] == [
        selected["set_vx_nm_min"], selected["set_vy_nm_min"], selected["set_climb_ft_min"],
    ]
    assert result["events"][-1]["payload"]["advisory_hash"] == selected["advisory_hash"]
    assert result["state"]["version"] == options_request["state"]["version"] + 1
    expect(page.locator("#advisory-options-count")).to_have_text("NO CURRENT REVIEW")
    expect(page.locator("#advisory-options-status")).to_contain_text("changed")
    page.locator("#review-options").click()
    expect(page.locator("#advisory-options-count")).to_have_text("0 ADMITTED / 0 CHECKED", timeout=90000)
    expect(page.locator("#advisory-options-status")).to_contain_text("No projected conflict")
    expect(page.locator("#audit-status")).to_have_text("4 EVENTS / VALID")
    context.close()

    phone, page = open_page(width=390, height=844)
    page.locator("#review-options").click()
    expect(page.locator("#advisory-options-count")).to_contain_text("ADMITTED", timeout=90000)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#advisory-review").screenshot(path=output / "mobile-alternatives.png")
    phone.close()

    unavailable, page = open_page(fail_helper=True)
    page.locator("#review-options").click()
    expect(page.locator("#advisory-options-status")).to_contain_text("source could not load", timeout=90000)
    expect(page.locator("#advisory-options-count")).to_have_text("NO CURRENT REVIEW")
    expect(page.locator("#approve")).to_be_disabled()
    page.locator("#run-planner").click()
    expect(page.locator("#proposal-state")).to_have_text("PROPOSAL READY", timeout=90000)
    expect(page.locator("#proposal-output")).to_contain_text("vy 2.0")
    unavailable.close()
    assert not errors, errors
    assert not external, external
    return {
        "browser": browser.version, "options_request": options_request, "options_response": options_response,
        "selected_advisory": selected, "apply_request": apply_request, "apply_response": apply_response,
        "passed": [
            "original native first-choice identity", "read-only review preserves approval and world",
            "native ordering, paging and flight filter", "selection clears prior authorization",
            "exact selected native body and hash through original apply", "original audit verifies",
            "changed snapshot invalidates options", "conflict-free complete empty review",
            "mobile review fits viewport", "helper-download failure leaves native planner available",
        ],
        "page_errors": errors, "external_requests": external,
        "source_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in ["towerops.py", "advisory_options.py", "web/airspace/src/main.ts",
                         "web/airspace/src/python-worker.ts", "web/airspace/src/advisory-options.ts",
                         "web/airspace/src/advisory-review.ts", "web/airspace/src/python.ts"]
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=ROOT / "web/airspace/dist"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=str(args.chrome), args=["--no-sandbox", "--disable-gpu"])
            try:
                receipt = check(browser, f"http://127.0.0.1:{server.server_port}/", args.output_dir)
                (args.output_dir / "browser-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps({"browser": receipt["browser"], "passed": receipt["passed"]}, indent=2))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
