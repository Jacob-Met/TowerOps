"""Real native-module and process receiving for the custom-world CLI."""

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

from advisory_options import review_advisory_options
from plan_world import (
    MAX_ABS_NUMBER,
    MAX_AIRCRAFT,
    MAX_VERSION,
    MAX_WORLD_BYTES,
    MIN_POLICY_VALUE,
    parse_world,
    review_world,
)
from towerops import AdvisoryPlanner, Aircraft, GateRejected, SafetyPolicy, WorldState

CLI = Path(__file__).resolve().parents[1] / "plan_world.py"


def make_world() -> dict:
    return WorldState(7, 120.0, (
        Aircraft("EAST", -8.0, 1.0, 12000.0, 2.0, 0.0),
        Aircraft("WEST", 8.0, 1.0, 12000.0, -2.0, 0.0),
        Aircraft("FAR", 40.0, 40.0, 25000.0, 0.0, 0.0),
    )).to_dict()


def encoded(world: dict | None = None) -> bytes:
    return (json.dumps(make_world() if world is None else world, indent=2) + "\n").encode()


def native_options(state: WorldState, now: float, policy: SafetyPolicy) -> list[dict]:
    return [
        {**asdict(advisory), "advisory_hash": advisory.advisory_hash}
        for advisory in review_advisory_options(state, now, policy).advisories
    ]


