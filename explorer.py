#!/usr/bin/env python3
"""Zero-dependency loopback-only explorer and deterministic scenario CLI."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from scenarios import DISCLAIMER, SCENARIOS, replay_result, run_scenario

ROOT = Path(__file__).resolve().parent
MAX_BODY = 262144
BODY_READ_TIMEOUT = 5.0


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
        if self.path not in {"/api/run", "/api/replay", "/api/replay/explain"}:
            self.respond(404, {"error": "Not found"})
            return
        try:
            if self.headers.get_all("Transfer-Encoding") is not None:
                self.respond(400, {"error": "Transfer-Encoding is not supported; use Content-Length"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if not lengths:
                self.respond(411, {"error": "Content-Length is required"})
                return
            if len(lengths) != 1:
                self.respond(400, {"error": "Provide exactly one Content-Length"})
                return
            length_text = lengths[0].strip(" \t")
            if not length_text.isascii() or not length_text.isdecimal():
                self.respond(400, {"error": "Content-Length must contain ASCII decimal digits"})
                return
            # Compare decimal text before conversion, including arbitrarily
            # many leading zeroes, without Python's integer-string limit.
            length_text = length_text.lstrip("0") or "0"
            maximum = str(MAX_BODY)
            if (length_text == "0" or len(length_text) > len(maximum)
                    or (len(length_text) == len(maximum) and length_text > maximum)):
                self.respond(413, {"error": "Body must be between 1 and 262144 bytes"})
                return
            length = int(length_text)
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.respond(415, {"error": "Use application/json"})
                return
            previous_timeout = self.connection.gettimeout()
            self.connection.settimeout(BODY_READ_TIMEOUT)
            try:
                raw = self.rfile.read(length)
            except TimeoutError:
                self.respond(408, {"error": "Timed out waiting for the complete request body"})
                return
            finally:
                self.connection.settimeout(previous_timeout)
            if len(raw) != length:
                self.respond(400, {"error": "Request body is shorter than Content-Length"})
                return
            def reject_constant(value):
                raise ValueError("Non-finite JSON is not supported")
            value = json.loads(raw, parse_constant=reject_constant)
            if self.path == "/api/replay":
                result = replay_result(value)
            elif self.path == "/api/replay/explain":
                from replay_explain import explain_replay
                result = explain_replay(value)
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
    replay.add_argument("--explain", action="store_true",
                        help="Report up to 32 literal differing JSON paths")
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
        if args.explain:
            from replay_explain import run_explanation
            raise SystemExit(run_explanation(args.file, MAX_BODY))
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
