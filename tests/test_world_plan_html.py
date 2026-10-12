from __future__ import annotations

import base64
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

import plan_world
from world_plan_html import render_plan_html

ROOT = Path(__file__).resolve().parents[1]


def world_bytes(aircraft=None):
    if aircraft is None:
        aircraft = [
            dict(aircraft_id="EAST", x_nm=-8, y_nm=1.0, altitude_ft=12000,
                 vx_nm_min=2, vy_nm_min=-0.0, climb_ft_min=0),
            dict(aircraft_id="WEST", x_nm=8, y_nm=1.0, altitude_ft=12000,
                 vx_nm_min=-2, vy_nm_min=0.0, climb_ft_min=0),
        ]
    return (json.dumps(dict(version=7, observed_at=120.0, aircraft=aircraft),
                       indent=2) + "\n").encode()


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = dict(tag=tag, attrs=dict(attrs), text="", ancestors=list(self.stack))
        self.nodes.append(node)
        if tag not in {"meta", "link", "br", "hr", "input", "img"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data

    def find(self, attr, value, within=None):
        return [n for n in self.nodes if n["attrs"].get(attr) == value
                and (within is None or any(p is within for p in n["ancestors"]))]

    def by_id(self, value):
        rows = self.find("id", value)
        if len(rows) != 1:
            raise AssertionError((value, len(rows)))
        return rows[0]

    def download(self):
        link = self.by_id("download-json")
        prefix = "data:application/json;charset=utf-8;base64,"
        if not link["attrs"]["href"].startswith(prefix):
            raise AssertionError("exact data download missing")
        return base64.b64decode(link["attrs"]["href"][len(prefix):], validate=True)


class WorldPlanHTMLTests(unittest.TestCase):
    def run_cli(self, raw, *args, stdin=False):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "world.json"
            source.write_bytes(raw)
            command = [sys.executable, "-B", str(ROOT / "plan_world.py"),
                       "-" if stdin else str(source), *args]
            result = subprocess.run(command, input=raw if stdin else None,
                                    capture_output=True, check=False, timeout=30)
            self.assertEqual(source.read_bytes(), raw)
            return result

    def test_complete_native_alternatives_and_current_bindings(self):
        raw = world_bytes()
        expected = plan_world.review_world(raw)
        actual = self.run_cli(raw, "--html")
        self.assertEqual(actual.returncode, 0, actual.stderr)
        doc = Document(actual.stdout.decode())
        nodes = doc.find("class", "alternative")
        self.assertGreater(len(nodes), 1)
        self.assertEqual(len(nodes), len(expected["advisories"]))
        current = {row["aircraft_id"]: row for row in expected["world"]["aircraft"]}
        for rank, (node, advisory) in enumerate(zip(nodes, expected["advisories"]), 1):
            self.assertEqual(node["attrs"]["data-rank"], str(rank))
            self.assertEqual(node["attrs"]["data-aircraft-id"], advisory["aircraft_id"])
            for field in ("vx_nm_min", "vy_nm_min", "climb_ft_min"):
                row = doc.find("data-component", field, node)[0]
                self.assertEqual(
                    doc.find("data-value", "current", row)[0]["text"],
                    json.dumps(current[advisory["aircraft_id"]][field]),
                )
                self.assertEqual(doc.find("data-value", "proposed", row)[0]["text"],
                                 json.dumps(advisory["set_" + field]))
            self.assertEqual(json.loads(doc.find("data-field", "advisory_json", node)[0]["text"]),
                             advisory)
        self.assertEqual([n["attrs"]["data-aircraft-id"]
                          for n in doc.find("data-aircraft-id", "EAST")
                          if any(p is doc.by_id("world") for p in n["ancestors"])], ["EAST"])

    def test_download_is_exact_default_json_and_native_writer_bytes(self):
        raw = world_bytes()
        default = self.run_cli(raw)
        optional = self.run_cli(raw, "--html")
        expected = json.dumps(plan_world.review_world(raw), ensure_ascii=False,
                              allow_nan=False, indent=2).encode() + b"\n"
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(optional.returncode, 0, optional.stderr)
        self.assertEqual(default.stdout, expected)
        self.assertIn(b"-0.0", default.stdout)
        self.assertEqual(Document(optional.stdout.decode()).download(), default.stdout)
        self.assertEqual(Document(optional.stdout.decode()).by_id("report-json")["text"].split(
            "\n", 1)[-1][-2:], "}\n")  # Original report remains inspectable.

    def test_complete_policy_provenance_and_stdin(self):
        raw = world_bytes()
        flags = ("--now", "125", "--horizontal-nm", "3", "--vertical-ft", "800",
                 "--horizon-min", "4")
        reference = self.run_cli(raw, *flags)
        candidate = self.run_cli(raw, "--html", *flags, stdin=True)
        self.assertEqual(reference.returncode, 0, reference.stderr)
        self.assertEqual(candidate.returncode, 0, candidate.stderr)
        doc = Document(candidate.stdout.decode())
        self.assertEqual(doc.download(), reference.stdout)
        data = json.loads(reference.stdout)
        for key, value in data["policy"].items():
            self.assertEqual(doc.find("data-policy-field", key)[0]["text"], json.dumps(value))
        summary = doc.by_id("summary")
        for key in ("status", "world_hash", "input_sha256", "candidate_count", "reviewed_at"):
            self.assertEqual(doc.find("data-field", key, summary)[0]["text"], str(data[key]))

    def test_both_empty_outcomes_are_distinct(self):
        worlds = [world_bytes([]), world_bytes([
            dict(aircraft_id=name, x_nm=0, y_nm=0, altitude_ft=12000,
                 vx_nm_min=0, vy_nm_min=0, climb_ft_min=0) for name in ("A", "B")
        ])]
        statuses = []
        for raw in worlds:
            result = self.run_cli(raw, "--html")
            self.assertEqual(result.returncode, 0, result.stderr)
            doc = Document(result.stdout.decode())
            status = json.loads(doc.download())["status"]
            statuses.append(status)
            self.assertEqual(doc.find("class", "alternative"), [])
            self.assertEqual(len(doc.find("id", "empty-alternatives")), 1)
        self.assertEqual(statuses, ["no_conflict", "no_admitted_option"])

    def test_literal_renderer_text_without_active_content(self):
        data = plan_world.review_world(world_bytes())
        attack = '<img src=x onerror="window.BAD=1"> & </script>\n漢字'
        original_id = data["world"]["aircraft"][0]["aircraft_id"]
        data["world"]["aircraft"][0]["aircraft_id"] = attack
        for entry in data["advisories"]:
            if entry["aircraft_id"] == original_id:
                entry["aircraft_id"] = attack
            entry["rationale"] = attack
        # Deliberate presentation-helper fixture; not a native admitted world.
        raw = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        doc = Document(render_plan_html(raw))
        self.assertEqual(doc.download(), raw.encode())
        self.assertFalse(any(n["tag"] in {"script", "img", "iframe", "form", "base"}
                             for n in doc.nodes))
        self.assertFalse(any(k.startswith("on") for n in doc.nodes for k in n["attrs"]))
        self.assertIn(attack, [n["text"] for n in doc.find("data-field", "rationale")])
        self.assertIn(attack, [n["attrs"].get("data-aircraft-id") for n in doc.nodes])

    def test_one_native_review_and_unchanged_return(self):
        raw = world_bytes()
        report = plan_world.review_world(raw)
        reference = copy.deepcopy(report)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "world.json"
            source.write_bytes(raw)
            out = io.StringIO()
            with patch("plan_world.review_world", return_value=report) as review:
                with contextlib.redirect_stdout(out):
                    code = plan_world.main([str(source), "--html"])
            self.assertEqual(code, 0)
            review.assert_called_once()
            self.assertEqual(report, reference)
            self.assertEqual(json.loads(Document(out.getvalue()).download()), report)

    def test_invalid_input_and_native_refusal_have_no_document(self):
        late = json.loads(world_bytes())
        late["aircraft"][-1]["climb_ft_min"] = "invalid"
        cases = [(b"{", (), 2), (b'{"version":1,"version":2}', (), 2),
                 (json.dumps(late).encode(), (), 2), (world_bytes(), ("--now", "131"), 1),
                 (world_bytes(), ("--horizontal-nm", "0"), 2)]
        for raw, flags, expected in cases:
            with self.subTest(raw=raw[:30], flags=flags):
                old = self.run_cli(raw, *flags)
                new = self.run_cli(raw, "--html", *flags)
                self.assertEqual((old.returncode, new.returncode), (expected, expected))
                self.assertEqual(new.stdout, b"")
                self.assertEqual(new.stderr, old.stderr)

    @unittest.skipUnless(os.name == "posix" and Path("/dev/full").exists(),
                         "requires a POSIX failing output device")
    def test_failed_output_keeps_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "world.json"
            raw = world_bytes([])
            source.write_bytes(raw)
            for flags in ([], ["--html"]):
                with Path("/dev/full").open("wb") as output:
                    result = subprocess.run(
                        [sys.executable, "-B", str(ROOT / "plan_world.py"), str(source), *flags],
                        stdout=output, stderr=subprocess.PIPE, check=False, timeout=30,
                    )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(b"cannot write report", result.stderr)
                self.assertEqual(source.read_bytes(), raw)

    def test_offline_document_has_only_internal_links_and_exact_download(self):
        doc = Document(render_plan_html(
            json.dumps(plan_world.review_world(world_bytes([])), indent=2) + "\n"))
        self.assertFalse(any(n["tag"] in {"script", "link", "iframe", "img"} for n in doc.nodes))
        for node in doc.nodes:
            href = node["attrs"].get("href")
            if href is not None:
                self.assertTrue(href.startswith("#") or node["attrs"].get("id") == "download-json")
        self.assertGreater(len([n for n in doc.nodes if n["tag"] == "summary"]), 0)
        self.assertEqual(doc.by_id("download-json")["attrs"]["download"], "world-plan.json")


if __name__ == "__main__":
    unittest.main()
