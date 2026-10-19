"""Unit, changed-input, CLI and native-consumer tests for saved sector occupancy."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sector_occupancy import render_html, summarize_occupancy

ROOT = Path(__file__).resolve().parents[1]


def row(name: str, start: float, end: float, horizon: float = 8) -> dict:
    return {
        "aircraft_id": name, "entry_after_min": start, "exit_after_min": end,
        "entry_window_clipped": start == 0, "exit_window_clipped": end == horizon,
        "inside_at_observation": start == 0, "contact_only": start == end,
    }


def saved(rows=None, horizon: float = 8) -> dict:
    entries = rows if rows is not None else [row("A", 0, 5), row("B", 2, 4), row("C", 4, 4), row("D", 4, 8)]
    return {
        "format": "towerops.sector-report.v1", "simulation_only": True, "read_only": True,
        "input_sha256": "a" * 64, "world_hash": "b" * 64,
        "world_version": 4, "observed_at": 23,
        "sector": {"west_nm": -5, "east_nm": 10, "south_nm": 0, "north_nm": 10},
        "horizon_min": horizon, "contacts": entries, "contact_count": len(entries),
    }


def bytes_for(value: dict) -> bytes:
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode()


class CoreTests(unittest.TestCase):
    def test_peaks_distinguish_shared_boundaries_and_sustained_overlap(self):
        raw = bytes_for(saved())
        result = summarize_occupancy(raw)
        self.assertEqual(result["format"], "towerops.sector-occupancy.v1")
        self.assertEqual(result["source_sector_report_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["contact_only_count"], 1)
        self.assertEqual(result["peak_open_interval_count"], 2)
        self.assertEqual(result["peak_instantaneous_count"], 4)
        self.assertEqual(result["peak_instantaneous_times_min"], [4])
        self.assertEqual([(s["start_after_min"], s["end_after_min"], s["aircraft_ids"])
                          for s in result["segments"]],
                         [(0, 2, ["A"]), (2, 4, ["A", "B"]),
                          (4, 5, ["A", "D"]), (5, 8, ["D"])])
        self.assertEqual(len(result["peak_open_windows"]), 2)
        self.assertEqual(result["boundary_events"][2]["aircraft_ids"], ["A", "B", "C", "D"])
        self.assertFalse(result["source_verified"])

    def test_empty_report_and_zero_horizon(self):
        output = summarize_occupancy(bytes_for(saved([], 8)))
        self.assertEqual(output["peak_open_interval_count"], 0)
        self.assertEqual(output["peak_instantaneous_count"], 0)
        self.assertEqual(output["segments"], [{"start_after_min": 0, "end_after_min": 8,
                                                "aircraft_ids": [], "count": 0}])
        zero = summarize_occupancy(bytes_for(saved([row("TOUCH", 0, 0, 0)], 0)))
        self.assertEqual(zero["segments"], [])
        self.assertEqual(zero["peak_open_interval_count"], 0)
        self.assertEqual(zero["peak_instantaneous_count"], 1)
        self.assertEqual(zero["peak_instantaneous_times_min"], [0])

    def test_adjacent_closed_intervals_are_not_sustained_overlap(self):
        out = summarize_occupancy(bytes_for(saved([row("A", 0, 3), row("B", 3, 8)])))
        self.assertEqual(out["peak_open_interval_count"], 1)
        self.assertEqual(out["peak_instantaneous_count"], 2)
        self.assertEqual(out["peak_instantaneous_times_min"], [3])

    def test_input_bytes_unchanged_and_repeated_calls_deterministic(self):
        raw = bytes_for(saved())
        original = raw[:]
        self.assertEqual(summarize_occupancy(raw), summarize_occupancy(raw))
        self.assertEqual(raw, original)

    def test_seeded_independent_midpoint_and_exact_point_baselines(self):
        rng = random.Random(103)
        for _ in range(200):
            entries = []
            for i in range(rng.randrange(0, 18)):
                a = rng.randrange(0, 9)
                b = rng.randrange(a, 9)
                entries.append(row(f"T{i}", a, b))
            out = summarize_occupancy(bytes_for(saved(entries)))
            for s in out["segments"]:
                midpoint = (s["start_after_min"] + s["end_after_min"]) / 2
                expected = sorted(r["aircraft_id"] for r in entries if r["entry_after_min"] < midpoint < r["exit_after_min"])
                self.assertEqual(s["aircraft_ids"], expected)
            for event in out["boundary_events"]:
                t = event["at_after_min"]
                expected = sorted(r["aircraft_id"] for r in entries if r["entry_after_min"] <= t <= r["exit_after_min"])
                self.assertEqual(event["aircraft_ids"], expected)
            self.assertEqual(sum(s["end_after_min"] - s["start_after_min"] for s in out["segments"]), 8)

    def test_html_offline_genuine_visualization(self):
        summary = summarize_occupancy(bytes_for(saved()))
        page = render_html(summary)
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn('Content-Security-Policy', page)
        self.assertIn("peak between-event tracks", page)
        self.assertIn("Peak exact instants", page)
        self.assertIn("A</th><td>0</td><td>5", page)
        self.assertIn('left:25%;width:25%;', page)
        self.assertIn('class="point"', page)
        self.assertNotIn("<script", page)
        self.assertNotIn("https://", page)
        self.assertNotIn("http://", page)

    def test_invalid_admission_negative_controls(self):
        bad_values = []
        original = saved()
        mutations = [
            ("format", "towerops.fake"), ("simulation_only", False), ("read_only", "true"),
            ("input_sha256", "x" * 64), ("world_hash", "ABC"),
            ("world_version", True), ("world_version", -1),
            ("observed_at", "now"), ("horizon_min", -1), ("horizon_min", True),
            ("contact_count", 99), ("contacts", {}), ("contacts", [row("A", 0, 8)] * 61),
            ("sector", {"west_nm": 3, "east_nm": 2, "south_nm": 0, "north_nm": 10}),
        ]
        for key, value in mutations:
            broken = copy.deepcopy(original)
            broken[key] = value
            bad_values.append(bytes_for(broken))
        for key, value in [
            ("aircraft_id", "../../A"), ("aircraft_id", "B"), ("entry_after_min", -1),
            ("exit_after_min", 9), ("entry_after_min", True), ("contact_only", True),
            ("exit_window_clipped", "true"), ("inside_at_observation", "true"),
        ]:
            broken = copy.deepcopy(original)
            broken["contacts"][0][key] = value
            bad_values.append(bytes_for(broken))
        broken = copy.deepcopy(original)
        broken["contacts"][1]["aircraft_id"] = "A"
        bad_values.append(bytes_for(broken))
        broken = copy.deepcopy(original)
        broken["contacts"][1]["entry_window_clipped"] = True
        bad_values.append(bytes_for(broken))
        broken = copy.deepcopy(original)
        broken["contacts"][1]["inside_at_observation"] = True
        bad_values.append(bytes_for(broken))
        broken = copy.deepcopy(original)
        broken["contacts"][0]["exit_window_clipped"] = True
        bad_values.append(bytes_for(broken))
        bad_values += [
            b'{"format":"towerops.sector-report.v1","format":"towerops.sector-report.v1"}',
            b'{"format":"towerops.sector-report.v1","contact_count":NaN}',
            b'\xff', b'[]', bytes(262145),
        ]
        for bad in bad_values:
            with self.subTest(payload=bad[:60]), self.assertRaises((ValueError, TypeError)):
                summarize_occupancy(bad)


class CliTests(unittest.TestCase):
    def command(self, content: bytes, *args: str, via_file: bool = False):
        with tempfile.TemporaryDirectory() as folder:
            if via_file:
                path = Path(folder) / "report.json"
                path.write_bytes(content)
                return subprocess.run([sys.executable, str(ROOT / "sector_occupancy.py"), str(path), *args], capture_output=True, check=False)
            return subprocess.run([sys.executable, str(ROOT / "sector_occupancy.py"), "-", *args], input=content, capture_output=True, check=False)

    def test_file_stdin_json_and_html(self):
        data = bytes_for(saved())
        stdin = self.command(data)
        file_result = self.command(data, via_file=True)
        self.assertEqual(stdin.returncode, 0, stdin.stderr)
        self.assertEqual(stdin.stdout, file_result.stdout)
        self.assertEqual(stdin.stderr, b"")
        self.assertEqual(json.loads(stdin.stdout)["peak_instantaneous_count"], 4)
        html_result = self.command(data, "--format", "html")
        self.assertEqual(html_result.returncode, 0, html_result.stderr)
        self.assertIn(b"<html lang=", html_result.stdout)
        self.assertNotIn(b"<script", html_result.stdout)

    def test_invalid_report_has_no_stdout(self):
        for bad in (b"{}", bytes(262145), bytes_for(saved([], -1))):
            process = self.command(bad, "--format", "html")
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, b"")
            self.assertIn(b"error: cannot review sector occupancy", process.stderr)

    def test_directory_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.run([sys.executable, str(ROOT / "sector_occupancy.py"), folder], capture_output=True, check=False)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, b"")

    def test_output_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as folder:
            before = set(Path(folder).iterdir())
            process = self.command(bytes_for(saved()))
            self.assertEqual(process.returncode, 0)
            self.assertEqual(before, set(Path(folder).iterdir()))


class ActualNativeProducerTests(unittest.TestCase):
    """Run true producer -> consumer when tests execute inside the repository."""

    @unittest.skipUnless((ROOT / "sector_report.py").exists() and (ROOT / "plan_world.py").exists(),
                         "actual native sector producer is absent in this isolated runner")
    def test_native_sector_report_reaches_occupancy_consumer(self):
        world = {
            "version": 2, "observed_at": 100,
            "aircraft": [
                {"aircraft_id": "ALPHA", "x_nm": 1, "y_nm": 2, "altitude_ft": 10000,
                 "vx_nm_min": 0, "vy_nm_min": 0, "climb_ft_min": 0},
                {"aircraft_id": "BRAVO", "x_nm": -5, "y_nm": 2, "altitude_ft": 12000,
                 "vx_nm_min": 2, "vy_nm_min": 0, "climb_ft_min": 0},
            ],
        }
        produced = subprocess.run(
            [sys.executable, str(ROOT / "sector_report.py"), "-", "--west-nm", "0", "--east-nm", "10",
             "--south-nm", "0", "--north-nm", "10", "--horizon-min", "6"],
            input=bytes_for(world), capture_output=True, check=False,
        )
        self.assertEqual(produced.returncode, 0, produced.stderr)
        received = self.command(produced.stdout)
        self.assertEqual(received.returncode, 0, received.stderr)
        report = json.loads(received.stdout)
        self.assertEqual(report["peak_open_interval_count"], 2)
        self.assertEqual(report["source_world_input_sha256"], hashlib.sha256(bytes_for(world)).hexdigest())


if __name__ == "__main__":
    unittest.main()
