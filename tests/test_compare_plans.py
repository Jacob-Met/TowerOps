"""Native saved-output comparison, admission and real-process receiving."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from compare_plans import MAX_REPORT_BYTES, POLICY_FIELDS, compare_reports, render_text
from plan_world import review_world
from towerops import Advisory, SafetyPolicy

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "compare_plans.py"
PRODUCER = ROOT / "plan_world.py"


def encoded(value: object, *, sort_keys: bool = False) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2,
                       sort_keys=sort_keys) + "\n").encode("utf-8")


def world() -> dict:
    return {"version": 7, "observed_at": 120.0, "aircraft": [
        {"aircraft_id": "EAST", "x_nm": -8.0, "y_nm": 1.0, "altitude_ft": 12000.0,
         "vx_nm_min": 2.0, "vy_nm_min": 0.0, "climb_ft_min": 0.0},
        {"aircraft_id": "WEST", "x_nm": 8.0, "y_nm": 1.0, "altitude_ft": 12000.0,
         "vx_nm_min": -2.0, "vy_nm_min": 0.0, "climb_ft_min": 0.0},
        {"aircraft_id": "FAR", "x_nm": 40.0, "y_nm": 40.0, "altitude_ft": 25000.0,
         "vx_nm_min": 0.0, "vy_nm_min": 0.0, "climb_ft_min": 0.0},
    ]}


def report(*, policy: SafetyPolicy | None = None, value: dict | None = None,
           now: float | None = None) -> dict:
    return review_world(encoded(world() if value is None else value), now, policy)


def rehash(row: dict) -> None:
    body = {key: value for key, value in row.items() if key != "advisory_hash"}
    row["advisory_hash"] = Advisory(**body).advisory_hash


class PlanComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.left = report()
        cls.right = report(policy=replace(SafetyPolicy(), min_horizontal_nm=6.0))
        cls.left_raw = encoded(cls.left)
        cls.right_raw = encoded(cls.right)

    def test_real_policy_change_keeps_complete_records_and_native_menu_order(self):
        left_ids = {row["advisory_hash"] for row in self.left["advisories"]}
        right_ids = {row["advisory_hash"] for row in self.right["advisories"]}
        self.assertTrue(left_ids - right_ids)
        result = compare_reports(self.left_raw, self.right_raw)
        self.assertEqual(result["counts"]["retained"], len(left_ids & right_ids))
        self.assertEqual(result["counts"]["left_only"], len(left_ids - right_ids))
        self.assertEqual(result["counts"]["right_only"], len(right_ids - left_ids))
        self.assertEqual([row["advisory"] for row in result["entries"]
                          if row["left_rank"] is not None], self.left["advisories"])
        for entry in result["entries"]:
            if entry["right_rank"] is not None:
                self.assertEqual(entry["advisory"],
                                 self.right["advisories"][entry["right_rank"] - 1])
        self.assertEqual(result["policy_changes"], [{
            "field": "min_horizontal_nm", "unit": "NM", "left": 5.0, "right": 6.0,
        }])
        self.assertEqual(result["world_hash"], self.left["world_hash"])

    def test_policy_change_does_not_imply_a_changed_menu(self):
        relaxed = report(policy=replace(SafetyPolicy(), min_horizontal_nm=3.0))
        result = compare_reports(self.left_raw, encoded(relaxed))
        self.assertEqual(result["counts"], {
            "retained": len(self.left["advisories"]), "left_only": 0,
            "right_only": 0, "rank_changed": 0,
        })
        self.assertEqual(len(result["policy_changes"]), 1)
        self.assertNotEqual(result["left"]["report_sha256"], result["right"]["report_sha256"])

    def test_reversing_inputs_keeps_new_rows_in_their_saved_right_order(self):
        result = compare_reports(self.right_raw, self.left_raw)
        added = [entry for entry in result["entries"] if entry["membership"] == "right_only"]
        self.assertTrue(added)
        self.assertEqual([entry["right_rank"] for entry in added],
                         sorted(entry["right_rank"] for entry in added))
        for entry in added:
            self.assertIsNone(entry["left_rank"])
            self.assertEqual(entry["advisory"], self.left["advisories"][entry["right_rank"] - 1])
        self.assertEqual(result["counts"]["left_only"], 0)

    def test_saved_priority_changes_are_not_hidden_by_set_comparison(self):
        other = copy.deepcopy(self.left)
        other["advisories"].reverse()
        result = compare_reports(self.left_raw, encoded(other))
        self.assertEqual(result["counts"]["retained"], len(other["advisories"]))
        self.assertEqual(result["counts"]["left_only"] + result["counts"]["right_only"], 0)
        self.assertGreater(result["counts"]["rank_changed"], 0)
        self.assertEqual(result["entries"][0]["left_rank"], 1)
        self.assertEqual(result["entries"][0]["right_rank"], len(other["advisories"]))
        self.assertEqual(result["policy_changes"], [])

    def test_actual_empty_outcomes_remain_explicit(self):
        short = report(policy=replace(SafetyPolicy(), horizon_min=0.1))
        result = compare_reports(self.left_raw, encoded(short))
        self.assertEqual(result["right"]["status"], "no_conflict")
        self.assertEqual(result["right"]["candidate_count"], 0)
        self.assertEqual(result["counts"]["left_only"], len(self.left["advisories"]))
        self.assertIsNone(result["right"]["first_advisory_hash"])
        coincident = world()
        coincident["aircraft"] = [
            {**coincident["aircraft"][0], "aircraft_id": identity, "x_nm": 0.0, "y_nm": 0.0}
            for identity in ("ONE", "TWO")
        ]
        unavailable = report(value=coincident)
        self.assertEqual(unavailable["status"], "no_admitted_option")
        result = compare_reports(encoded(unavailable), encoded(unavailable))
        self.assertEqual(result["counts"], {
            "retained": 0, "left_only": 0, "right_only": 0, "rank_changed": 0,
        })
        self.assertEqual(result["left"]["status"], "no_admitted_option")
        empty = report(value={"version": 0, "observed_at": 0, "aircraft": []})
        self.assertEqual(compare_reports(encoded(empty), encoded(empty))["entries"], [])

    def test_changed_world_identity_is_refused_even_for_equal_numeric_values(self):
        variants = []
        changed = world()
        changed["version"] += 1
        variants.append(changed)
        changed = world()
        changed["observed_at"] = 119.0
        variants.append(changed)
        changed = world()
        changed["aircraft"][0]["aircraft_id"] = "East"
        variants.append(changed)
        changed = world()
        changed["aircraft"][0]["x_nm"] = -8
        variants.append(changed)
        changed = world()
        changed["aircraft"][0]["vy_nm_min"] = -0.0
        variants.append(changed)
        for changed in variants:
            with self.subTest(world=changed):
                other = report(value=changed, now=120.0)
                with self.assertRaisesRegex(ValueError, "different exact native worlds"):
                    compare_reports(self.left_raw, encoded(other))

    def test_exact_review_clock_keeps_integer_float_and_signed_zero_identity(self):
        for now in (121.0, 120):
            with self.subTest(now=repr(now)):
                other = report(now=now)
                with self.assertRaisesRegex(ValueError, "different exact native review clocks"):
                    compare_reports(self.left_raw, encoded(other))
        empty = {"version": 0, "observed_at": 0.0, "aircraft": []}
        positive = report(value=empty, now=0.0)
        negative = report(value=empty, now=-0.0)
        with self.assertRaisesRegex(ValueError, "different exact native review clocks"):
            compare_reports(encoded(positive), encoded(negative))

    def test_file_formatting_and_native_world_order_keep_both_source_identities(self):
        raw = encoded(world())
        other_raw = encoded(world(), sort_keys=True)
        self.assertNotEqual(raw, other_raw)
        other = review_world(other_raw)
        other["world"]["aircraft"].reverse()
        other_bytes = encoded(other, sort_keys=True)
        result = compare_reports(self.left_raw, other_bytes)
        self.assertEqual(result["world_hash"], self.left["world_hash"])
        self.assertEqual(result["counts"]["retained"], len(self.left["advisories"]))
        self.assertNotEqual(result["left"]["reported_input_sha256"],
                            result["right"]["reported_input_sha256"])
        self.assertEqual(result["left"]["report_sha256"], hashlib.sha256(self.left_raw).hexdigest())
        self.assertEqual(result["right"]["report_sha256"], hashlib.sha256(other_bytes).hexdigest())
        self.assertEqual([row["aircraft_id"] for row in result["world"]["aircraft"]],
                         ["EAST", "FAR", "WEST"])

    def test_policy_numeric_representation_is_a_visible_saved_difference(self):
        integer = report(policy=replace(SafetyPolicy(), min_horizontal_nm=5))
        result = compare_reports(self.left_raw, encoded(integer))
        self.assertEqual(len(result["policy_changes"]), 1)
        change = result["policy_changes"][0]
        self.assertIs(type(change["left"]), float)
        self.assertIs(type(change["right"]), int)
        self.assertEqual(result["counts"]["left_only"] + result["counts"]["right_only"], 0)

    def test_full_advisory_identity_is_not_replaced_by_maneuver_or_rounded_numbers(self):
        for field, value in (("rationale", "Literal e\u0301 / \u00e9\nsaved rationale"),
                             ("set_climb_ft_min", -0.0), ("expires_at", 129.0)):
            with self.subTest(field=field):
                other = copy.deepcopy(self.left)
                other["advisories"][0][field] = value
                rehash(other["advisories"][0])
                result = compare_reports(self.left_raw, encoded(other))
                self.assertEqual(result["counts"]["left_only"], 1)
                self.assertEqual(result["counts"]["right_only"], 1)
                added = next(row for row in result["entries"] if row["membership"] == "right_only")
                self.assertEqual(added["advisory"], other["advisories"][0])
                if field == "set_climb_ft_min":
                    self.assertEqual(math.copysign(1, added["advisory"][field]), -1)

    def test_consumer_never_calls_planning_or_screening(self):
        targets = (
            "plan_world.review_world",
            "advisory_options.review_advisory_options",
            "towerops.AdvisoryPlanner.plan",
            "towerops.AdvisoryPlanner._maneuver_candidates",
            "towerops.SafetyPolicy.conflicting_aircraft",
            "towerops.ControlRoom.screen_batch",
        )
        managers = [patch(target, side_effect=AssertionError("planning must not run"))
                    for target in targets]
        for manager in managers:
            manager.start()
            self.addCleanup(manager.stop)
        result = compare_reports(self.left_raw, self.right_raw)
        self.assertGreater(result["counts"]["retained"], 0)

    def test_hashes_bind_complete_world_and_advisory_bodies_and_duplicates_refuse(self):
        variants = []
        changed = copy.deepcopy(self.left)
        changed["world_hash"] = "0" * 64
        variants.append(changed)
        changed = copy.deepcopy(self.left)
        changed["world"]["version"] += 1
        variants.append(changed)
        changed = copy.deepcopy(self.left)
        changed["advisories"][-1]["advisory_hash"] = "0" * 64
        variants.append(changed)
        changed = copy.deepcopy(self.left)
        changed["advisories"][-1]["world_hash"] = "f" * 64
        variants.append(changed)
        changed = copy.deepcopy(self.left)
        changed["advisories"][-1]["set_vx_nm_min"] += 0.001
        variants.append(changed)
        changed = copy.deepcopy(self.left)
        changed["advisories"].append(copy.deepcopy(changed["advisories"][0]))
        changed["candidate_count"] += 1
        variants.append(changed)
        changed = copy.deepcopy(self.left)
        changed["advisories"][-1]["issued_at"] = 120
        rehash(changed["advisories"][-1])
        variants.append(changed)
        for index, changed in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                compare_reports(self.left_raw, encoded(changed))

    def test_complete_report_policy_world_and_advisory_shapes_are_required(self):
        for section in (None, "policy", "world"):
            original = self.left if section is None else self.left[section]
            for field in original:
                with self.subTest(section=section, field=field):
                    changed = copy.deepcopy(self.left)
                    target = changed if section is None else changed[section]
                    del target[field]
                    with self.assertRaises(ValueError):
                        compare_reports(self.left_raw, encoded(changed))
            changed = copy.deepcopy(self.left)
            target = changed if section is None else changed[section]
            target["unexpected"] = "not part of v1"
            with self.subTest(section=section, extra=True), self.assertRaises(ValueError):
                compare_reports(self.left_raw, encoded(changed))
        for field in self.left["advisories"][0]:
            changed = copy.deepcopy(self.left)
            del changed["advisories"][-1][field]
            with self.subTest(advisory=field), self.assertRaises(ValueError):
                compare_reports(self.left_raw, encoded(changed))

    def test_recorded_flags_status_counts_and_identity_lists_are_not_coerced(self):
        for key, value in (
            ("format", "towerops.world-plan.v2"),
            ("simulation_only", 1), ("proposal_only", False),
            ("input_sha256", "A" * 64), ("candidate_count", True),
            ("candidate_count", -1), ("candidate_count", 0),
            ("advisories", {}), ("conflicting_aircraft", ["EAST", "EAST"]),
            ("conflicting_aircraft", ["ABSENT"]), ("conflicting_aircraft", [[]]),
            ("status", "no_conflict"), ("status", "no_admitted_option"),
            ("status", "unknown"),
        ):
            changed = copy.deepcopy(self.left)
            changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                compare_reports(self.left_raw, encoded(changed))
        for value in (True, "5", 0.0, -0.0, 1e-7, 1e13):
            changed = copy.deepcopy(self.left)
            changed["policy"]["min_horizontal_nm"] = value
            with self.subTest(policy=value), self.assertRaises(ValueError):
                compare_reports(self.left_raw, encoded(changed))

    def test_malformed_json_duplicate_fields_unicode_depth_and_size_refuse(self):
        raw_variants = [
            b"\xff", b"", b"null", b"[]",
            self.left_raw.replace(b'"format":', b'"format":"towerops.world-plan.v1","format":', 1),
            b"[" * 2000 + b"0" + b"]" * 2000,
            self.left_raw.replace(b'"reviewed_at": 120.0', b'"reviewed_at": 1e999'),
        ]
        nonfinite = copy.deepcopy(self.left)
        nonfinite["candidate_count"] = float("nan")
        raw_variants.append(json.dumps(nonfinite).encode("ascii"))
        changed = copy.deepcopy(self.left)
        changed["advisories"][-1]["rationale"] = "\ud800"
        raw_variants.append(json.dumps(changed).encode("ascii"))
        for index, raw in enumerate(raw_variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                compare_reports(self.left_raw, raw)
        boundary = self.left_raw + b" " * (MAX_REPORT_BYTES - len(self.left_raw))
        self.assertEqual(compare_reports(boundary, self.left_raw)["counts"]["retained"],
                         len(self.left["advisories"]))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            compare_reports(boundary + b" ", self.left_raw)

    def test_native_maximum_clock_expiry_and_literal_text_remain_readable(self):
        large_world = world()
        large_world["observed_at"] = 1_000_000_000_000
        large = report(value=large_world)
        result = compare_reports(encoded(large), encoded(large))
        self.assertEqual(result["entries"][0]["advisory"]["expires_at"], 1_000_000_000_008.0)
        other = copy.deepcopy(self.left)
        literal = "Literal e\u0301 / \u00e9 / \u2728\n\t\x1b[31m\x00\u202e"
        other["advisories"][0]["rationale"] = literal
        rehash(other["advisories"][0])
        result = compare_reports(encoded(other), encoded(other))
        text = render_text(result, "left\n\x1b[31m.json", "right.json")
        self.assertTrue(text.isascii())
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\x00", text)
        self.assertIn("\\u0301", text)
        self.assertIn("\\u00e9", text)
        self.assertEqual(json.loads(json.dumps(result))["entries"][0]["advisory"]["rationale"], literal)
        for field in POLICY_FIELDS:
            self.assertIn(field, text)
        for value in (result["world_hash"], result["left"]["report_sha256"],
                      result["right"]["reported_input_sha256"],
                      result["entries"][0]["advisory"]["advisory_hash"]):
            self.assertIn(value, text)


class ComparePlansCLI(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="towerops-plan-comparison-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.world_path = self.root / "world.json"
        self.left_path = self.root / "left.json"
        self.right_path = self.root / "right.json"
        self.world_path.write_bytes(encoded(world()))
        for path, arguments in ((self.left_path, []),
                                (self.right_path, ["--horizontal-nm", "6"])):
            produced = subprocess.run(
                [sys.executable, "-B", str(PRODUCER), str(self.world_path), *arguments],
                capture_output=True, timeout=10, check=False,
            )
            self.assertEqual(produced.returncode, 0, produced.stderr.decode(errors="replace"))
            self.assertEqual(produced.stderr, b"")
            path.write_bytes(produced.stdout)
        self.before = {path: path.read_bytes() for path in
                       (self.world_path, self.left_path, self.right_path)}
        self.addCleanup(self.check_input_custody)

    def check_input_custody(self):
        for path, before in self.before.items():
            self.assertEqual(path.read_bytes(), before)

    def invoke(self, *arguments, **kwargs):
        return subprocess.run(
            [sys.executable, "-B", str(CLI), *(str(value) for value in arguments)],
            stdin=subprocess.DEVNULL, capture_output=True,
            timeout=10, check=False, **kwargs,
        )

    def test_actual_native_producer_reports_reach_text_and_complete_json(self):
        text = self.invoke(self.left_path, self.right_path)
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertEqual(text.stderr, b"")
        self.assertIn(b"TowerOps saved policy comparison", text.stdout)
        native_policy = json.loads(self.before[self.right_path])["policy"]["min_horizontal_nm"]
        self.assertIs(type(native_policy), int)
        self.assertEqual(native_policy, 6)
        self.assertIn(b"min_horizontal_nm (NM): 5.0 -> 6\n", text.stdout)
        result = self.invoke(self.left_path, self.right_path, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["format"], "towerops.plan-comparison.v1")
        self.assertGreater(document["counts"]["left_only"], 0)
        self.assertGreater(document["counts"]["retained"], 0)
        self.assertEqual(document["counts"]["right_only"], 0)
        self.assertEqual(document["left"]["report_sha256"],
                         hashlib.sha256(self.before[self.left_path]).hexdigest())
        left = json.loads(self.before[self.left_path])
        self.assertEqual([entry["advisory"] for entry in document["entries"]
                          if entry["left_rank"] is not None], left["advisories"])

    def test_read_only_and_identical_direct_file_inputs_are_supported(self):
        self.left_path.chmod(0o444)
        result = self.invoke("--json", self.left_path, self.left_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["counts"]["left_only"] + value["counts"]["right_only"], 0)
        self.assertEqual(value["sources"]["left"], value["sources"]["right"])

    def test_invalid_late_right_row_leaves_stdout_empty_and_inputs_intact(self):
        value = json.loads(self.before[self.right_path])
        value["advisories"][-1]["advisory_hash"] = "0" * 64
        bad = self.root / "late-invalid.json"
        bad.write_bytes(encoded(value))
        original = bad.read_bytes()
        result = self.invoke(self.left_path, bad, "--json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"Right report", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertEqual(bad.read_bytes(), original)

    def test_incompatible_saved_clock_is_an_error_not_an_empty_diff(self):
        other = self.root / "other-clock.json"
        other.write_bytes(encoded(report(now=121.0)))
        result = self.invoke(self.left_path, other)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"different exact native review clocks", result.stderr)

    def test_oversized_regular_file_is_refused_before_json_output(self):
        huge = self.root / "oversized.json"
        with huge.open("wb") as stream:
            stream.seek(MAX_REPORT_BYTES)
            stream.write(b" ")
        before = huge.stat().st_size
        result = self.invoke(self.left_path, huge)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"exceeds", result.stderr)
        self.assertEqual(huge.stat().st_size, before)

    def test_missing_directory_symlink_and_fifo_inputs_refuse_without_blocking(self):
        paths = [self.root / "missing.json", self.root]
        if hasattr(os, "symlink"):
            link = self.root / "linked.json"
            link.symlink_to(self.left_path)
            paths.append(link)
        if hasattr(os, "mkfifo"):
            fifo = self.root / "report.fifo"
            os.mkfifo(fifo)
            paths.append(fifo)
        for path in paths:
            with self.subTest(path=path.name):
                result = self.invoke(path, self.right_path)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertNotIn(b"Traceback", result.stderr)

    def test_argument_refusals_and_help_do_not_need_input_files(self):
        missing = self.root / "no-such-file.json"
        result = self.invoke("--help", missing, missing)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"Compare saved TowerOps policy experiments", result.stdout)
        for arguments in ((), (missing,), ("--unsupported", missing, missing)):
            with self.subTest(arguments=arguments):
                result = self.invoke(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertNotIn(b"Traceback", result.stderr)
        self.assertFalse(missing.exists())

    def test_closed_stdout_pipe_is_reported_as_failed_output(self):
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            result = subprocess.run(
                [sys.executable, "-B", str(CLI), str(self.left_path), str(self.right_path), "--json"],
                stdin=subprocess.DEVNULL, stdout=write_fd, stderr=subprocess.PIPE,
                timeout=10, check=False,
            )
        finally:
            os.close(write_fd)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(b"cannot write comparison", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)


def test_frozen_independent_receiving(tmp_path, capsys):
    """Run immutable producer-grounded controls through ordinary pytest."""
    packet = ROOT / "docs/qualification/plan-compare-ultra-1b3276062063/independent"
    frozen_hashes = {
        "independent_compare.py": "8b143a918ad29210226831c8247f69bb106862301993651992aa562eea9bba44",
        "producer_fixture_builder.py": "68181c1eecda7c89baafc6e320dbbef84fed732fde5ba2adcf2cbb0f6f3fadbc",
        "fixtures.json.zlib.b64": "fff05a419792411a8176658991a7db7a8ddde9f44976620b09aa67e95db335dd",
        "PRE_CANDIDATE.json": "4b69bf7aa1e3e63de6b04f4a50cd159c06cadf91dc172a7eafb3a7d9040c15c7",
        "CLOUD_API_RECEIVING.json": "667a3954198b808e73873ede3154c1b7b2824d553568b1cb51b4c9ba276beb76",
        "CLOUD_METADATA_PROBE_FAILURE.log": "ad703f9006abd72e512e96aee9af2898965172195b76a39a01ce36b472321cd0",
        "MAC_API_UNOBSERVED.json": "684e3ed871df0da94bc50c32fce6a0c8d6478ae7d7cb1af6c394893d0791a43d",
        "REVIEW.md": "cba143d251f54b201cba044d76f0249cf3a39f12d7cff3d7a025c1105635cf00",
    }
    for name, expected in frozen_hashes.items():
        raw = (packet / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, name

    work = tmp_path / "independent-receiving"
    assert not work.exists()
    command = [
        sys.executable, "-B", str(packet / "independent_compare.py"),
        "--source", str(CLI), "--fixtures", str(packet / "fixtures.json.zlib.b64"),
        "--work", str(work),
    ]
    failure = None
    try:
        process = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True,
            timeout=180, check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b"", error.stderr or b""
        failure = "Independent receiving exceeded its 180-second process bound."
        exit_code = None
    else:
        stdout, stderr = process.stdout, process.stderr
        exit_code = process.returncode

    def archived(name, data):
        return {
            "path": name, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "base64": base64.b64encode(data).decode("ascii"),
        }

    files = [archived("harness.stdout", stdout), archived("harness.stderr", stderr)]
    receipt_bytes = None
    if work.exists():
        for path in sorted(work.iterdir()):
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            if path.name != "RECEIVING.json" and path.suffix not in {".stdout", ".stderr"}:
                continue
            data = path.read_bytes()
            files.append(archived(path.name, data))
            if path.name == "RECEIVING.json":
                receipt_bytes = data
    archive = json.dumps(
        {"format": "towerops.independent-raw-output.v1", "files": files},
        ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    compressed = zlib.compress(archive, level=9)
    envelope = {
        "format": "towerops.independent-log-archive.v1",
        "encoding": "base64(zlib(JSON UTF-8))",
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "compressed_bytes": len(compressed),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "base64": base64.b64encode(compressed).decode("ascii"),
    }
    with capsys.disabled():
        print("\nTOWEROPS_INDEPENDENT_RECEIVING_JSON_BEGIN")
        if receipt_bytes is None:
            print(json.dumps({"receipt_unavailable": True, "exit": exit_code}))
        else:
            print(receipt_bytes.decode("utf-8"), end="")
        print("TOWEROPS_INDEPENDENT_RECEIVING_JSON_END")
        print("TOWEROPS_INDEPENDENT_RAW_ARCHIVE_BEGIN")
        print(json.dumps(envelope, sort_keys=True))
        print("TOWEROPS_INDEPENDENT_RAW_ARCHIVE_END", flush=True)

    assert failure is None, failure
    assert exit_code == 0, stderr.decode("utf-8", "replace")
    assert receipt_bytes is not None
    receipt = json.loads(receipt_bytes)
    assert receipt["format"] == "towerops.independent-comparison-receiving.v1"
    assert receipt["passed"] is True
    assert receipt["source_unchanged"] is True
    assert receipt["source_sha256"] == hashlib.sha256(CLI.read_bytes()).hexdigest()
    assert receipt["api"]["case_count"] == 27
    assert receipt["api"]["passed"] is True
    assert receipt["cli"]["case_count"] == 22
    assert receipt["cli"]["process_count"] == 22
    assert receipt["cli"]["passed"] is True

if __name__ == "__main__":
    unittest.main()