class WorldPlanReceiving(unittest.TestCase):
    def test_complete_native_menu_order_bodies_and_hashes_are_retained(self):
        raw = encoded()
        state = parse_world(raw)
        policy = SafetyPolicy()
        expected = review_advisory_options(state, 120.0, policy)
        result = review_world(raw)
        self.assertEqual(result["format"], "towerops.world-plan.v1")
        self.assertEqual(result["status"], "options_available")
        self.assertEqual(result["candidate_count"], expected.candidate_count)
        self.assertEqual(result["advisories"], native_options(state, 120.0, policy))
        self.assertGreater(len(result["advisories"]), 1)
        self.assertEqual(result["advisories"][0]["advisory_hash"],
                         AdvisoryPlanner(policy).plan(state, 120.0)[0].advisory_hash)
        self.assertEqual(result["conflicting_aircraft"], ["EAST", "WEST"])
        self.assertNotIn("FAR", {row["aircraft_id"] for row in result["advisories"]})
        self.assertEqual(result["world"], state.to_dict())
        self.assertEqual(result["world_hash"], state.world_hash)
        self.assertEqual(result["input_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["policy"], asdict(policy))
        self.assertIs(result["simulation_only"], True)
        self.assertIs(result["proposal_only"], True)
        self.assertNotIn("approval", result)
        self.assertNotIn("audit_events", result)
        self.assertEqual(encoded(), raw)

    def test_empty_singleton_and_separated_worlds_need_no_advisory(self):
        base = make_world()
        for aircraft in ([], [base["aircraft"][0]], [base["aircraft"][0], base["aircraft"][1]]):
            # Native to_dict sorts EAST, FAR, WEST, so EAST/FAR is separated.
            world = {**base, "aircraft": aircraft}
            result = review_world(encoded(world))
            self.assertEqual(result["status"], "no_conflict")
            self.assertEqual(result["candidate_count"], 0)
            self.assertEqual(result["conflicting_aircraft"], [])
            self.assertEqual(result["advisories"], [])

    def test_conflicted_world_without_an_admitted_option_is_distinct(self):
        world = make_world()
        world["aircraft"] = [
            {**world["aircraft"][0], "aircraft_id": identity, "x_nm": 0.0, "y_nm": 0.0}
            for identity in ("ONE", "TWO")
        ]
        result = review_world(encoded(world))
        self.assertEqual(result["status"], "no_admitted_option")
        self.assertEqual(result["conflicting_aircraft"], ["ONE", "TWO"])
        self.assertGreater(result["candidate_count"], 0)
        self.assertEqual(result["advisories"], [])

    def test_native_case_numeric_types_and_negative_zero_are_not_normalized(self):
        world = make_world()
        world["observed_at"] = 120
        world["aircraft"][0]["aircraft_id"] = "a"
        world["aircraft"][2]["aircraft_id"] = "A"
        world["aircraft"][0]["y_nm"] = -0.0
        raw = encoded(world)
        state = parse_world(raw)
        result = review_world(raw)
        self.assertEqual({a.aircraft_id for a in state.aircraft}, {"a", "A", "FAR"})
        self.assertIs(type(result["reviewed_at"]), int)
        self.assertIs(type(state.get("a").x_nm), float)
        self.assertEqual(math.copysign(1, state.get("a").y_nm), -1)
        self.assertEqual(result["advisories"], native_options(state, 120, SafetyPolicy()))
        self.assertEqual(result["world_hash"], state.world_hash)

    def test_policy_and_review_clock_use_the_original_native_gate(self):
        raw = encoded()
        state = parse_world(raw)
        policy = replace(SafetyPolicy(), min_horizontal_nm=3, min_vertical_ft=800, horizon_min=4)
        result = review_world(raw, 125, policy)
        self.assertEqual(result["policy"], asdict(policy))
        self.assertEqual(result["reviewed_at"], 125)
        self.assertEqual(result["advisories"], native_options(state, 125, policy))
        short = review_world(raw, policy=replace(policy, horizon_min=0.1))
        self.assertEqual(short["status"], "no_conflict")
        self.assertEqual(short["advisories"], [])

    def test_stale_future_and_exact_freshness_boundary_keep_native_reasons(self):
        for raw in (encoded(), encoded({"version": 0, "observed_at": 120, "aircraft": []})):
            self.assertIn(review_world(raw, 130)["status"], ("options_available", "no_conflict"))
            for now, reason in ((119, "future_state"), (130.001, "stale_state")):
                with self.assertRaises(GateRejected) as caught:
                    review_world(raw, now)
                self.assertEqual(caught.exception.reason, reason)

    def test_complete_world_and_aircraft_shapes_are_required(self):
        world = make_world()
        invalid = [None, [], {**world, "policy": {}}, {k: v for k, v in world.items() if k != "version"}]
        for entry in (None, [], {"aircraft_id": "ONLY"}, {**world["aircraft"][0], "ignored": 1}):
            invalid.append({**world, "aircraft": [entry]})
        for value in invalid:
            with self.assertRaises(ValueError):
                parse_world(json.dumps(value).encode())

    def test_version_is_a_bounded_json_integer(self):
        for version in (0, MAX_VERSION):
            self.assertEqual(parse_world(encoded({**make_world(), "version": version})).version, version)
        for version in (-1, True, False, 1.0, "1", None, MAX_VERSION + 1):
            with self.assertRaisesRegex(ValueError, "version"):
                parse_world(encoded({**make_world(), "version": version}))

    def test_nonfinite_coerced_and_unsupported_numbers_are_refused(self):
        for value in (True, "1", None, float("nan"), float("inf"), -float("inf"), MAX_ABS_NUMBER + 1):
            for field in ("x_nm", "y_nm", "altitude_ft", "vx_nm_min", "vy_nm_min", "climb_ft_min"):
                world = make_world()
                world["aircraft"][0][field] = value
                with self.assertRaises(ValueError):
                    parse_world(encoded(world))
            with self.assertRaises(ValueError):
                parse_world(encoded({**make_world(), "observed_at": value}))
            if value is not None:  # None is the public API's default-clock sentinel.
                with self.assertRaises(ValueError):
                    review_world(encoded(), now=value)

    def test_supported_numeric_boundary_and_policy_range_are_explicit(self):
        world = {"version": 0, "observed_at": MAX_ABS_NUMBER, "aircraft": [
            asdict(Aircraft("BOUND", MAX_ABS_NUMBER, -MAX_ABS_NUMBER, MAX_ABS_NUMBER, 0, 0)),
        ]}
        result = review_world(encoded(world))
        self.assertEqual(result["world"], world)
        self.assertEqual(result["status"], "no_conflict")
        for value in (0, -1, MIN_POLICY_VALUE / 2, True, float("inf"), MAX_ABS_NUMBER + 1):
            with self.assertRaises(ValueError):
                review_world(encoded(), policy=replace(SafetyPolicy(), horizon_min=value))
        with self.assertRaises(TypeError):
            review_world(encoded(), policy={})

    def test_duplicate_fields_and_duplicate_native_ids_are_refused(self):
        for raw in (
            b'{"version":1,"version":2,"observed_at":0,"aircraft":[]}',
            encoded().replace(b'"x_nm": -8.0', b'"x_nm": -8.0, "x_nm": 5'),
        ):
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                parse_world(raw)
        world = make_world()
        world["aircraft"].append(world["aircraft"][0])
        with self.assertRaisesRegex(ValueError, "duplicate aircraft_id"):
            parse_world(encoded(world))

    def test_identity_and_aircraft_count_limits_are_checked(self):
        for identity in ("", "TOO-LONG-ID!", "has space", "x\n", "é", 3, None):
            world = make_world()
            world["aircraft"][0]["aircraft_id"] = identity
            with self.assertRaisesRegex(ValueError, "aircraft_id"):
                parse_world(encoded(world))
        entry = make_world()["aircraft"][0]
        world = {"version": 0, "observed_at": 0, "aircraft": [
            {**entry, "aircraft_id": f"A{i}"} for i in range(MAX_AIRCRAFT)
        ]}
        self.assertEqual(len(parse_world(encoded(world)).aircraft), MAX_AIRCRAFT)
        world["aircraft"].append({**entry, "aircraft_id": "EXTRA"})
        with self.assertRaisesRegex(ValueError, "0 to 60"):
            parse_world(encoded(world))

    def test_malformed_text_and_depth_are_refused_without_repair(self):
        for raw in (b"", b"{", b"\xff", b"\xef\xbb\xbf{}", b"[" * 2000 + b"]" * 2000,
                    b'{"version":0,"observed_at":1e999,"aircraft":[]}'):
            with self.assertRaises(ValueError):
                parse_world(raw)
        with self.assertRaises(TypeError):
            parse_world("{}")

    def test_exact_byte_limit_retains_original_byte_identity(self):
        raw = encoded({"version": 0, "observed_at": 0, "aircraft": []})
        at_limit = raw + b" " * (MAX_WORLD_BYTES - len(raw))
        report = review_world(at_limit)
        self.assertEqual(report["input_sha256"], hashlib.sha256(at_limit).hexdigest())
        with self.assertRaisesRegex(ValueError, "exceeds"):
            review_world(at_limit + b" ")


class WorldPlanProcessReceiving(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="towerops-world-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "world input Ω.json"
        self.raw = encoded()
        self.path.write_bytes(self.raw)

    def run_cli(self, *args, raw: bytes | None = None):
        return subprocess.run(
            [sys.executable, str(CLI), *map(str, args)], input=raw, capture_output=True,
            cwd=self.root, check=False, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def assert_refused(self, result, status: int):
        self.assertEqual(result.returncode, status, result.stderr.decode(errors="replace"))
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"error:", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)

    def test_file_and_stdin_outputs_are_exact_and_input_is_unchanged(self):
        self.path.chmod(0o444)
        file_result = self.run_cli(self.path)
        stdin_result = self.run_cli("-", raw=self.raw)
        self.assertEqual(file_result.returncode, 0, file_result.stderr)
        self.assertEqual(stdin_result.returncode, 0, stdin_result.stderr)
        self.assertEqual(file_result.stderr, b"")
        self.assertEqual(stdin_result.stderr, b"")
        self.assertEqual(file_result.stdout, stdin_result.stdout)
        self.assertEqual(json.loads(file_result.stdout), review_world(self.raw))
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [self.path.name])

    def test_explicit_policy_and_clock_match_the_native_review(self):
        result = self.run_cli(self.path, "--now", "125", "--horizontal-nm", "3",
                              "--vertical-ft", "800", "--horizon-min", "4")
        self.assertEqual(result.returncode, 0, result.stderr)
        policy = replace(SafetyPolicy(), min_horizontal_nm=3, min_vertical_ft=800, horizon_min=4)
        self.assertEqual(json.loads(result.stdout), review_world(self.raw, 125, policy))
        short = self.run_cli(self.path, "--horizon-min", "0.1")
        self.assertEqual(short.returncode, 0, short.stderr)
        self.assertEqual(json.loads(short.stdout)["status"], "no_conflict")

    def test_no_conflict_and_no_option_are_successful_completed_reviews(self):
        world = make_world()
        world["aircraft"] = [{**world["aircraft"][0], "aircraft_id": identity} for identity in ("X", "Y")]
        for raw, status in ((encoded({"version": 0, "observed_at": 0, "aircraft": []}), "no_conflict"),
                            (encoded(world), "no_admitted_option")):
            result = self.run_cli("-", raw=raw)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], status)
            self.assertEqual(report["advisories"], [])

    def test_native_freshness_refusals_have_exit_one_and_no_report(self):
        for now, reason in (("119", b"future_state"), ("130.001", b"stale_state")):
            result = self.run_cli(self.path, "--now", now)
            self.assert_refused(result, 1)
            self.assertIn(reason, result.stderr)
            self.assertEqual(self.path.read_bytes(), self.raw)

    def test_unreadable_and_malformed_inputs_have_exit_two_and_no_report(self):
        for path in (self.root / "missing" / "world.json", self.root):
            self.assert_refused(self.run_cli(path), 2)
        for raw in (b"bad json", b"\xff", b'{"version":0,"observed_at":false,"aircraft":[]}'):
            self.assert_refused(self.run_cli("-", raw=raw), 2)
        self.assertFalse((self.root / "missing").exists())
        self.assertEqual(self.path.read_bytes(), self.raw)

    def test_oversized_file_and_stdin_are_refused_without_source_changes(self):
        oversized = self.raw + b" " * MAX_WORLD_BYTES
        self.path.write_bytes(oversized)
        for result in (self.run_cli(self.path), self.run_cli("-", raw=oversized)):
            self.assert_refused(result, 2)
            self.assertIn(b"exceeds", result.stderr)
        self.assertEqual(self.path.read_bytes(), oversized)

    def test_help_argument_and_policy_refusals_precede_file_access(self):
        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn(b"proposals only", help_result.stdout)
        for args in ((), (self.path, "--unknown"), (self.path, "--now", "true"),
                     (self.path, "--now", "null"),
                     (self.path, "--horizontal-nm", "NaN")):
            self.assert_refused(self.run_cli(*args), 2)
        result = self.run_cli(self.root / "missing.json", "--horizon-min", "0")
        self.assert_refused(result, 2)
        self.assertIn(b"policy.horizon_min", result.stderr)

    @unittest.skipUnless(Path("/dev/full").exists(), "requires the native full-output device")
    def test_output_io_failure_does_not_claim_a_successful_review(self):
        with Path("/dev/full").open("wb") as full:
            result = subprocess.run(
                [sys.executable, str(CLI), str(self.path)], stdout=full,
                stderr=subprocess.PIPE, cwd=self.root, check=False, timeout=30,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"cannot write report", result.stderr)
        self.assertNotIn(b"Exception ignored", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertEqual(self.path.read_bytes(), self.raw)


if __name__ == "__main__":
    unittest.main()
