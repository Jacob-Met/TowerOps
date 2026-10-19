"""Geometry and native-CLI receiving tests for sector_report."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sector_report import axis_interval, sector_interval

ROOT = Path(__file__).resolve().parents[1]


def contact(x: float, y: float, vx: float, vy: float, horizon: float = 5.0):
    return sector_interval(x, y, vx, vy, 0.0, 10.0, 0.0, 10.0, horizon)


class GeometryTests(unittest.TestCase):
    def test_stationary_interior_and_exterior(self):
        self.assertEqual(contact(5, 5, 0, 0), (0, 5))
        self.assertIsNone(contact(-1, 5, 0, 0))
        self.assertEqual(contact(0, 10, 0, 0), (0, 5))

    def test_crossing_and_horizon_clipping(self):
        self.assertEqual(contact(-5, 5, 2, 0, 8), (2.5, 7.5))
        self.assertEqual(contact(-5, 5, 2, 0, 4), (2.5, 4))
        self.assertIsNone(contact(-5, 5, 2, 0, 2))

    def test_negative_direction_and_currently_inside_exit(self):
        self.assertEqual(contact(15, 5, -5, 0), (1, 3))
        self.assertEqual(contact(5, 5, 1, 0, 20), (0, 5))

    def test_diagonal_corner_contact_is_zero_duration(self):
        self.assertEqual(contact(-5, 5, 1, 1, 20), (5, 5))
        self.assertEqual(contact(-5, -5, 1, 1, 20), (5, 15))

    def test_disjoint_per_axis_windows(self):
        self.assertIsNone(contact(-5, 15, 1, 1, 20))
        self.assertIsNone(contact(-5, 15, 1, -1, 4))

    def test_zero_horizon_uses_closed_boundary(self):
        self.assertEqual(contact(0, 0, -1, -1, 0), (0, 0))
        self.assertIsNone(contact(-1, 0, 1, 0, 0))

    def test_single_axis_stillness_and_tiny_rates(self):
        self.assertEqual(axis_interval(5, 0, 0, 10), (-math.inf, math.inf))
        self.assertIsNone(axis_interval(-1, 0, 0, 10))
        self.assertEqual(contact(5, 5, 1e-310, -1e-310), (0, 5))

    def test_translation_equivariance(self):
        original = sector_interval(-3, 12, 4, -2, 0, 10, 0, 10, 8)
        translated = sector_interval(997, -1988, 4, -2, 1000, 1010, -2000, -1990, 8)
        self.assertEqual(original, translated)

    def test_boundary_endpoint_touch_at_horizon(self):
        self.assertEqual(contact(-5, 5, 1, 0, 5), (5, 5))
        self.assertEqual(contact(5, 5, -1, 0, 5), (0, 5))


WORLD = {
    "version": 3,
    "observed_at": 100.0,
    "aircraft": [
        {"aircraft_id": "LATER", "x_nm": -10, "y_nm": 5,
         "altitude_ft": 12000, "vx_nm_min": 2, "vy_nm_min": 0, "climb_ft_min": 0},
        {"aircraft_id": "NOW", "x_nm": 5, "y_nm": 5,
         "altitude_ft": 8000, "vx_nm_min": 0, "vy_nm_min": 0, "climb_ft_min": 0},
        {"aircraft_id": "MISS", "x_nm": 20, "y_nm": 20,
         "altitude_ft": 5000, "vx_nm_min": 0, "vy_nm_min": 0, "climb_ft_min": 0},
    ],
}


class NativeCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import plan_world  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("native TowerOps plan_world.py is unavailable in this isolated geometry runner") from None

    def command(self, *extra: str, payload: bytes | None = None, via_stdin: bool = True):
        options = ["--west-nm", "0", "--east-nm", "10", "--south-nm", "0", "--north-nm", "10"]
        data = json.dumps(WORLD).encode() if payload is None else payload
        if via_stdin:
            return subprocess.run([sys.executable, str(ROOT / "sector_report.py"), "-", *options, *extra],
                                  input=data, capture_output=True, check=False)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "world.json"
            path.write_bytes(data)
            return subprocess.run([sys.executable, str(ROOT / "sector_report.py"), str(path), *options, *extra],
                                  capture_output=True, check=False)

    def test_native_file_and_stdin_same_json(self):
        stdin = self.command()
        named = self.command(via_stdin=False)
        self.assertEqual(stdin.returncode, 0, stdin.stderr)
        self.assertEqual(named.returncode, 0, named.stderr)
        self.assertEqual(json.loads(stdin.stdout), json.loads(named.stdout))
        report = json.loads(stdin.stdout)
        self.assertEqual(report["format"], "towerops.sector-report.v1")
        self.assertEqual([t["aircraft_id"] for t in report["contacts"]], ["NOW", "LATER"])
        self.assertEqual(report["contacts"][1]["entry_after_min"], 5)
        self.assertTrue(report["read_only"])
        self.assertEqual(report["world_version"], 3)

    def test_no_contact_and_zero_horizon(self):
        result = self.command("--horizon-min", "0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([x["aircraft_id"] for x in json.loads(result.stdout)["contacts"]], ["NOW"])

    def test_invalid_bounds_are_atomic(self):
        invalid = self.command("--horizon-min", "-1")
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(invalid.stdout)

    def test_duplicate_fields_are_native_refusal(self):
        raw = b'{"version":0,"version":1,"observed_at":1,"aircraft":[]}'
        invalid = self.command(payload=raw)
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(invalid.stdout)

    def test_refuse_oversize_without_output(self):
        invalid = self.command(payload=b" " * 262145)
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(invalid.stdout)

    def test_nonfinite_args_not_admitted(self):
        invalid = self.command("--horizon-min", "1e999")
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(invalid.stdout)


if __name__ == "__main__":
    unittest.main()
