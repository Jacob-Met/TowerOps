"""Ordinary saved-row summary contracts; no planner or geometry campaign."""

from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import review_saved_plan as reader
from towerops import Advisory, Aircraft, WorldState


def saved_report(*, with_rows=True, empty=False):
    """Authored recorded data, with native identity hashes but no screening."""
    aircraft = () if empty else tuple(
        Aircraft(identity, index * 10, 0, 4000, 1, 0, 0)
        for index, identity in enumerate(("ALPHA", "BETA", "ZERO"))
    )
    world = WorldState(4, -0.0, aircraft)
    rows = []
    if with_rows and not empty:
        for identity, vx in (("BETA", 2), ("ALPHA", -0.0), ("BETA", 3.0)):
            advisory = Advisory(identity, world.world_hash, vx, 0, 0, -0.0, 8.0, "Authored saved row")
            rows.append({**asdict(advisory), "advisory_hash": advisory.advisory_hash})
    return {
        "format": "towerops.world-plan.v1",
        "simulation_only": True,
        "proposal_only": True,
        "input_sha256": "a" * 64,
        "world": world.to_dict(),
        "world_hash": world.world_hash,
        "reviewed_at": -0.0,
        "policy": {
            "min_horizontal_nm": 5,
            "min_vertical_ft": 1000.0,
            "horizon_min": 4,
            "sample_step_min": 0.25,
            "max_state_age_sec": 15,
            "max_speed_nm_min": 6.0,
            "max_climb_ft_min": 3000,
        },
        "status": "no_conflict" if empty else ("options_available" if with_rows else "no_admitted_option"),
        "conflicting_aircraft": [] if empty else ["BETA", "ALPHA", "ZERO"],
        "candidate_count": 0 if empty else 7,
        "advisories": rows,
    }


def encoded(report):
    return (json.dumps(report, ensure_ascii=True, indent=2) + "\n").encode()


class SavedPlanSummaryTests(unittest.TestCase):
    def test_literal_group_order_zero_and_recorded_candidate_count(self):
        raw = encoded(saved_report())
        result = reader.summarize_report(raw)
        self.assertEqual(result["counts"], {"aircraft": 3, "conflicting_aircraft": 3, "saved_alternatives": 3})
        self.assertEqual(result["saved_alternative_counts"], [
            {"aircraft_id": "BETA", "count": 2},
            {"aircraft_id": "ALPHA", "count": 1},
            {"aircraft_id": "ZERO", "count": 0},
        ])
        self.assertEqual(result["recorded"]["candidate_count"], 7)
        self.assertEqual(result["recorded"]["conflicting_aircraft"], ["BETA", "ALPHA", "ZERO"])
        self.assertNotIn("first_advisory_hash", result)
        self.assertNotIn("source_path", result)
        self.assertEqual(result["validation"], "internal_consistency_only")

    def test_both_empty_outcomes_are_completed_recorded_summaries(self):
        for report in (saved_report(empty=True), saved_report(with_rows=False)):
            result = reader.summarize_report(encoded(report))
            self.assertEqual(result["recorded"]["status"], report["status"])
            self.assertEqual(result["counts"]["saved_alternatives"], 0)
            self.assertTrue(all(row["count"] == 0 for row in result["saved_alternative_counts"]))

    def test_every_policy_value_and_numeric_representation_survives(self):
        report = saved_report()
        result = reader.summarize_report(encoded(report))
        self.assertEqual(json.dumps(result["policy"]), json.dumps(report["policy"]))
        self.assertEqual(json.dumps(result["recorded"]["observed_at"]), "-0.0")
        self.assertEqual(json.dumps(result["recorded"]["reviewed_at"]), "-0.0")
        self.assertIs(type(result["recorded"]["version"]), int)

    def test_raw_identity_changes_when_only_serialization_changes(self):
        report = saved_report()
        first = encoded(report)
        second = json.dumps(report, separators=(",", ":")).encode()
        summaries = [reader.summarize_report(raw) for raw in (first, second)]
        for raw, summary in zip((first, second), summaries, strict=True):
            self.assertEqual(summary.pop("report_bytes"), len(raw))
            self.assertEqual(summary.pop("report_sha256"), hashlib.sha256(raw).hexdigest())
        self.assertEqual(summaries[0], summaries[1])

    def test_no_planner_or_screening_execution(self):
        raw = encoded(saved_report())
        with patch("plan_world.review_world", side_effect=AssertionError("planner called")), \
             patch("advisory_options.review_advisory_options", side_effect=AssertionError("planner called")), \
             patch("towerops.SafetyPolicy.conflicting_aircraft", side_effect=AssertionError("screening called")):
            self.assertEqual(reader.summarize_report(raw)["counts"]["saved_alternatives"], 3)

    def test_plain_sheet_literal_limits_and_complete_policy(self):
        result = reader.summarize_report(encoded(saved_report()))
        result["source_path"] = 'saved "review"\n\u03bb.json'
        text = reader.render_text(result)
        self.assertTrue(text.startswith('TowerOps recorded plan summary\nRecorded status: "options_available"\nRecorded review time (synthetic sec): -0.0\n'))
        self.assertIn('Source path: "saved \\"review\\"\\n\\u03bb.json"', text)
        self.assertTrue(text.isascii())
        self.assertIn('  "ZERO": 0\n', text)
        for field, unit in zip(reader.POLICY_FIELDS, reader.POLICY_UNITS, strict=True):
            self.assertIn(f"  {field} ({unit}): {json.dumps(result['policy'][field])}\n", text)
        self.assertIn("candidate-menu completeness or safety approval.", text)
        self.assertIn("not as a simultaneous batch.", text)

    def test_cli_json_and_plain_read_same_file_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saved report.json"
            raw = encoded(saved_report())
            path.write_bytes(raw)
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            for extra in (["--json"], []):
                out, err = io.StringIO(), io.StringIO()
                with patch("sys.stdout", out), patch("sys.stderr", err):
                    self.assertEqual(reader.main([str(path), *extra]), 0)
                self.assertEqual(err.getvalue(), "")
                if extra:
                    result = json.loads(out.getvalue())
                    self.assertEqual(result["source_path"], str(path))
                    self.assertEqual(result["counts"]["saved_alternatives"], 3)
                else:
                    self.assertIn("Saved alternative count: 3\n", out.getvalue())
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)


if __name__ == "__main__":
    unittest.main()
