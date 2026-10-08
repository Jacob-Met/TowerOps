"""Exercise the encounter explorer and real Python gate in an installed browser.

Run after npm run build. All traffic is explicitly synthetic; the HTTP server is
ephemeral and loopback-only. A new output directory retains source/build pins,
raw browser findings and desktop/phone captures.
"""
import argparse
import hashlib
import json
import math
import mimetypes
import subprocess
import threading
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    dist = ROOT / "web/airspace/dist"
    served = {"/" + str(p.relative_to(dist)): p.read_bytes() for p in dist.rglob("*") if p.is_file()}
    assert "/index.html" in served, "Build Airspace Lab first"
    source_files = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    source_pins = {name: sha((ROOT / name).read_bytes()) for name in source_files}
    build_pins = {name: {"bytes": len(data), "sha256": sha(data)} for name, data in served.items()}
    receipt = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "incomplete",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "source_files": source_pins,
        "build_files": build_pins,
        "cases": [],
        "console_errors": [],
        "page_errors": [],
        "off_origin_requests": [],
        "http_errors": [],
        "served_paths": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            path = "/index.html" if path == "/" else path
            data = served.get(path)
            receipt["served_paths"].append(path)
            if data is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    receipt["origin"] = origin

    def record(name, **evidence):
        receipt["cases"].append({"name": name, "status": "passed", **evidence})

    def attach(page):
        page.on("pageerror", lambda error: receipt["page_errors"].append(str(error)))
        page.on("console", lambda msg: receipt["console_errors"].append(msg.text) if msg.type == "error" else None)
        page.on("response", lambda response: receipt["http_errors"].append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
        page.on("request", lambda request: receipt["off_origin_requests"].append(request.url) if not request.url.startswith(origin + "/") else None)

    def snapshot(page):
        page.locator("#export-world").click()
        return {
            "world": json.loads(page.locator("#world-json").input_value()),
            "clock": page.locator("#sim-clock").inner_text(),
            "proposal": page.locator("#proposal-output").inner_text(),
            "proposal_state": page.locator("#proposal-state").inner_text(),
            "gates": [page.locator(f"#{name} i").inner_text() for name in ("gate-screen", "gate-approval", "gate-ack")],
            "audit": page.locator("#audit-events").inner_text(),
            "audit_status": page.locator("#audit-status").inner_text(),
        }

    def check_values(page, state):
        ids = [page.locator(f"#encounter-{name}").input_value() for name in ("first", "second")]
        a, b = [next(track for track in state["aircraft"] if track["aircraft_id"] == ident) for ident in ids]
        minutes = float(page.locator("#encounter-time").input_value()) / 60
        horizontal = math.hypot(a["x_nm"] - b["x_nm"] + (a["vx_nm_min"] - b["vx_nm_min"]) * minutes,
                                a["y_nm"] - b["y_nm"] + (a["vy_nm_min"] - b["vy_nm_min"]) * minutes)
        vertical = abs(a["altitude_ft"] - b["altitude_ft"] + (a["climb_ft_min"] - b["climb_ft_min"]) * minutes)
        actual_h = float(page.locator("#encounter-horizontal-value").inner_text().split()[0])
        actual_v = float(page.locator("#encounter-vertical-value").inner_text().split()[0])
        assert math.isclose(actual_h, horizontal, abs_tol=0.0051)
        assert math.isclose(actual_v, vertical, abs_tol=0.0501)
        return {"pair": ids, "minutes": minutes, "horizontal_nm": horizontal, "vertical_ft": vertical}

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=args.chrome, headless=True)
            receipt["browser"] = browser.version
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            attach(page)
            page.goto(origin + "/", wait_until="networkidle")
            page.locator("details.state-workbench > summary").click()
            page.locator("details.telemetry-wrap > summary").click()
            page.locator("#encounter-explorer > summary").click()
            before = snapshot(page)
            assert page.get_by_role("combobox", name="FIRST FLIGHT", exact=True).count() == 1
            assert page.get_by_role("combobox", name="SECOND FLIGHT", exact=True).count() == 1
            page.locator("#encounter-midpoint").click()
            values = check_values(page, before["world"])
            assert page.locator("#encounter-verdict").inner_text() == "Below both minimum separations at this time."
            page.locator("#encounter-time").focus()
            previous = page.locator("#encounter-time").input_value()
            page.locator("#encounter-time").press("ArrowRight")
            assert page.locator("#encounter-time").input_value() != previous
            assert snapshot(page) == before
            record("forecast values, keyboard cursor and complete visible-state nonmutation", **values)

            page.locator("#run-planner").click()
            page.wait_for_function("document.querySelector('#proposal-state').textContent === 'PROPOSAL READY'", timeout=90000)
            page.locator("#approve").click()
            approved = snapshot(page)
            page.locator("#encounter-closest").click()
            page.locator("#encounter-now").click()
            page.locator("#encounter-midpoint").click()
            assert snapshot(page) == approved
            page.locator("#encounter-explorer").screenshot(path=str(args.out / "encounter-desktop.png"))
            record("pending real Python advisory and approval preserved while exploring", proposal=approved["proposal"], gates=approved["gates"])
            page.locator("#readback").click()
            page.wait_for_function("document.querySelector('#world-title').textContent.includes('No projected conflict')", timeout=90000)
            assert page.locator("#gate-ack i").inner_text() == "ACCEPTED"
            page.wait_for_function("document.querySelector('#audit-status').textContent.includes('VALID')", timeout=10000)
            assert "VALID" in page.locator("#audit-status").inner_text()
            assert page.locator("#encounter-midpoint").is_disabled()
            assert page.locator("#encounter-overlap-window").inner_text() == "None in this window"
            record("real Python readback applies and forecast refreshes", world=snapshot(page)["world"])

            page.locator("#reset-world").click()
            page.locator("#encounter-time").focus()
            page.locator("#encounter-time").press("End")
            assert float(page.locator("#encounter-time").input_value()) == 300
            page.locator("details.control-card > summary").click()
            page.locator("details.policy-editor > summary").click()
            page.locator("#policy-horizon").evaluate("(e) => {e.value='2';e.dispatchEvent(new Event('input',{bubbles:true}));}")
            assert float(page.locator("#encounter-time").input_value()) == 120
            assert page.locator("#encounter-time").get_attribute("max") == "120"
            record("reduced look-ahead clamps the read-only cursor")
            page.locator("#policy-horizon").evaluate("(e) => {e.value='10';e.dispatchEvent(new Event('input',{bubbles:true}));}")
            endpoint_labels = []
            for chart in ("horizontal", "vertical"):
                label = page.locator(f"#encounter-{chart}-chart text.encounter-axis").last
                bounds = label.evaluate("(e) => {const b=e.getBBox();return {text:e.textContent,x:b.x,width:b.width};}")
                assert bounds["text"] == "10.0"
                assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 320
                endpoint_labels.append({"chart": chart, **bounds})
            page.locator("#encounter-explorer").screenshot(path=str(args.out / "encounter-ten-minute.png"))
            record("ten-minute endpoint labels stay within both chart viewports", labels=endpoint_labels)

            page.locator("#reset-world").click()
            original = snapshot(page)
            page.locator("#edit-selected-track").click()
            new_x = str(float(page.locator("#flight-x").input_value()) + 0.5)
            page.locator("#flight-x").fill(new_x)
            page.locator("#preview-track-edit").click()
            preview = page.locator("#track-edit-preview").inner_text()
            page.locator("#encounter-midpoint").click()
            assert page.locator("#flight-x").input_value() == new_x
            assert page.locator("#track-edit-preview").inner_text() == preview
            page.locator("#cancel-track-edit").click()
            assert snapshot(page) == original
            record("selected-flight draft and preview survive forecast interaction")

            custom = {
                "version": 23, "observed_at": 300,
                "aircraft": [
                    {"aircraft_id": "ALPHA", "x_nm": 0, "y_nm": 0, "altitude_ft": 10000, "vx_nm_min": 1, "vy_nm_min": 0, "climb_ft_min": 0},
                    {"aircraft_id": "BRAVO", "x_nm": 10, "y_nm": 0, "altitude_ft": 10000, "vx_nm_min": -1, "vy_nm_min": 0, "climb_ft_min": 0},
                    {"aircraft_id": "CHARLIE", "x_nm": 0, "y_nm": 50, "altitude_ft": 10000, "vx_nm_min": 1, "vy_nm_min": 0, "climb_ft_min": 0},
                ],
            }
            page.locator("#world-json").fill(json.dumps(custom))
            page.locator("#load-world").click()
            assert page.locator("#encounter-first").input_value() == "ALPHA"
            page.locator("#encounter-second").select_option("BRAVO")
            page.locator("#encounter-midpoint").click()
            check_values(page, custom)
            page.locator("#encounter-second").select_option("CHARLIE")
            assert page.locator("#encounter-midpoint").is_disabled()
            check_values(page, custom)
            assert snapshot(page)["world"] == custom
            record("imported three-flight world and independent pair selection")
            page.locator("#policy-horizontal").evaluate("(e) => {e.value='3';e.dispatchEvent(new Event('input',{bubbles:true}));}")
            common_motion_readings = []
            for mode in ("horizontal", "vertical", "vertical boundary"):
                vertical_case = mode != "horizontal"
                altitude = 1e16 if mode == "vertical boundary" else 1e19
                vertical_gap = 500 if mode == "vertical boundary" else 2048
                minimum = 500 if mode == "vertical boundary" else 1000
                page.locator("#policy-vertical").evaluate("(e, value) => {e.value=String(value);e.dispatchEvent(new Event('input',{bubbles:true}));}", minimum)
                large = {
                    "version": 51, "observed_at": 400,
                    "aircraft": [
                        {"aircraft_id": "COMMON1", "x_nm": 1e16 if mode == "horizontal" else 0, "y_nm": 0,
                         "altitude_ft": altitude if vertical_case else 10000,
                         "vx_nm_min": 1e16 if mode == "horizontal" else 0, "vy_nm_min": 0,
                         "climb_ft_min": altitude if vertical_case else 0},
                        {"aircraft_id": "COMMON2", "x_nm": 1e16 + 4 if mode == "horizontal" else 0, "y_nm": 0,
                         "altitude_ft": altitude + vertical_gap if vertical_case else 10000,
                         "vx_nm_min": 1e16 if mode == "horizontal" else 0, "vy_nm_min": 0,
                         "climb_ft_min": altitude if vertical_case else 0},
                    ],
                }
                page.locator("#world-json").fill(json.dumps(large))
                page.locator("#load-world").click()
                source_before = snapshot(page)
                page.locator("#encounter-time").evaluate("(e) => {e.value='180';e.dispatchEvent(new Event('input',{bubbles:true}));}")
                assert page.locator("#encounter-horizontal-value").inner_text() == ("4.00 NM" if mode == "horizontal" else "0.00 NM")
                assert page.locator("#encounter-vertical-value").inner_text() == (f"{vertical_gap:.1f} FT" if vertical_case else "0.0 FT")
                assert page.locator("#encounter-overlap-window").inner_text() == "None in this window"
                assert page.locator("#encounter-verdict").inner_text() == "At least one separation is at or above its minimum."
                assert page.locator("#encounter-midpoint").is_disabled()
                assert snapshot(page) == source_before
                common_motion_readings.append({"mode": mode, **check_values(page, large)})
            record("large shared horizontal/vertical motion preserves constant pair separation", readings=common_motion_readings)
            custom["aircraft"] = custom["aircraft"][:1]
            page.locator("#world-json").fill(json.dumps(custom))
            page.locator("#load-world").click()
            assert page.locator("#encounter-content").is_hidden()
            assert page.locator("#encounter-message").inner_text() == "Add a second flight to compare an encounter."
            assert page.locator("#encounter-time").is_disabled()
            page.locator("#reset-world").click()
            assert page.locator("#encounter-content").is_visible()
            page.locator("#toggle-run").click()
            assert page.locator("#encounter-content").is_hidden()
            assert page.locator("#encounter-message").inner_text() == "Pause traffic to explore a stable forecast."
            page.locator("#toggle-run").click()
            assert page.locator("#encounter-content").is_visible()
            record("one-flight and running worlds hide stale forecasts; reset and pause restore them")

            phone = browser.new_context(viewport={"width": 320, "height": 568}, is_mobile=True, has_touch=True, device_scale_factor=1)
            mobile = phone.new_page()
            attach(mobile)
            mobile.goto(origin + "/", wait_until="networkidle")
            mobile.locator("#encounter-explorer > summary").tap()
            mobile.locator("#encounter-midpoint").tap()
            assert mobile.locator("#encounter-verdict").inner_text() == "Below both minimum separations at this time."
            bounds = mobile.locator("#encounter-time").bounding_box()
            assert bounds and bounds["width"] > 200
            mobile.locator("#encounter-time").tap(position={"x": bounds["width"] * 0.75, "y": bounds["height"] / 2})
            assert float(mobile.locator("#encounter-time").input_value()) > 0
            assert not mobile.evaluate("document.documentElement.scrollWidth > innerWidth")
            assert mobile.locator("#encounter-horizontal-chart").is_visible()
            assert mobile.locator("#encounter-vertical-chart").is_visible()
            mobile.locator("#encounter-explorer").screenshot(path=str(args.out / "encounter-mobile.png"))
            record("320x568 touch exploration and responsive charts", cursor=mobile.locator("#encounter-time").input_value())
            phone.close()
            context.close()
            browser.close()

        assert not receipt["page_errors"], receipt["page_errors"]
        assert not receipt["console_errors"], receipt["console_errors"]
        assert not receipt["http_errors"], receipt["http_errors"]
        assert not receipt["off_origin_requests"], receipt["off_origin_requests"]
        assert source_pins == {name: sha((ROOT / name).read_bytes()) for name in source_files}
        assert build_pins == {"/" + str(p.relative_to(dist)): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in dist.rglob("*") if p.is_file()}
        receipt["status"] = "passed"
    except BaseException:
        receipt["failure"] = traceback.format_exc()
        raise
    finally:
        server.shutdown()
        server.server_close()
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        receipt["served_paths"] = sorted(set(receipt["served_paths"]))
        (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"status": receipt["status"], "cases": receipt["cases"], "failure": receipt.get("failure"), "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
