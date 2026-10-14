"""Ordinary saved-world authoring and file-custody checks; no planning."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from edit_world import edit_world
from plan_world import parse_world
from towerops import WorldState


def example():
    return {
        "version": 4,
        "observed_at": -0.0,
        "aircraft": [
            {"aircraft_id": "Z", "x_nm": 0, "y_nm": 2.5, "altitude_ft": 10000,
             "vx_nm_min": 1.0, "vy_nm_min": -0.0, "climb_ft_min": 0},
            {"aircraft_id": "A", "x_nm": 7.0, "y_nm": -3, "altitude_ft": 12000.0,
             "vx_nm_min": -2.5, "vy_nm_min": 0, "climb_ft_min": 500},
            {"aircraft_id": "a", "x_nm": 11, "y_nm": 4, "altitude_ft": 15000,
             "vx_nm_min": 0, "vy_nm_min": 1.5, "climb_ft_min": 0},
        ],
    }


def raw(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()


class SavedWorldEditTests(unittest.TestCase):
    def test_exact_selected_edit_preserves_other_fields_order_time_and_inputs(self):
        value = example()
        source = raw(value)
        changes = {"altitude_ft": 13500, "x_nm": 8.5}
        before_changes = copy.deepcopy(changes)
        expected = copy.deepcopy(value)
        expected["version"] = 5
        expected["aircraft"][1]["x_nm"] = 8.5
        expected["aircraft"][1]["altitude_ft"] = 13500
        output = edit_world(source, "A", changes)
        self.assertEqual(output, raw(expected))
        self.assertEqual(changes, before_changes)
        self.assertEqual(source, raw(value))
        admitted = parse_world(output)
        self.assertEqual([a.aircraft_id for a in admitted.aircraft], ["Z", "A", "a"])
        self.assertEqual(math.copysign(1, admitted.observed_at), -1)

    def test_uses_original_native_replace_once_with_original_time(self):
        calls = []
        original = WorldState.replace_aircraft
        def observe(state, updated, observed_at):
            calls.append((state.version, updated.aircraft_id, observed_at))
            return original(state, updated, observed_at)
        with patch.object(WorldState, "replace_aircraft", observe):
            result = edit_world(raw(example()), "a", {"climb_ft_min": 100})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], (4, "a"))
        self.assertEqual(math.copysign(1, calls[0][2]), -1)
        self.assertEqual(parse_world(result).version, 5)

    def test_explicit_numeric_representation_changes_are_retained(self):
        expected = example()
        expected["version"] = 5
        expected["aircraft"][0]["x_nm"] = 0.0
        expected["aircraft"][0]["vy_nm_min"] = 0.0
        result = edit_world(raw(example()), "Z", {"x_nm": 0.0, "vy_nm_min": 0.0})
        self.assertEqual(result, raw(expected))
        a = parse_world(result).get("Z")
        self.assertIs(type(a.x_nm), float)
        self.assertEqual(math.copysign(1, a.vy_nm_min), 1)

    def test_all_six_explicit_components_use_the_same_native_envelope(self):
        changes = {"x_nm": 9, "y_nm": -4.0, "altitude_ft": 11000,
                   "vx_nm_min": 2.0, "vy_nm_min": -1, "climb_ft_min": 250}
        expected = example()
        expected["version"] = 5
        expected["aircraft"][0].update(changes)
        self.assertEqual(edit_world(raw(example()), "Z", changes), raw(expected))

    def test_unknown_or_unchanged_edit_does_not_produce_a_revision(self):
        source = raw(example())
        with self.assertRaisesRegex(ValueError, "Unknown aircraft_id"):
            edit_world(source, "missing", {"x_nm": 3})
        with self.assertRaisesRegex(ValueError, "Change at least one"):
            edit_world(source, "A", {"x_nm": 7.0})
        self.assertEqual(source, raw(example()))

    def run_cli(self, directory, *arguments):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "edit_world.py"), *arguments],
            cwd=directory, env=env, capture_output=True, timeout=10, check=False,
        )

    def test_actual_cli_new_file_and_literal_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "old world.json"
            source.write_bytes(raw(example()))
            stamp = source.stat().st_mtime_ns
            result = self.run_cli(directory, source.name, "--aircraft", "A", "--out", "new world.json",
                                  "--altitude-ft", "13500", "--x-nm", "8.5")
            self.assertEqual((result.returncode, result.stderr), (0, b""))
            output = (directory / "new world.json").read_bytes()
            expected = example()
            expected["version"] = 5
            expected["aircraft"][1].update(x_nm=8.5, altitude_ft=13500)
            self.assertEqual(output, raw(expected))
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt, {
                "format": "towerops.world-edit-created.v1",
                "source": {"path": source.name, "bytes": len(source.read_bytes()),
                           "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
                "output": {"path": "new world.json", "bytes": len(output),
                           "sha256": hashlib.sha256(output).hexdigest()},
                "aircraft_id": "A", "changed_fields": ["x_nm", "altitude_ft"],
                "source_version": 4, "version": 5, "observed_at": -0.0,
            })
            self.assertEqual(source.read_bytes(), raw(example()))
            self.assertEqual(source.stat().st_mtime_ns, stamp)

    def test_existing_output_is_kept_with_no_success_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "before.json").write_bytes(raw(example()))
            output = directory / "keep.json"
            output.write_bytes(b"an earlier authored world\n")
            stamp = output.stat().st_mtime_ns
            result = self.run_cli(directory, "before.json", "--aircraft", "Z", "--out", "keep.json", "--x-nm", "4")
            self.assertEqual((result.returncode, result.stdout), (2, b""))
            self.assertIn(b"Output already exists", result.stderr)
            self.assertEqual(output.read_bytes(), b"an earlier authored world\n")
            self.assertEqual(output.stat().st_mtime_ns, stamp)

    def test_repeated_field_is_usage_refusal_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "before.json").write_bytes(raw(example()))
            result = self.run_cli(directory, "before.json", "--aircraft", "Z", "--out", "after.json",
                                  "--x-nm", "3", "--x-nm", "4")
            self.assertEqual((result.returncode, result.stdout), (2, b""))
            self.assertIn(b"only once", result.stderr)
            self.assertFalse((directory / "after.json").exists())


if __name__ == "__main__":
    unittest.main()
