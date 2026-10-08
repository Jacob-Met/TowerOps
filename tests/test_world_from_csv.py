"""Native CSV authoring and unchanged planner consumption, using synthetic data."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plan_world import MAX_WORLD_BYTES, parse_world
from world_from_csv import COLUMNS, main, world_from_csv

ROOT = Path(__file__).resolve().parents[1]
HEADER = ",".join(COLUMNS) + "\n"
ROWS = "WEST,5,0,10000,-1,0,0\nEAST,-5,0,10000,1,0,0\n"


def cli(raw: bytes, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "world_from_csv.py"), "-", "--observed-at", "1000", *args],
        input=raw, capture_output=True, check=False,
    )


class CSVWorldTests(unittest.TestCase):
    def test_real_cli_stdout_is_consumed_by_unchanged_native_planner(self):
        result = cli((HEADER + ROWS).encode(), "--version", "8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        expected = {"version": 8, "observed_at": 1000, "aircraft": [
            dict(zip(COLUMNS, ("EAST", -5, 0, 10000, 1, 0, 0))),
            dict(zip(COLUMNS, ("WEST", 5, 0, 10000, -1, 0, 0))),
        ]}
        self.assertEqual(json.loads(result.stdout), expected)
        planned = subprocess.run(
            [sys.executable, str(ROOT / "plan_world.py"), "-"],
            input=result.stdout, capture_output=True, check=False,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr)
        report = json.loads(planned.stdout)
        self.assertEqual(report["world"], expected)
        self.assertEqual(report["world_hash"], parse_world(result.stdout).world_hash)
        self.assertEqual(report["input_sha256"], hashlib.sha256(result.stdout).hexdigest())
        self.assertEqual(report["status"], "options_available")
        self.assertTrue(report["proposal_only"])
        self.assertTrue(report["advisories"])

    def test_bom_crlf_quoted_reordered_columns_and_rows_have_native_order(self):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writerow(reversed(COLUMNS))
        for row in reversed(list(csv.reader(io.StringIO(ROWS)))):
            writer.writerow(reversed(row))
        changed = cli(b"\xef\xbb\xbf" + stream.getvalue().encode())
        ordinary = cli((HEADER + ROWS).encode())
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertEqual(changed.stdout, ordinary.stdout)

    def test_numeric_interpretation_preserves_types_and_signed_float_zero(self):
        raw = (HEADER + "A,1,1.0,-0.0,2e-3, 4 ,0\n").encode()
        world = world_from_csv(raw, observed_at=-0.0)
        aircraft = world.aircraft[0]
        self.assertIs(type(aircraft.x_nm), int)
        self.assertIs(type(aircraft.y_nm), float)
        self.assertEqual(math.copysign(1, aircraft.altitude_ft), -1)
        self.assertEqual(math.copysign(1, world.observed_at), -1)
        self.assertEqual(aircraft.vx_nm_min, 0.002)
        self.assertEqual(aircraft.vy_nm_min, 4)
        self.assertEqual(world.version, 0)
        self.assertEqual(raw, (HEADER + "A,1,1.0,-0.0,2e-3, 4 ,0\n").encode())

    def test_header_only_is_an_explicit_empty_world(self):
        result = cli(HEADER.encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"version": 0, "observed_at": 1000, "aircraft": []})
        for raw in (b"", b"\xef\xbb\xbf", (HEADER + "\n").encode()):
            with self.subTest(raw=raw):
                self.assert_refused(raw)

    def assert_refused(self, raw: bytes, *args: str):
        result = cli(raw, *args)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertTrue(result.stderr)

    def test_header_shape_is_exact(self):
        headers = [COLUMNS[:-1], (*COLUMNS, "notes"), (*COLUMNS[:-1], "x_nm"),
                   ("Aircraft_ID", *COLUMNS[1:]), (" aircraft_id", *COLUMNS[1:])]
        for header in headers:
            with self.subTest(header=header):
                self.assert_refused((",".join(header) + "\n" + ROWS).encode())

    def test_late_record_refusals_never_publish_valid_prefix(self):
        invalid = ["A,1,2\n", "A,1,2,3,4,5,6,extra\n", '"A,1,2,3,4,5,6\n',
                   '"A"suffix,1,2,3,4,5,6\n', " EAST,0,0,0,0,0,0\n",
                   "EAST,0,0,0,0,0,0\n", "bad/id,0,0,0,0,0,0\n"]
        for row in invalid:
            with self.subTest(row=row):
                self.assert_refused((HEADER + ROWS + row).encode())

    def test_native_number_rules_and_no_spreadsheet_formula_evaluation(self):
        for value in ("", "NaN", "Infinity", "-Infinity", "1e999", "1000000000001",
                      "-1000000000001", "true", "null", "[]", "{}", "01", "+1", "1_000", "=2+2"):
            with self.subTest(value=value):
                self.assert_refused((HEADER + "A," + value + ",0,0,0,0,0\n").encode())
        self.assert_refused((HEADER + 'A,"1,000",0,0,0,0,0\n').encode())
        self.assert_refused((HEADER + 'A,"""1""",0,0,0,0,0\n').encode())

    def test_native_metadata_rules_and_required_observation(self):
        for version in ("-1", "1.0", "1e0", "9007199254740992", "true"):
            with self.subTest(version=version):
                self.assert_refused(HEADER.encode(), "--version", version)
        for observed in ("NaN", "1e999", "1000000000001", "false"):
            with self.subTest(observed=observed):
                self.assert_refused(HEADER.encode(), "--observed-at", observed)
        result = subprocess.run([sys.executable, str(ROOT / "world_from_csv.py"), "-"],
                                input=HEADER.encode(), capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(cli(HEADER.encode(), "--version", "9007199254740991").returncode, 0)

    def test_row_count_and_exact_input_byte_limit(self):
        rows = "".join(f"A{i},0,0,0,0,0,0\n" for i in range(60))
        self.assertEqual(cli((HEADER + rows).encode()).returncode, 0)
        self.assert_refused((HEADER + rows + "LAST,0,0,0,0,0,0\n").encode())
        # A legal numeric cell padded with JSON whitespace exercises the byte
        # boundary without changing csv.field_size_limit's process-global value.
        padding = MAX_WORLD_BYTES - len((HEADER + ROWS).encode())
        parts = ROWS.split(",")
        for index in (1, 2, 3):
            amount = padding // 3 + (1 if index <= padding % 3 else 0)
            parts[index] += " " * amount
        exact = (HEADER + ",".join(parts)).encode()
        self.assertEqual(len(exact), MAX_WORLD_BYTES)
        self.assertEqual(cli(exact).returncode, 0)
        self.assert_refused(exact + b" ")

    def test_native_validation_also_applies_to_direct_callers(self):
        for kwargs in ({"observed_at": True}, {"observed_at": 0, "version": False},
                       {"observed_at": 0, "version": 2.0}, {"observed_at": float("inf")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                world_from_csv(HEADER.encode(), **kwargs)
        with self.assertRaises(TypeError):
            world_from_csv(HEADER, observed_at=0)
        self.assert_refused(HEADER.encode() + b"\xff")

    def test_file_input_remains_exact_and_matches_stdin(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "traffic input.csv"
            raw = (HEADER + ROWS).encode()
            path.write_bytes(raw)
            result = subprocess.run([sys.executable, str(ROOT / "world_from_csv.py"),
                                     str(path), "--observed-at", "1000"], capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, cli(raw).stdout)
            self.assertEqual(path.read_bytes(), raw)

    def test_flush_failure_is_reported_without_claiming_completed_output(self):
        class Input:
            buffer = io.BytesIO(HEADER.encode())

        class Output(io.StringIO):
            def flush(self):
                raise OSError("authored flush refusal")

        output = Output()
        errors = io.StringIO()
        with patch("sys.stdin", Input()), patch("sys.stdout", output), patch("sys.stderr", errors):
            self.assertEqual(main(["-", "--observed-at", "0"]), 2)
        self.assertIn("cannot write world", errors.getvalue())
        self.assertTrue(output.closed)


if __name__ == "__main__":
    unittest.main()
