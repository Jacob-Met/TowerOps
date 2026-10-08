"""Native saved-pair consumer controls; no browser, server or planner fixture."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from inspect_encounter import inspect_encounter
from plan_world import MAX_WORLD_BYTES, parse_world
from towerops import AdvisoryPlanner, ControlRoom, SafetyPolicy

ROOT = Path(__file__).resolve().parents[1]


def world_bytes(altitude: int | float = 12000, **second_changes: int | float) -> bytes:
    first = dict(
        aircraft_id="A", x_nm=0, y_nm=0, altitude_ft=10000,
        vx_nm_min=0, vy_nm_min=0, climb_ft_min=0,
    )
    second = {
        **first, "aircraft_id": "B", "x_nm": 6, "altitude_ft": altitude,
        "vx_nm_min": -4, "climb_ft_min": -1000, **second_changes,
    }
    return json.dumps({"version": 7, "observed_at": 120, "aircraft": [second, first]}).encode()


class EncounterTests(unittest.TestCase):
    def test_known_simultaneous_windows_and_cursor(self):
        raw = world_bytes()
        result = inspect_encounter(raw, "A", "B", at_min=1.5)
        self.assertEqual(result["horizontal_window_min"], (0.25, 2.75))
        self.assertEqual(result["vertical_window_min"], (1, 3))
        self.assertEqual(result["overlap_window_min"], (1, 2.75))
        self.assertTrue(result["native_pair_conflict"])
        self.assertEqual(result["closest_horizontal"], result["cursor"])
        self.assertEqual(result["cursor"], {
            "minutes": 1.5, "horizontal_nm": 0, "vertical_ft": 500,
            "horizontal_below": True, "vertical_below": True, "simultaneous": True,
        })

    def test_disjoint_windows_do_not_become_a_conflict(self):
        raw = world_bytes(14000)
        early = inspect_encounter(raw, "A", "B", at_min=1.5)
        late = inspect_encounter(raw, "A", "B", at_min=4)
        self.assertEqual(early["horizontal_window_min"], (0.25, 2.75))
        self.assertEqual(early["vertical_window_min"], (3, 5))
        self.assertIsNone(early["overlap_window_min"])
        self.assertFalse(early["native_pair_conflict"])
        self.assertTrue(early["cursor"]["horizontal_below"])
        self.assertFalse(early["cursor"]["vertical_below"])
        self.assertFalse(late["cursor"]["horizontal_below"])
        self.assertTrue(late["cursor"]["vertical_below"])
        self.assertFalse(late["cursor"]["simultaneous"])
        for key in early.keys() - {"cursor"}:
            self.assertEqual(early[key], late[key], key)

    def test_touching_windows_and_threshold_equality(self):
        raw = world_bytes(13750)
        touching = inspect_encounter(raw, "A", "B", at_min=2.75)
        self.assertEqual(touching["vertical_window_min"], (2.75, 4.75))
        self.assertIsNone(touching["overlap_window_min"])
        self.assertFalse(touching["native_pair_conflict"])
        self.assertEqual(touching["cursor"]["horizontal_nm"], 5)
        self.assertEqual(touching["cursor"]["vertical_ft"], 1000)
        self.assertFalse(touching["cursor"]["horizontal_below"])
        self.assertFalse(touching["cursor"]["vertical_below"])
        for time, key in [(0.25, "horizontal_below"), (1, "vertical_below")]:
            with self.subTest(time=time):
                self.assertFalse(inspect_encounter(world_bytes(), "A", "B", at_min=time)["cursor"][key])

    def test_horizon_clipping_preserves_strict_overlap(self):
        policy = replace(SafetyPolicy(), horizon_min=1)
        result = inspect_encounter(world_bytes(), "A", "B", at_min=1, policy=policy)
        self.assertEqual(result["horizontal_window_min"], (0.25, 1))
        self.assertIsNone(result["vertical_window_min"])
        self.assertIsNone(result["overlap_window_min"])
        self.assertFalse(result["native_pair_conflict"])
        self.assertEqual(result["closest_horizontal"]["minutes"], 1)
        self.assertEqual(result["policy"], asdict(policy))
        policy = replace(policy, horizon_min=2)
        result = inspect_encounter(world_bytes(), "A", "B", policy=policy)
        self.assertEqual(result["overlap_window_min"], (1, 2))
        self.assertTrue(result["native_pair_conflict"])

    def test_stationary_and_diverging_closest_times(self):
        raw = world_bytes(10000, x_nm=2, vx_nm_min=0, climb_ft_min=0)
        for time in (0, 5):
            with self.subTest(time=time):
                result = inspect_encounter(raw, "A", "B", at_min=time)
                self.assertEqual(result["overlap_window_min"], (0, 5))
                self.assertEqual(result["closest_horizontal"]["minutes"], 0)
                self.assertTrue(result["cursor"]["simultaneous"])
        result = inspect_encounter(world_bytes(10000, vx_nm_min=4), "A", "B")
        self.assertEqual(result["closest_horizontal"]["minutes"], 0)
        self.assertIsNone(result["horizontal_window_min"])

    def test_horizontal_tangency_is_not_below_threshold(self):
        result = inspect_encounter(world_bytes(10000, y_nm=5, climb_ft_min=0), "A", "B", at_min=1.5)
        self.assertIsNone(result["horizontal_window_min"])
        self.assertIsNone(result["overlap_window_min"])
        self.assertEqual(result["cursor"]["horizontal_nm"], 5)
        self.assertFalse(result["cursor"]["simultaneous"])

    def test_order_identity_and_raw_numeric_provenance(self):
        data = json.loads(world_bytes())
        data["observed_at"] = -0.0
        data["aircraft"][1]["aircraft_id"] = "a"
        raw = (json.dumps(data, indent=1) + "\n").encode()
        before = bytes(raw)
        forward = inspect_encounter(raw, "a", "B")
        reverse = inspect_encounter(raw, "B", "a")
        self.assertEqual(forward["aircraft_a"], "a")
        self.assertEqual(reverse["aircraft_a"], "B")
        for key in forward.keys() - {"aircraft_a", "aircraft_b"}:
            self.assertEqual(forward[key], reverse[key], key)
        self.assertEqual(raw, before)
        self.assertEqual(forward["input_sha256"], hashlib.sha256(raw).hexdigest())
        state = parse_world(raw)
        self.assertEqual(forward["world"], state.to_dict())
        self.assertEqual(forward["world_hash"], state.world_hash)
        self.assertEqual(math.copysign(1, forward["world"]["observed_at"]), -1)

    def test_native_helper_and_pair_verdict_parity(self):
        policies = [SafetyPolicy(), replace(SafetyPolicy(), min_horizontal_nm=2, min_vertical_ft=300, horizon_min=2)]
        for raw in [world_bytes(), world_bytes(14000), world_bytes(13750), world_bytes(10000, x_nm=2, vx_nm_min=0)]:
            state = parse_world(raw)
            a, b = state.get("A"), state.get("B")
            for policy in policies:
                with self.subTest(raw=raw, policy=policy):
                    result = inspect_encounter(raw, "A", "B", policy=policy)
                    self.assertEqual(result["horizontal_window_min"], policy._horizontal_unsafe_interval(
                        a.x_nm-b.x_nm, a.y_nm-b.y_nm, a.vx_nm_min-b.vx_nm_min,
                        a.vy_nm_min-b.vy_nm_min, policy.min_horizontal_nm, policy.horizon_min))
                    self.assertEqual(result["vertical_window_min"], policy._linear_abs_unsafe_interval(
                        a.altitude_ft-b.altitude_ft, a.climb_ft_min-b.climb_ft_min,
                        policy.min_vertical_ft, policy.horizon_min))
                    self.assertEqual(result["native_pair_conflict"], policy._pair_conflict(a, b))
                    self.assertEqual(result["overlap_window_min"] is not None, result["native_pair_conflict"])

    def test_never_calls_planner_or_control_room(self):
        with (
            patch.object(AdvisoryPlanner, "plan", side_effect=AssertionError("planner called")),
            patch.object(AdvisoryPlanner, "_maneuver_candidates", side_effect=AssertionError("menu called")),
            patch.object(ControlRoom, "screen_batch", side_effect=AssertionError("gate called")),
            patch.object(ControlRoom, "apply", side_effect=AssertionError("apply called")),
        ):
            result = inspect_encounter(world_bytes(), "A", "B", at_min=2)
        self.assertTrue(result["native_pair_conflict"])
        self.assertEqual(result["world"]["observed_at"], 120)
        self.assertEqual(result["world"]["version"], 7)
        self.assertNotIn("advisories", result)

    def test_unknown_same_or_invalid_selected_identifiers(self):
        for first, second in [("A", "missing"), ("missing", "A"), ("a", "B"), ("A", "A"), (None, "B"), ("A", ["B"])]:
            with self.subTest(first=first, second=second):
                with self.assertRaises((ValueError, TypeError)):
                    inspect_encounter(world_bytes(), first, second)

    def test_cursor_and_policy_refusals(self):
        for cursor in [-1, 5.00001, True, "1", None, float("nan"), float("inf")]:
            with self.subTest(cursor=cursor):
                with self.assertRaises(ValueError):
                    inspect_encounter(world_bytes(), "A", "B", at_min=cursor)
        for policy in [False, replace(SafetyPolicy(), horizon_min=0), replace(SafetyPolicy(), min_horizontal_nm=float("inf"))]:
            with self.subTest(policy=policy):
                with self.assertRaises((ValueError, TypeError)):
                    inspect_encounter(world_bytes(), "A", "B", policy=policy)

    def test_existing_complete_world_admission_is_retained(self):
        for raw in [b"{}", b"\xff", b'{"version":1,"version":2}', b" "*(MAX_WORLD_BYTES+1), world_bytes()+b"bad"]:
            with self.subTest(raw=raw[:80]):
                with self.assertRaises((ValueError, TypeError)):
                    inspect_encounter(raw, "A", "B")


class CliTests(unittest.TestCase):
    def invoke(self, *args, data=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "inspect_encounter.py"), *args],
            input=data, capture_output=True, check=False, timeout=10,
        )

    def test_file_stdin_equivalence_and_input_preservation(self):
        raw = world_bytes()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "world.json"
            path.write_bytes(raw)
            file_result = self.invoke(str(path), "B", "A", "--at-min", "1.5", "--horizon-min", "4")
            stdin_result = self.invoke("-", "B", "A", "--at-min", "1.5", "--horizon-min", "4", data=raw)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(list(Path(temp).iterdir()), [path])
        self.assertEqual(file_result.returncode, 0, file_result.stderr)
        self.assertEqual(file_result.stderr, b"")
        self.assertEqual(file_result.stdout, stdin_result.stdout)
        result = json.loads(file_result.stdout)
        self.assertEqual(result["cursor"]["minutes"], 1.5)
        self.assertEqual(result["policy"]["horizon_min"], 4)
        self.assertEqual(result["aircraft_a"], "B")

    def test_argument_and_input_failures_have_no_report(self):
        for arguments, raw in [
            (["-", "A", "B", "--at-min", "true"], world_bytes()),
            (["-", "A", "B", "--at-min", "6"], world_bytes()),
            (["-", "A", "B", "--horizon-min", "0"], world_bytes()),
            (["-", "A", "missing"], world_bytes()),
            (["-", "A", "B"], world_bytes()+b"late"),
            (["-", "A", "B"], b" "*(MAX_WORLD_BYTES+1)),
        ]:
            with self.subTest(arguments=arguments, raw=raw[:40]):
                result = self.invoke(*arguments, data=raw)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertTrue(result.stderr)

    @unittest.skipUnless(os.path.exists("/dev/full"), "requires the native full output device")
    def test_output_failure_returns_failure(self):
        with open("/dev/full", "wb") as stream:
            result = subprocess.run(
                [sys.executable, str(ROOT/"inspect_encounter.py"), "-", "A", "B"],
                input=world_bytes(), stdout=stream, stderr=subprocess.PIPE, check=False, timeout=10,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"cannot write report", result.stderr)


if __name__ == "__main__":
    unittest.main()
