"""Behavior and native CLI receiving for saved-plan/source identity comparison."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import check_plan_source as binding
from plan_world import MAX_WORLD_BYTES, review_world


def encoded(value: object, *, compact: bool = False) -> bytes:
    if compact:
        return json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")


def world() -> dict:
    return {
        "version": 4, "observed_at": -0.0,
        "aircraft": [
            {"aircraft_id": "ALPHA", "x_nm": -8.0, "y_nm": 0.0,
             "altitude_ft": 11000, "vx_nm_min": 2.0, "vy_nm_min": -0.0,
             "climb_ft_min": 0},
            {"aircraft_id": "BETA", "x_nm": 8.0, "y_nm": 0.0,
             "altitude_ft": 11000, "vx_nm_min": -2.0, "vy_nm_min": 0,
             "climb_ft_min": 0},
        ],
    }


class SourceBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_world = encoded(world())
        cls.report = encoded(review_world(cls.original_world))
        cls.compact_world = encoded(world(), compact=True)
        changed = world()
        changed["aircraft"][0]["x_nm"] = -7.5
        cls.changed_world = encoded(changed)
        assert cls.original_world != cls.compact_world

    def test_true_original_exact_world_and_report_identities(self):
        result = binding.verify_plan_source(self.report, self.original_world)
        self.assertEqual(result["format"], "towerops.plan-source-binding.v1")
        self.assertEqual(result["binding_status"], "exact_bytes_and_world")
        self.assertTrue(result["matched"])
        self.assertEqual(result["checks"], {
            "input_bytes_sha256_match": True,
            "native_world_hash_match": True,
        })
        self.assertTrue(result["simulation_only"])
        self.assertTrue(result["proposal_only"])
        self.assertEqual(result["report"]["sha256"], hashlib.sha256(self.report).hexdigest())
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(self.original_world).hexdigest())
        self.assertEqual(result["source"]["world_hash"], result["report"]["world_hash"])
        self.assertEqual(result["source"]["version"], 4)
        self.assertEqual(json.dumps(result["source"]["observed_at"]), "-0.0")
        self.assertEqual(result["source"]["aircraft_count"], 2)
        self.assertNotIn("report_path", result)
        self.assertNotIn("world_path", result)

    def test_reformatted_same_native_world_not_original_bytes(self):
        result = binding.verify_plan_source(self.report, self.compact_world)
        self.assertFalse(result["matched"])
        self.assertEqual(result["binding_status"], "same_native_world_different_bytes")
        self.assertFalse(result["checks"]["input_bytes_sha256_match"])
        self.assertTrue(result["checks"]["native_world_hash_match"])
        self.assertNotEqual(result["report"]["reported_input_sha256"], result["source"]["sha256"])
        self.assertEqual(result["report"]["world_hash"], result["source"]["world_hash"])

    def test_changed_world_differs_in_both_identities(self):
        result = binding.verify_plan_source(self.report, self.changed_world)
        self.assertEqual(result["binding_status"], "different_bytes_and_world")
        self.assertFalse(result["matched"])
        self.assertFalse(any(result["checks"].values()))
        self.assertNotEqual(result["report"]["world_hash"], result["source"]["world_hash"])

    def test_claimed_matching_bytes_with_different_native_world_is_not_success(self):
        altered = json.loads(self.report)
        altered["input_sha256"] = hashlib.sha256(self.changed_world).hexdigest()
        result = binding.verify_plan_source(encoded(altered), self.changed_world)
        self.assertEqual(result["binding_status"], "reported_bytes_but_different_world")
        self.assertEqual(result["checks"], {
            "input_bytes_sha256_match": True, "native_world_hash_match": False,
        })
        self.assertFalse(result["matched"])

    def test_no_mutation_or_planning_during_comparison(self):
        original_report, original_world = self.report, self.original_world
        with (
            patch("plan_world.review_world", side_effect=AssertionError("planner ran")),
            patch("advisory_options.review_advisory_options", side_effect=AssertionError("search ran")),
            patch("towerops.SafetyPolicy.conflicting_aircraft", side_effect=AssertionError("screening ran")),
        ):
            result = binding.verify_plan_source(original_report, original_world)
        self.assertTrue(result["matched"])
        self.assertEqual(self.report, original_report)
        self.assertEqual(self.original_world, original_world)

    def test_empty_world_and_literal_signed_zero(self):
        raw = encoded({"version": 0, "observed_at": -0.0, "aircraft": []})
        report = encoded(review_world(raw))
        result = binding.verify_plan_source(report, raw)
        self.assertTrue(result["matched"])
        self.assertEqual(result["source"]["aircraft_count"], 0)
        self.assertEqual(result["report"]["status"], "no_conflict")
        self.assertEqual(json.dumps(result["source"]["observed_at"]), "-0.0")

    def test_reject_invalid_report_before_world_and_no_partial_result(self):
        cases = [
            b'{"format":"first","format":"second"}',
            b'{"format":NaN}',
            b'[]',
            b"{" + b" " * (4 * 1024 * 1024) + b"}",
        ]
        invalid_body = json.loads(self.report)
        invalid_body["advisories"][0]["advisory_hash"] = "0" * 64
        cases.append(encoded(invalid_body))
        for raw in cases:
            with self.subTest(length=len(raw)), self.assertRaisesRegex(ValueError, "Saved report"):
                binding.verify_plan_source(raw, self.original_world)

    def test_reject_invalid_world_even_if_report_is_acceptable(self):
        duplicate = world()
        duplicate["aircraft"].append(copy.deepcopy(duplicate["aircraft"][0]))
        invalid_cases = [
            b'{"version":1,"version":1,"observed_at":0,"aircraft":[]}',
            b'{"version":1,"observed_at":NaN,"aircraft":[]}',
            b'{"version":1,"observed_at":0,"aircraft":"wrong"}',
            b'{"version":true,"observed_at":0,"aircraft":[]}',
            b"{" + b" " * (MAX_WORLD_BYTES + 1) + b"}",
            encoded(duplicate),
        ]
        for raw in invalid_cases:
            with self.subTest(length=len(raw)), self.assertRaisesRegex(ValueError, "Raw source world"):
                binding.verify_plan_source(self.report, raw)

    def test_nonbytes_refused_and_no_implicit_coercion(self):
        with self.assertRaisesRegex(ValueError, "Saved report"):
            binding.verify_plan_source("not bytes", self.original_world)
        with self.assertRaisesRegex(ValueError, "Raw source world"):
            binding.verify_plan_source(self.report, bytearray(self.original_world))

    def test_text_renders_status_hashes_clock_and_limits_ascii_safely(self):
        result = binding.verify_plan_source(self.report, self.original_world)
        result["report_path"] = 'r"\n\u03bb.json'
        result["world_path"] = "w\r.json"
        text = binding.render_text(result)
        self.assertTrue(text.isascii())
        self.assertIn('Saved report path: "r\\\"\\n\\u03bb.json"', text)
        self.assertIn('Raw world path: "w\\r.json"', text)
        self.assertIn("Research simulation only.", text)
        self.assertIn("Source observation clock (synthetic sec): -0.0", text)
        self.assertIn(result["report"]["sha256"], text)
        self.assertIn("do not authenticate", text)
        self.assertTrue(text.endswith("\n"))

    def test_actual_process_in_foreign_directory_under_normal_and_optimized_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                "report": root / 'recorded plan \u03bb.json',
                "original": root / "source original.json",
                "reformatted": root / "source compact.json",
                "changed": root / "source changed.json",
            }
            for name, contents in (
                ("report", self.report), ("original", self.original_world),
                ("reformatted", self.compact_world), ("changed", self.changed_world),
            ):
                paths[name].write_bytes(contents)
            untouched = {
                name: (path.read_bytes(), path.stat().st_mtime_ns)
                for name, path in paths.items()
            }
            for optimized in (False, True):
                prefix = [sys.executable, "-B", *(["-O"] if optimized else []),
                          str(ROOT / "check_plan_source.py")]
                for key, expected_status, expected_code in (
                    ("original", "exact_bytes_and_world", 0),
                    ("reformatted", "same_native_world_different_bytes", 1),
                    ("changed", "different_bytes_and_world", 1),
                ):
                    with self.subTest(optimized=optimized, source=key):
                        cmd = [*prefix, str(paths["report"]), str(paths[key]), "--json"]
                        run = subprocess.run(cmd, cwd=directory, capture_output=True, text=True, check=False)
                        self.assertEqual(run.returncode, expected_code, run.stderr)
                        self.assertEqual(run.stderr, "")
                        result = json.loads(run.stdout)
                        self.assertEqual(result["binding_status"], expected_status)
                        self.assertEqual(result["report_path"], str(paths["report"]))
                        self.assertEqual(result["world_path"], str(paths[key]))
                plain = subprocess.run([*prefix, str(paths["report"]), str(paths["original"])],
                                       cwd=directory, capture_output=True, text=True, check=False)
                self.assertEqual(plain.returncode, 0, plain.stderr)
                self.assertIn("Exact original bytes and native world both match: true", plain.stdout)
            for name, path in paths.items():
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), untouched[name])

    def test_cli_error_has_empty_stdout_and_no_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path = root / "report.json"
            world_path = root / "world.json"
            report_path.write_bytes(self.report)
            world_path.write_bytes(b'{"version":0,"observed_at":0,"aircraft":[],"aircraft":[]}')
            cmd = [sys.executable, "-B", str(ROOT / "check_plan_source.py"),
                   str(report_path), str(world_path), "--json"]
            run = subprocess.run(cmd, cwd=directory, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, "")
            self.assertIn("Raw source world", run.stderr)
            self.assertEqual(report_path.read_bytes(), self.report)
            self.assertEqual(world_path.read_bytes(), b'{"version":0,"observed_at":0,"aircraft":[],"aircraft":[]}')

    def test_report_symlink_refused_and_world_symlink_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_report = root / "report.json"
            original_world = root / "world.json"
            report_link = root / "report-link.json"
            world_link = root / "world-link.json"
            original_report.write_bytes(self.report)
            original_world.write_bytes(self.original_world)
            try:
                report_link.symlink_to(original_report)
                world_link.symlink_to(original_world)
            except (NotImplementedError, OSError):
                self.skipTest("symlinks unavailable in this environment")
            with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                self.assertEqual(binding.main([str(report_link), str(original_world)]), 2)
            output = io.StringIO()
            with patch("sys.stdout", output), patch("sys.stderr", io.StringIO()):
                self.assertEqual(binding.main([str(original_report), str(world_link), "--json"]), 0)
            self.assertTrue(json.loads(output.getvalue())["matched"])

    def test_output_failure_return_code_two_and_no_success_claim(self):
        class FailingStdout:
            def write(self, _text):
                raise BrokenPipeError("write refused")
            def flush(self):
                raise BrokenPipeError("flush refused")
            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            report_file = Path(directory) / "report.json"
            world_file = Path(directory) / "world.json"
            report_file.write_bytes(self.report)
            world_file.write_bytes(self.original_world)
            errors = io.StringIO()
            with patch("sys.stdout", FailingStdout()), patch("sys.stderr", errors):
                self.assertEqual(binding.main([str(report_file), str(world_file)]), 2)
            self.assertIn("cannot write binding result", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
