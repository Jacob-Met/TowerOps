"""Actual CLI receiving for named-file admission and preserved streamed input."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "plan_world.py"
MAX_BYTES = 262144
RAW = b'{"version":7,"observed_at":120.0,"aircraft":[]}\n'


class WorldFileInput(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="towerops-world-file-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.world = self.root / "world input \u03a9.json"
        self.world.write_bytes(RAW)

    def run_cli(self, *args, raw: bytes | None = None, script: str | None = None):
        command = [sys.executable, "-B"]
        command += ["-c", script, str(ROOT)] if script else [str(CLI)]
        return subprocess.run(
            [*command, *map(str, args)], input=raw, capture_output=True,
            cwd=self.root, timeout=5, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def assert_refused(self, result, message=b"regular file"):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"error: cannot review world:", result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)

    def test_regular_file_and_stdin_retain_exact_output_and_input(self):
        regular = self.run_cli(self.world)
        streamed = self.run_cli("-", raw=RAW)
        self.assertEqual(regular.returncode, 0, regular.stderr)
        self.assertEqual(streamed.returncode, 0, streamed.stderr)
        self.assertEqual(regular.stdout, streamed.stdout)
        self.assertEqual(regular.stderr, b"")
        self.assertEqual(streamed.stderr, b"")
        report = json.loads(regular.stdout)
        self.assertEqual(report["input_sha256"], hashlib.sha256(RAW).hexdigest())
        self.assertEqual(report["status"], "no_conflict")
        self.assertEqual(self.world.read_bytes(), RAW)

    def test_a_literal_dash_filename_remains_distinct_from_stdin(self):
        (self.root / "-").write_bytes(RAW)
        result = self.run_cli("./-", raw=b"this is not the requested input")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["input_sha256"], hashlib.sha256(RAW).hexdigest())

    @unittest.skipUnless(os.name == "posix", "requires ordinary POSIX symlink creation")
    def test_regular_file_symlink_remains_supported_and_untouched(self):
        link = self.root / "world-link.json"
        link.symlink_to(self.world.name)
        result = self.run_cli(link)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.run_cli(self.world).stdout)
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.world.read_bytes(), RAW)

    def test_directory_and_missing_paths_refuse_without_a_report(self):
        self.assert_refused(self.run_cli(self.root))
        missing = self.root / "absent.json"
        self.assert_refused(self.run_cli(missing), b"error: cannot review world:")
        self.assertFalse(missing.exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires native named pipes")
    def test_fifo_and_fifo_symlink_refuse_without_waiting_for_a_writer(self):
        fifo = self.root / "waiting.fifo"
        os.mkfifo(fifo)
        link = self.root / "fifo-link"
        link.symlink_to(fifo.name)
        for path in (fifo, link):
            with self.subTest(path=path.name):
                self.assert_refused(self.run_cli(path))

    @unittest.skipUnless(os.name == "posix" and Path("/dev/null").exists(), "requires a character device")
    def test_character_device_is_refused_as_a_path(self):
        self.assert_refused(self.run_cli("/dev/null"))

    def test_exact_limit_is_admitted_and_oversize_refuses(self):
        at_limit = RAW + b" " * (MAX_BYTES - len(RAW))
        self.world.write_bytes(at_limit)
        result = self.run_cli(self.world)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["input_sha256"], hashlib.sha256(at_limit).hexdigest())
        with self.world.open("ab") as stream:
            stream.write(b" ")
        self.assert_refused(self.run_cli(self.world), b"exceeds 262144 bytes")
        self.assertEqual(self.world.read_bytes(), at_limit + b" ")
        self.assert_refused(self.run_cli("-", raw=at_limit + b" "), b"exceeds 262144 bytes")

    def test_malformed_file_and_native_gate_keep_their_exit_contracts(self):
        self.world.write_bytes(b"{broken}")
        malformed = self.run_cli(self.world)
        self.assert_refused(malformed, b"Expecting property name")
        self.world.write_bytes(RAW)
        stale = self.run_cli(self.world, "--now", "131")
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertEqual(stale.stdout, b"")
        self.assertIn(b"stale_state", stale.stderr)
        self.assertEqual(self.world.read_bytes(), RAW)

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"), "requires nonblocking FIFO open")
    def test_a_path_replaced_with_a_fifo_after_preflight_cannot_block_open(self):
        # Swap at the path check boundary in an actual child. Removing either
        # O_NONBLOCK or descriptor admission causes a timeout or wrong outcome.
        script = """
import os
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import plan_world
target = Path(sys.argv[2])
original_stat = Path.stat
changed = False
def swap_after_stat(path, *args, **kwargs):
    global changed
    info = original_stat(path, *args, **kwargs)
    if path == target and not changed:
        changed = True
        path.unlink()
        os.mkfifo(path)
    return info
with patch.object(Path, 'stat', swap_after_stat):
    code = plan_world.main([str(target)])
assert changed
raise SystemExit(code)
"""
        result = self.run_cli(self.world, script=script)
        self.assert_refused(result, b"Opened world input is not a regular file")

    def test_oversize_is_refused_before_reading_the_opened_file(self):
        with self.world.open("ab") as stream:
            stream.truncate(MAX_BYTES + 1)
        script = """
import sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import plan_world
with patch('os.fdopen', side_effect=AssertionError('must not read an oversized file')):
    raise SystemExit(plan_world.main([sys.argv[2]]))
"""
        self.assert_refused(self.run_cli(self.world, script=script), b"exceeds 262144 bytes")


if __name__ == "__main__":
    unittest.main()
