#!/usr/bin/env python3
"""Zero-dependency loopback-only explorer and deterministic scenario CLI."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from typing import cast
from scenarios import DISCLAIMER, SCENARIOS, replay_result, run_scenario

ROOT = Path(__file__).resolve().parent
MAX_BODY = 262144


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def local_request(self):
        host = self.headers.get("Host", "")
        port = cast(ThreadingHTTPServer, self.server).server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        if host not in allowed or (origin is not None and origin != "http://" + host):
            self.respond(403, {"error": "Loopback same-origin requests only"})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        route = urlsplit(self.path).path
        if route == "/api/scenarios":
            self.respond(200, {"disclaimer": DISCLAIMER, "scenarios": [
                {"id": key, "label": label, "description": description}
                for key, (label, description) in SCENARIOS.items()]})
        elif route in {"/", "/app.js", "/style.css"}:
            name, mime = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                          "/style.css": ("style.css", "text/css")}[route]
            self.respond(200, (ROOT / "web" / name).read_bytes(), mime + "; charset=utf-8")
        else:
            self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if not self.local_request():
            return
        if self.path not in {"/api/run", "/api/replay"}:
            self.respond(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= MAX_BODY:
                self.respond(413, {"error": "Body must be between 1 and 262144 bytes"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.respond(415, {"error": "Use application/json"})
                return
            def reject_constant(value):
                raise ValueError("Non-finite JSON is not supported")
            value = json.loads(self.rfile.read(length), parse_constant=reject_constant)
            if self.path == "/api/replay":
                result = replay_result(value)
            else:
                if not isinstance(value, dict) or set(value) != {"scenario", "include_approval", "include_ack"}:
                    raise ValueError("Provide scenario and both fixture switches")
                if not isinstance(value["scenario"], str):
                    raise ValueError("Scenario must be a string")
                result = run_scenario(**value)
            self.respond(200, result)
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            self.respond(400, {"error": str(exc)[:200]})


def main():
    parser = argparse.ArgumentParser(description=DISCLAIMER)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Loopback-only browser UI")
    serve.add_argument("--port", type=int, default=8765)
    run = commands.add_parser("run", help="Export a fixed synthetic case as JSON")
    run.add_argument("scenario", choices=SCENARIOS)
    run.add_argument("--without-approval", action="store_true")
    run.add_argument("--without-ack", action="store_true")
    replay = commands.add_parser("replay", help="Recompute and compare a local JSON export")
    replay.add_argument("file", type=Path)
    args = parser.parse_args()
    if args.command == "serve":
        with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
            print(f"Synthetic explorer: http://127.0.0.1:{server.server_port}\n{DISCLAIMER}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    elif args.command == "run":
        print(json.dumps(run_scenario(args.scenario, not args.without_approval, not args.without_ack), indent=2))
    else:
        try:
            if args.file.stat().st_size > MAX_BODY:
                raise ValueError("Export exceeds 262144 bytes")
            result = replay_result(json.loads(args.file.read_text()))
        except (ValueError, TypeError) as exc:
            parser.exit(2, str(exc) + "\n")
        print(json.dumps(result, indent=2))
        if not result["matches"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
