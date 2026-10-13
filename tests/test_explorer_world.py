"""Bounded consumer tests for the saved Explorer-to-WorldState connector."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from explorer_world import MAX_EXPORT_BYTES, ReplayMismatch, extract_world
from plan_world import parse_world, review_world
from scenarios import SCENARIOS, run_scenario

def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")

class ExplorerWorldTests(unittest.TestCase):
    def command(self, *arguments, data=None, stdout=subprocess.PIPE):
        return subprocess.run([sys.executable, "-B"] + (["-O"] if sys.flags.optimize else [])
                              + [str(ROOT / "explorer_world.py"), *arguments],
                              input=data, stdout=stdout, stderr=subprocess.PIPE, cwd=ROOT,
                              env={})

    def test_all_fixed_scenarios_switches_and_both_worlds_reach_native_consumer(self):
        for name in SCENARIOS:
            for approval in (False, True):
                for ack in (False, True):
                    original = run_scenario(name, approval, ack)
                    raw = encoded(original)
                    for phase in ("before", "after"):
                        with self.subTest(scenario=name, approval=approval, ack=ack, phase=phase):
                            selected = extract_world(raw, phase)
                            self.assertEqual(selected, original[phase])
                            state = parse_world(encoded(selected))
                            self.assertEqual(state.world_hash, original[phase + "_world_hash"])
                            native = review_world(encoded(selected))
                            self.assertEqual(native["world_hash"], state.world_hash)
                            self.assertTrue(native["proposal_only"])
                            self.assertEqual(raw, encoded(original))

    def test_complete_export_is_verified_including_the_unselected_world_and_audit(self):
        good = run_scenario("approved")
        variants = []
        changed = copy.deepcopy(good); changed["after"]["version"] += 1; variants.append(changed)
        changed = copy.deepcopy(good); changed["label"] = "Changed label"; variants.append(changed)
        changed = copy.deepcopy(good); changed["audit_events"][0]["payload"]["scenario"] = "missing_ack"; variants.append(changed)
        changed = copy.deepcopy(good); changed["unrecorded"] = True; variants.append(changed)
        for changed in variants:
            with self.subTest(value=changed):
                with self.assertRaises(ReplayMismatch):
                    extract_world(encoded(changed), "before")

    def test_equivalent_finite_json_numbers_are_preserved_and_results_are_detached(self):
        def integers(value):
            if type(value) is float and value.is_integer():return int(value)
            if isinstance(value, dict):return {k:integers(v) for k,v in value.items()}
            if isinstance(value, list):return [integers(v) for v in value]
            return value
        exported = integers(run_scenario("approved"))
        raw = encoded(exported)
        result = extract_world(raw, "before")
        self.assertIs(type(result["observed_at"]), int)
        result["aircraft"][0]["x_nm"] = 999
        self.assertEqual(extract_world(raw, "before"), exported["before"])

    def test_invalid_carriers_formats_encoding_and_duplicate_fields_refuse(self):
        for phase in ("", "BEFORE", None, 1, []):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                extract_world(b"{}", phase)
        with self.assertRaises(TypeError):extract_world("{}", "before")
        for raw in (b"[]", b"{}", b"null", b"{", b"\xff",
                    b'{"format":"x","format":"towerops.synthetic-explorer.v1"}',
                    b'{"value":NaN}', b'{"value":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, TypeError)):
                extract_world(raw, "before")

    def test_exact_export_size_limit_including_whitespace(self):
        raw = encoded(run_scenario("missing_ack"))
        padded = raw + b" " * (MAX_EXPORT_BYTES - len(raw))
        self.assertEqual(extract_world(padded, "after"), json.loads(raw)["after"])
        with self.assertRaises(ValueError):extract_world(padded + b" ", "after")

    def test_real_cli_file_stdin_and_planner_handoff_preserve_source(self):
        exported = subprocess.run([sys.executable, "-B"] + (["-O"] if sys.flags.optimize else []) + [str(ROOT/"explorer.py"), "run", "approved"],
                                  capture_output=True, cwd=ROOT, env={})
        self.assertEqual(exported.returncode, 0, exported.stderr)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"approved # fixture.json"
            path.write_bytes(exported.stdout)
            for phase, expected in (("before","options_available"),("after","no_conflict")):
                for source in (str(path), "-"):
                    result = self.command(source, "--phase", phase,
                                          data=exported.stdout if source == "-" else None)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, b"")
                    self.assertEqual(json.loads(result.stdout), json.loads(exported.stdout)[phase])
                    reviewed = subprocess.run([sys.executable, "-B"] + (["-O"] if sys.flags.optimize else []) + [str(ROOT/"plan_world.py"), "-"],
                                              input=result.stdout, capture_output=True, cwd=ROOT, env={})
                    self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
                    self.assertEqual(json.loads(reviewed.stdout)["status"], expected)
                    self.assertEqual(path.read_bytes(), exported.stdout)
            mismatch=json.loads(exported.stdout);mismatch["after"]["version"]+=1
            bad=self.command("-", "--phase","before", data=encoded(mismatch))
            self.assertEqual((bad.returncode,bad.stdout),(1,b""))
            self.assertIn(b"replay mismatch",bad.stderr)
            absent=self.command(str(Path(directory)/"absent.json"),"--phase","before")
            self.assertEqual((absent.returncode,absent.stdout),(2,b""))
            missing_phase=self.command(str(path))
            self.assertEqual((missing_phase.returncode,missing_phase.stdout),(2,b""))

    @unittest.skipUnless(os.name == "posix" and Path("/dev/full").exists(), "requires /dev/full")
    def test_cli_reports_actual_output_failure_before_shutdown(self):
        with open("/dev/full","wb",buffering=0) as sink:
            result=self.command("-","--phase","before",data=encoded(run_scenario("approved")),stdout=sink)
        self.assertEqual(result.returncode,2)
        self.assertIn(b"cannot write world",result.stderr)
        self.assertNotIn(b"Exception ignored",result.stderr)

if __name__ == "__main__":
    unittest.main(verbosity=2)
