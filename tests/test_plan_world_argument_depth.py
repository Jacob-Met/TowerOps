"""Numeric option decoder limits remain ordinary CLI argument errors."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "plan_world.py"


class NumericArgumentDepth(unittest.TestCase):
    def test_deep_json_numeric_arguments_refuse_before_reading_a_world(self):
        # Keep the payload below 32 KiB for ordinary Windows launches. This
        # reaches the JSON nesting guard on the receiving CPython 3.12 runtime.
        argument = "[" * 12288 + "0" + "]" * 12288
        with tempfile.TemporaryDirectory(prefix="towerops-argument-depth-") as temporary:
            missing = Path(temporary) / "not-read.json"
            for option in ("--now", "--horizontal-nm", "--vertical-ft", "--horizon-min"):
                with self.subTest(option=option):
                    result = subprocess.run(
                        [sys.executable, "-B", str(CLI), str(missing), option, argument],
                        cwd=temporary, capture_output=True, text=True, timeout=5, check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(f"argument {option}", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertNotIn(str(missing), result.stderr)
                    self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
