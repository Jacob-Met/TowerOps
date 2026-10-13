"""Focused public API and actual CLI controls for Explorer replay explanations."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from replay_explain import explain_replay, run_explanation
from scenarios import replay_result, run_scenario

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 262144


class ReplayExplanationTests(unittest.TestCase):
    def setUp(self):
        self.export = run_scenario("approved")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "export 東京.json"

    def save(self, value=None):
        self.path.write_text(json.dumps(self.export if value is None else value),
                             encoding="utf-8")
        return self.path

    def cli(self, *args, stdout=subprocess.PIPE):
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        optimize = ["-O"] if sys.flags.optimize else []
        return subprocess.run([sys.executable, *optimize, "-B", str(ROOT / "explorer.py"),
                               "replay", *map(str, args)], cwd=self.directory.name,
                              env=env, stdout=stdout, stderr=subprocess.PIPE, timeout=15)

    def test_match_and_finite_numeric_equivalence(self):
        actual = copy.deepcopy(self.export)
        actual["before"]["aircraft"][0]["x_nm"] = -5
        report = explain_replay(actual)
        self.assertTrue(report["matches"])
        self.assertEqual(report["differences"], [])
        self.assertFalse(report["differences_truncated"])
        self.assertEqual(report["difference_limit"], 32)
        self.assertEqual({k: report[k] for k in replay_result(actual)}, replay_result(actual))

    def test_literal_type_value_missing_null_and_pointer_order(self):
        actual = copy.deepcopy(self.export)
        actual["after"]["version"] += 1
        actual["policy"]["horizon_min"] = True
        del actual["rejection_reason"]
        actual["z/~東京"] = "<literal>&\nline"
        report = explain_replay(actual)
        self.assertFalse(report["matches"])
        self.assertEqual([(r["path"], r["kind"]) for r in report["differences"]],
                         [("/after/version", "value"), ("/policy/horizon_min", "type"),
                          ("/rejection_reason", "missing"), ("/z~1~0東京", "unexpected")])
        rows = report["differences"]
        self.assertEqual(rows[1]["expected"]["type"], "number")
        self.assertEqual(rows[1]["actual"], {"present": True, "type": "boolean", "value": True})
        self.assertEqual(rows[2]["expected"], {"present": True, "type": "null", "value": None})
        self.assertEqual(rows[2]["actual"], {"present": False})
        self.assertEqual(rows[3]["actual"]["value"], "<literal>&\nline")

    def test_array_presence_and_subtree_type_are_explicit(self):
        actual = copy.deepcopy(self.export)
        missing = actual["before"]["aircraft"].pop()
        report = explain_replay(actual)
        self.assertEqual(report["differences"], [{
            "path": "/before/aircraft/1", "kind": "missing",
            "expected": {"present": True, "type": "object", "value": missing},
            "actual": {"present": False}}])
        actual = copy.deepcopy(self.export)
        actual["before"]["aircraft"].append(None)
        report = explain_replay(actual)
        self.assertEqual(report["differences"][0]["path"], "/before/aircraft/2")
        self.assertEqual(report["differences"][0]["kind"], "unexpected")
        actual["before"]["aircraft"] = "not an array"
        report = explain_replay(actual)
        self.assertEqual(len(report["differences"]), 1)
        self.assertEqual(report["differences"][0]["kind"], "type")
        self.assertEqual(report["differences"][0]["path"], "/before/aircraft")

    def test_limit_detects_more_without_claiming_total(self):
        actual = copy.deepcopy(self.export)
        for index in range(32):
            actual[f"z{index:02}"] = index
        exact = explain_replay(actual)
        self.assertEqual(len(exact["differences"]), 32)
        self.assertFalse(exact["differences_truncated"])
        actual["z32"] = 32
        overflow = explain_replay(actual)
        self.assertEqual(overflow["differences"], exact["differences"])
        self.assertTrue(overflow["differences_truncated"])
        self.assertNotIn("difference_count", overflow)

    def test_report_is_detached_and_input_unchanged(self):
        actual = copy.deepcopy(self.export)
        actual["extra"] = {"literal": ["東京"]}
        before = copy.deepcopy(actual)
        report = explain_replay(actual)
        self.assertEqual(actual, before)
        report["differences"][0]["actual"]["value"]["literal"].append("local note")
        self.assertEqual(actual, before)

    def test_default_reply_and_actual_cli_match_mismatch(self):
        path = self.save()
        original_bytes = path.read_bytes()
        default = self.cli(path)
        self.assertEqual((default.returncode, default.stderr), (0, b""))
        self.assertEqual(default.stdout, (json.dumps(replay_result(self.export), indent=2) + "\n").encode())
        matching = self.cli(path, "--explain")
        self.assertEqual((matching.returncode, matching.stderr), (0, b""))
        self.assertEqual(json.loads(matching.stdout)["differences"], [])
        self.assertEqual(path.read_bytes(), original_bytes)
        self.export["after"]["version"] += 1
        self.save()
        mismatch = self.cli("--explain", path)
        self.assertEqual((mismatch.returncode, mismatch.stderr), (1, b""))
        self.assertEqual(json.loads(mismatch.stdout)["differences"][0]["path"], "/after/version")

    def test_explain_refuses_malformed_deep_nonfinite_and_bad_utf8_before_stdout(self):
        valid = json.dumps(self.export).encode()
        cases = [b"{", b"\xff", b"[" * 2000 + b"0" + b"]" * 2000]
        for token in [b"NaN", b"Infinity", b"-Infinity", b"1e999"]:
            cases.append(valid[:-1] + b', "extra": ' + token + b"}")
        for raw in cases:
            with self.subTest(raw_prefix=raw[:16]):
                self.path.write_bytes(raw)
                result = self.cli(self.path, "--explain")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertIn(b"Replay explanation rejected:", result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)
                self.assertEqual(self.path.read_bytes(), raw)

    def test_explain_actual_byte_bound_and_regular_file_refusal(self):
        self.path.write_bytes(b" " * (MAX_BYTES + 1))
        result = self.cli(self.path, "--explain")
        self.assertEqual((result.returncode, result.stdout), (2, b""))
        self.assertIn(b"Export exceeds 262144 bytes", result.stderr)
        for path in [Path(self.directory.name), Path(self.directory.name) / "missing.json"]:
            with self.subTest(path=str(path)):
                result = self.cli(path, "--explain")
                self.assertEqual((result.returncode, result.stdout), (2, b""))
                self.assertNotIn(b"Traceback", result.stderr)
        if hasattr(os, "mkfifo"):
            fifo = Path(self.directory.name) / "input.fifo"
            os.mkfifo(fifo)
            result = self.cli(fifo, "--explain")
            self.assertEqual((result.returncode, result.stdout), (2, b""))
            self.assertIn(b"regular file", result.stderr)

    def test_short_write_and_flush_failure_never_claim_success(self):
        self.save()

        class Output:
            def __init__(self, short=False):
                self.short = short
                self.text = ""
                self.closed = False

            def write(self, text):
                self.text += text
                return len(text) - 1 if self.short else len(text)

            def flush(self):
                raise OSError("authored flush failure")

            def close(self):
                self.closed = True

        for short in [False, True]:
            output, errors = Output(short), io.StringIO()
            self.assertEqual(run_explanation(self.path, MAX_BYTES, output, errors), 2)
            self.assertIn("output failed:", errors.getvalue())
            self.assertFalse(output.closed)
            self.assertTrue(json.loads(output.text)["matches"])

    @unittest.skipUnless(Path("/dev/full").exists(), "/dev/full is unavailable")
    def test_actual_stdout_failure_is_controlled_and_preserves_input(self):
        self.save()
        before = self.path.read_bytes()
        with open("/dev/full", "wb") as sink:
            result = self.cli(self.path, "--explain", stdout=sink)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"Replay explanation output failed:", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertNotIn(b"Exception ignored", result.stderr)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
