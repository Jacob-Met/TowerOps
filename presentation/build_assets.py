"""Regenerate presentation PNG/screenshots from the repo. Needs playwright+chromium (test-only dep).
Usage: python presentation/build_assets.py   (run from repo root)"""
import pathlib
import sys
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright

from explorer import Handler, ThreadingHTTPServer

root = pathlib.Path(__file__).resolve().parent
assets = root / "assets"; assets.mkdir(exist_ok=True)
server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_port}"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 940})
    pg.goto((root / "architecture.svg").as_uri())
    pg.screenshot(path=str(assets / "architecture.png"))
    pg.close()
    for w, h, tag in ((1280, 900, "desktop"), (390, 844, "mobile")):
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto(url)
        pg.wait_for_function("() => document.querySelector('#scenario').options.length === 8")
        for case in ("approved", "missing_ack", "late_ack"):
            pg.select_option("#scenario", case)
            pg.click("#run")
            pg.wait_for_function("() => document.querySelector('#status').textContent.startsWith('Result:')")
            pg.locator("#minute").fill("5"); pg.locator("#minute").dispatch_event("input")
            pg.screenshot(path=str(assets / f"ui-{tag}-{case}.png"), full_page=True)
        pg.close()
    b.close()
server.shutdown()
