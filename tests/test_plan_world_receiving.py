"""Independent raw-world CLI receiving against the existing immutable native APIs."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

import towerops
from advisory_options import review_advisory_options
from towerops import (
    Advisory,
    AdvisoryPlanner,
    Aircraft,
    ControlRoom,
    GateRejected,
    SafetyPolicy,
    WorldState,
    canonical_bytes,
)

SOURCE = Path(towerops.__file__).resolve().parent
FROZEN_INPUT_HASHES = {'paired-world.json': '2c8f41416122613af31e53910bfbcf79148d5e66d5c8a030819e3f85909f008b', 'paired-world-compact.json': '6a5b58bfa3207023c6d0ef033da71430faa7f10779834f0caab79aafd7574c69', 'empty-world.json': '195064a9c209187dc1aa42110fc1c5cf3f9865ff757c3674839ad79bd0fdabeb', 'coincident-world.json': '36dcf81a47c504059e258255f856189efae2f9fb87ac51e69b3510ed2d97dfd5'}


def aircraft(identity, x, y, altitude, vx, vy, climb):
    return {"aircraft_id": identity, "x_nm": x, "y_nm": y, "altitude_ft": altitude,
            "vx_nm_min": vx, "vy_nm_min": vy, "climb_ft_min": climb}


def synthetic_inputs():
    paired = {
        "version": 41, "observed_at": 250,
        "aircraft": [
            aircraft("b", 8, 60.0, 12000, -2.0, 0.0, 0),
            aircraft("A", -8, -0.0, 12000, 2.0, 0, -0.0),
            aircraft("a", 8.0, 0, 12000.0, -2, -0.0, 0),
            aircraft("B", -8.0, 60, 12000, 2, 0, 0.0),
        ],
    }
    empty = {"version": 0, "observed_at": 100.0, "aircraft": []}
    coincident = {
        "version": 2, "observed_at": 10.0,
        "aircraft": [
            aircraft("L", 1, 0, 12000, 0, 2, 0.0),
            aircraft("l", 1.0, -0.0, 12000.0, 0.0, -2.0, -0.0),
        ],
    }
    return {
        "paired-world.json": (json.dumps(paired, indent=3) + "\n").encode(),
        "paired-world-compact.json": json.dumps(paired, separators=(",", ":"), sort_keys=True).encode(),
        "empty-world.json": (json.dumps(empty, indent=2) + "\n").encode(),
        "coincident-world.json": (json.dumps(coincident, indent=2) + "\n").encode(),
    }


def native_expected(raw, now=None, policy=None):
    data = json.loads(raw)
    state = WorldState(data["version"], data["observed_at"], tuple(Aircraft(**a) for a in data["aircraft"]))
    policy = SafetyPolicy() if policy is None else policy
    now = state.observed_at if now is None else now
    options = review_advisory_options(state, now, policy)
    conflicts = [a.aircraft_id for a in policy.conflicting_aircraft(state)]
    status = "options_available" if options.advisories else ("no_admitted_option" if conflicts else "no_conflict")
    result = {
        "format": "towerops.world-plan.v1", "simulation_only": True, "proposal_only": True,
        "input_sha256": hashlib.sha256(raw).hexdigest(), "world": state.to_dict(),
        "world_hash": state.world_hash, "reviewed_at": now, "policy": asdict(policy),
        "status": status, "conflicting_aircraft": conflicts, "candidate_count": options.candidate_count,
        "advisories": [{**asdict(a), "advisory_hash": a.advisory_hash} for a in options.advisories],
    }
    return result, state, policy


class NativeWorldPlanReceiving(unittest.TestCase):
    def setUp(self):
        retain = os.environ.get("TOWEROPS_RECEIVING_OUTPUT")
        if retain:
            self.work = Path(retain) / self._testMethodName
            self.work.mkdir(parents=True, exist_ok=False)
        else:
            temporary = tempfile.TemporaryDirectory(prefix="towerops-plan-peer-")
            self.addCleanup(temporary.cleanup)
            self.work = Path(temporary.name)
        self.logs = self.work / "receiving-logs"
        self.logs.mkdir()
        self.inputs = synthetic_inputs()
        self.assertEqual({name: hashlib.sha256(raw).hexdigest() for name, raw in self.inputs.items()},
                         FROZEN_INPUT_HASHES, "blind fixture bytes drifted")
        self.source_before = self.source_hashes()
        self.sequence = 0
        self.stdout_files = {}

    def source_hashes(self):
        return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(SOURCE.glob("*.py"))}

    def tearDown(self):
        self.assertEqual(self.source_before, self.source_hashes(), "native source bytes changed")
        (self.logs / "source-hashes.json").write_text(json.dumps(self.source_before, indent=2) + "\n")

    def snapshot_work(self):
        return {str(path.relative_to(self.work)): (path.stat().st_mode, hashlib.sha256(path.read_bytes()).hexdigest())
                for path in self.work.rglob("*") if path.is_file()}

    def fixture(self, name, destination=None):
        path = self.work / (destination or name)
        path.write_bytes(self.inputs[name])
        return path

    def cli(self, *args, stdin=None, closed_stdout=False):
        env = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, "-B", str(SOURCE / "plan_world.py"), *(str(arg) for arg in args)]
        before = self.snapshot_work()
        before_names = {str(path.relative_to(self.work)) for path in self.work.rglob("*")}
        if closed_stdout:
            read_fd, write_fd = os.pipe()
            os.close(read_fd)
            try:
                result = subprocess.run(command, cwd=self.work, env=env, input=stdin,
                                        stdout=write_fd, stderr=subprocess.PIPE, timeout=30, check=False)
            finally:
                os.close(write_fd)
        else:
            result = subprocess.run(command, cwd=self.work, env=env, input=stdin,
                                    capture_output=True, timeout=30, check=False)
        self.assertEqual(before, self.snapshot_work(), "consumer changed a saved file or emitted a fallback file")
        self.assertEqual(before_names, {str(path.relative_to(self.work)) for path in self.work.rglob("*")},
                         "consumer created/deleted working-directory content")
        self.assertEqual(self.source_before, self.source_hashes(), "consumer changed source")
        self.sequence += 1
        stdout = result.stdout or b""
        digest = hashlib.sha256(stdout).hexdigest()
        output_path = None
        if stdout:
            path = self.logs / f"command-{self.sequence}.stdout"
            if digest in self.stdout_files:
                os.link(self.stdout_files[digest], path)
            else:
                path.write_bytes(stdout)
                self.stdout_files[digest] = path
            output_path = path.name
        entry = {"argv": command, "returncode": result.returncode,
                 "stdin_sha256": hashlib.sha256(stdin).hexdigest() if stdin is not None else None,
                 "stdout_sha256": digest, "stdout_bytes": len(stdout), "stdout_file": output_path,
                 "stderr": result.stderr.decode("utf-8"), "closed_stdout_pipe": closed_stdout}
        with (self.logs / "commands.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry) + "\n")
        return result

    def completed(self, result, raw, now=None, policy=None):
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        actual = json.loads(result.stdout)
        expected, state, native_policy = native_expected(raw, now, policy)
        # Canonical serialization distinguishes JSON integer/float values and signed zero.
        self.assertEqual(canonical_bytes(actual), canonical_bytes(expected))
        return actual, state, native_policy

    def refusal(self, result, code, reason):
        self.assertEqual(result.returncode, code, result.stderr.decode())
        self.assertEqual(result.stdout or b"", b"")
        self.assertIn(reason, result.stderr.decode())
        self.assertNotIn("Traceback", result.stderr.decode())

    def test_custom_world_file_stdin_exact_native_menu_and_approval_boundary(self):
        raw = self.inputs["paired-world.json"]
        self.fixture("paired-world.json", "-")
        arguments = ("--now", "258.0", "--horizontal-nm", "3.0", "--vertical-ft", "750", "--horizon-min", "4")
        policy = SafetyPolicy(min_horizontal_nm=3.0, min_vertical_ft=750, horizon_min=4)
        file_result = self.cli("./-", *arguments)
        actual, state, policy = self.completed(file_result, raw, 258.0, policy)
        stdin_result = self.cli("-", *arguments, stdin=raw)
        self.completed(stdin_result, raw, 258.0, policy)
        self.assertEqual(file_result.stdout, stdin_result.stdout)
        self.assertEqual([a["aircraft_id"] for a in actual["world"]["aircraft"]], ["A", "B", "a", "b"])
        self.assertEqual(actual["status"], "options_available")
        self.assertGreater(actual["candidate_count"], 0)
        self.assertGreater(len(actual["advisories"]), 1)
        compact = self.inputs["paired-world-compact.json"]
        compact_path = self.fixture("paired-world-compact.json")
        compact_actual, _, _ = self.completed(self.cli(compact_path, *arguments), compact, 258.0, policy)
        self.assertNotEqual(actual["input_sha256"], compact_actual["input_sha256"])
        self.assertEqual(actual["world_hash"], compact_actual["world_hash"])
        self.assertEqual(canonical_bytes(actual["advisories"]), canonical_bytes(compact_actual["advisories"]))
        first = dict(actual["advisories"][0])
        reported_hash = first.pop("advisory_hash")
        advisory = Advisory(**first)
        self.assertEqual(advisory.advisory_hash, reported_hash)
        self.assertEqual(canonical_bytes(asdict(advisory)), canonical_bytes(asdict(AdvisoryPlanner(policy).plan(state, 258.0)[0])))
        original_world = canonical_bytes(state.to_dict())
        updated = replace(state.get(advisory.aircraft_id), vx_nm_min=advisory.set_vx_nm_min,
                          vy_nm_min=advisory.set_vy_nm_min, climb_ft_min=advisory.set_climb_ft_min)
        counterfactual = replace(state, aircraft=tuple(updated if a.aircraft_id == updated.aircraft_id else a
                                                       for a in state.aircraft))
        self.assertTrue(policy.advisory_safe(state, advisory))
        self.assertTrue(policy.state_has_conflict(counterfactual), "an unrelated encounter should remain")
        room = ControlRoom(policy)
        with self.assertRaisesRegex(GateRejected, "^human_approval_required$"):
            room.apply(state, advisory, None, None, 258.0)
        self.assertEqual(canonical_bytes(state.to_dict()), original_world)
        self.assertFalse(any(event["kind"] in ("approval", "ack", "simulated_actuation") for event in room.audit.events))

    def test_requested_horizon_and_empty_world_keep_native_clock_refusals(self):
        raw = self.inputs["paired-world.json"]
        path = self.fixture("paired-world.json")
        policy = SafetyPolicy(min_horizontal_nm=3.0, min_vertical_ft=750, horizon_min=2)
        result = self.cli(path, "--now", "258.0", "--horizontal-nm", "3.0", "--vertical-ft", "750", "--horizon-min", "2")
        actual, _, _ = self.completed(result, raw, 258.0, policy)
        self.assertEqual((actual["status"], actual["candidate_count"], actual["advisories"]), ("no_conflict", 0, []))
        empty_path = self.fixture("empty-world.json")
        empty, _, _ = self.completed(self.cli(empty_path), self.inputs["empty-world.json"])
        self.assertEqual((empty["status"], empty["world"]["aircraft"], empty["candidate_count"]), ("no_conflict", [], 0))
        self.refusal(self.cli(empty_path, "--now", "99.5"), 1, "future_state")
        self.refusal(self.cli(empty_path, "--now", "110.5"), 1, "stale_state")

    def test_conflicting_world_with_no_admitted_option_is_a_completed_review(self):
        path = self.fixture("coincident-world.json")
        actual, _, _ = self.completed(self.cli(path), self.inputs["coincident-world.json"])
        self.assertEqual(actual["status"], "no_admitted_option")
        self.assertEqual(actual["conflicting_aircraft"], ["L", "l"])
        self.assertGreater(actual["candidate_count"], 0)
        self.assertEqual(actual["advisories"], [])

    def test_generated_report_is_not_raw_input_and_closed_pipe_failure_is_clean(self):
        path = self.fixture("empty-world.json")
        initial = self.cli(path)
        self.completed(initial, self.inputs["empty-world.json"])
        self.refusal(self.cli("-", stdin=initial.stdout), 2, "World must contain exactly")
        self.refusal(self.cli(path, closed_stdout=True), 2, "cannot write report")


if __name__ == "__main__":
    unittest.main(verbosity=2)
