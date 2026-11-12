"""Consumer and negative controls for deterministic synthetic-world producer."""

from __future__ import annotations

import contextlib
import io
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from plan_world import MAX_VERSION, parse_world
from synthesize_world import MAX_SEED, main, synthesize_world
from towerops import SafetyPolicy

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "synthesize_world.py"
PLANNER = ROOT / "plan_world.py"


def launch(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args],
        cwd=cwd or ROOT, capture_output=True, text=True, check=False,
    )


class SynthesizedWorldTests(unittest.TestCase):
    def test_deterministic_native_world_for_both_modes_and_counts(self) -> None:
        for mode in ("encounter", "clear"):
            for count in (2, 3, 8, 60):
                for seed in (0, 1, 999):
                    with self.subTest(mode=mode, count=count, seed=seed):
                        a = synthesize_world(seed, count, mode)
                        b = synthesize_world(seed, count, mode)
                        self.assertEqual(a, b)
                        world = parse_world(json.dumps(a).encode("utf-8"))
                        self.assertEqual(world.to_dict(), a)
                        self.assertEqual(len(world.aircraft), count)
                        self.assertEqual(SafetyPolicy().state_has_conflict(world), mode == "encounter")
                        self.assertEqual(
                            [v.aircraft_id for v in world.aircraft],
                            [f"SYN{i:02d}" for i in range(count)],
                        )

    def test_seed_changes_geometry_not_identity_or_mode(self) -> None:
        one = synthesize_world(11, 6)
        two = synthesize_world(12, 6)
        self.assertNotEqual(one, two)
        self.assertEqual(
            [a["aircraft_id"] for a in one["aircraft"]],
            [a["aircraft_id"] for a in two["aircraft"]],
        )
        self.assertTrue(SafetyPolicy().state_has_conflict(parse_world(json.dumps(two).encode())))

    def test_primary_pair_meets_authored_timing_and_clear_mode_diverges(self) -> None:
        for seed in range(12):
            for mode in ("encounter", "clear"):
                with self.subTest(seed=seed, mode=mode):
                    world = parse_world(json.dumps(synthesize_world(seed, 60, mode)).encode())
                    a, b = world.aircraft[:2]
                    distance_at_zero = math.hypot(a.x_nm - b.x_nm, a.y_nm - b.y_nm)
                    a5, b5 = a.projected(5), b.projected(5)
                    distance_at_five = math.hypot(a5.x_nm - b5.x_nm, a5.y_nm - b5.y_nm)
                    self.assertEqual(distance_at_zero, 20)
                    self.assertEqual(distance_at_five, 0 if mode == "encounter" else 40)
                    self.assertEqual(a.altitude_ft, b.altitude_ft)
                    self.assertEqual(SafetyPolicy()._pair_conflict(a, b), mode == "encounter")
                    # Independent coordinate bounds show backgrounds cannot
                    # approach each other or the primary pair in five minutes.
                    for i, x in enumerate(world.aircraft):
                        for y in world.aircraft[i + 1:]:
                            if (x, y) == (a, b):
                                continue
                            self.assertGreater(abs(x.x_nm - y.x_nm) - 5 * abs(x.vx_nm_min - y.vx_nm_min), 5)

    def test_bounds_and_literal_numeric_identity(self) -> None:
        result = synthesize_world(MAX_SEED, 60, "clear", -0.0, MAX_VERSION)
        self.assertEqual(result["version"], MAX_VERSION)
        self.assertEqual(result["observed_at"], 0.0)
        self.assertEqual(math.copysign(1, result["observed_at"]), -1)
        self.assertFalse(SafetyPolicy().state_has_conflict(parse_world(json.dumps(result).encode())))
        self.assertEqual(synthesize_world(0, 2, observed_at=1)["observed_at"], 1)
        self.assertIs(type(synthesize_world(0, 2, observed_at=1)["observed_at"]), int)

    def test_refuses_malformed_python_parameters(self) -> None:
        invalid = [
            {"seed": -1}, {"seed": MAX_SEED + 1}, {"seed": True},
            {"seed": 1.0}, {"seed": "1"}, {"seed": None},
            {"seed": 0, "aircraft_count": 1}, {"seed": 0, "aircraft_count": 61},
            {"seed": 0, "aircraft_count": True}, {"seed": 0, "aircraft_count": 2.0},
            {"seed": 0, "mode": "not-a-mode"}, {"seed": 0, "mode": 1},
            {"seed": 0, "observed_at": True}, {"seed": 0, "observed_at": "1000"},
            {"seed": 0, "observed_at": math.inf}, {"seed": 0, "observed_at": math.nan},
            {"seed": 0, "observed_at": 10**13},
            {"seed": 0, "version": True}, {"seed": 0, "version": -1},
            {"seed": 0, "version": MAX_VERSION + 1},
        ]
        for case in invalid:
            with self.subTest(case=case), self.assertRaises(ValueError):
                synthesize_world(**case)

    def test_cli_json_is_byte_reproducible_and_native_admitted(self) -> None:
        args = ("--seed", "71", "--aircraft-count", "6", "--mode", "clear", "--observed-at", "-0.0")
        a = launch(*args)
        b = launch(*args)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)
        self.assertEqual(a.stderr, "")
        self.assertTrue(a.stdout.endswith("\n"))
        self.assertEqual(a.stdout.count("\n"), 1)
        world = parse_world(a.stdout.encode("utf-8"))
        self.assertFalse(SafetyPolicy().state_has_conflict(world))
        self.assertEqual(math.copysign(1, world.observed_at), -1)

    @unittest.skipUnless(PLANNER.exists(), "requires full repository native planner")
    def test_foreign_cwd_and_native_planner_consumer(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            generated = launch("--seed", "123", "--mode", "encounter", cwd=td)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            plan = subprocess.run(
                [sys.executable, "-B", str(PLANNER), "-"],
                input=generated.stdout, cwd=td,
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(plan.returncode, 0, plan.stderr)
            output = json.loads(plan.stdout)
            self.assertEqual(output["format"], "towerops.world-plan.v1")
            self.assertEqual(output["status"], "options_available")
            self.assertTrue(output["proposal_only"])
            self.assertEqual(set(output["conflicting_aircraft"]), {"SYN00", "SYN01"})

    def test_argument_errors_produce_no_normal_output(self) -> None:
        bad_args = [
            (), ("--seed", "no"), ("--seed", "-1"),
            ("--seed", str(MAX_SEED + 1)), ("--seed", "0", "--aircraft-count", "0"),
            ("--seed", "0", "--aircraft-count", "61"),
            ("--seed", "0", "--mode", "bogus"), ("--seed", "0", "--observed-at", "NaN"),
            ("--seed", "0", "--observed-at", "Infinity"),
            ("--seed", "0", "--observed-at", "true"),
            ("--seed", "0", "--version", "9007199254740992"),
            ("--seed", "0", "extra"),
        ]
        for args in bad_args:
            with self.subTest(args=args):
                run = launch(*args)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(run.stdout, "")
                self.assertTrue(run.stderr)

    def test_stdout_failure_reports_error_status(self) -> None:
        class RejectingOutput:
            def write(self, value: str) -> int:
                raise OSError("injected output failure")

            def flush(self) -> None:
                return None

            def close(self) -> None:
                return None

        err = io.StringIO()
        with patch.object(sys, "stdout", RejectingOutput()), contextlib.redirect_stderr(err):
            result = main(["--seed", "3"])
        self.assertEqual(result, 2)
        self.assertIn("cannot write world", err.getvalue())

    def test_import_is_quiet_and_help_does_not_synthesize(self) -> None:
        imported = subprocess.run(
            [sys.executable, "-B", "-c", "import synthesize_world"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(imported.stdout, "")
        self.assertEqual(imported.stderr, "")
        help_run = launch("--help")
        self.assertEqual(help_run.returncode, 0)
        self.assertIn("--seed", help_run.stdout)
        self.assertEqual(help_run.stderr, "")


if __name__ == "__main__":
    unittest.main()
