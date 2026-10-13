"""Saved UTF-8 audit bytes have the same verdict through a file or stdin."""

import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_replay
from towerops import AuditLog

ROOT = Path(__file__).resolve().parents[1]


def trace(reason):
    log = AuditLog()
    log.append("reject", {"reason": reason})
    return log.events


def encoded(events):
    return (json.dumps(events, ensure_ascii=False) + "\n").encode("utf-8")


def invoke(arguments, raw, encoding):
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = encoding
    return subprocess.run(
        [sys.executable, "-B", str(ROOT / "audit_replay.py"), *arguments],
        input=raw, capture_output=True, check=False, timeout=5, cwd=ROOT, env=environment,
    )


class UTF8StdinTests(unittest.TestCase):
    def test_unicode_file_and_both_stdin_forms_have_identical_clean_reports(self):
        for reason in ("café", "café — 東京"):
            raw = encoded(trace(reason))
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "saved café trace.json"
                path.write_bytes(raw)
                for encoding in ("utf-8", "cp1252", "ascii:strict"):
                    reference = invoke([str(path)], None, encoding)
                    self.assertEqual(reference.returncode, 0, reference.stderr)
                    self.assertEqual(reference.stderr, b"")
                    value = json.loads(reference.stdout)
                    self.assertTrue(value["ok"])
                    self.assertTrue(value["chain_valid"])
                    self.assertEqual(value["rejects"], 1)
                    for arguments in ([], ["-"]):
                        with self.subTest(reason=reason, encoding=encoding, args=arguments):
                            actual = invoke(arguments, raw, encoding)
                            self.assertEqual(actual.returncode, 0, actual.stderr)
                            self.assertEqual(actual.stderr, b"")
                            self.assertEqual(actual.stdout, reference.stdout)
                self.assertEqual(path.read_bytes(), raw)

    def test_ascii_empty_and_changed_digest_keep_their_verdicts(self):
        changed = copy.deepcopy(trace("declined"))
        changed[0]["payload"]["reason"] = "changed without matching digest"
        cases = (([], 0), (trace("declined"), 0), (changed, 1))
        for events, expected in cases:
            raw = encoded(events)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "control.json"
                path.write_bytes(raw)
                for encoding in ("utf-8", "cp1252"):
                    with self.subTest(expected=expected, encoding=encoding, events=events):
                        reference = invoke([str(path)], None, encoding)
                        actual = invoke(["-"], raw, encoding)
                        self.assertEqual(reference.returncode, expected, reference.stderr)
                        self.assertEqual(actual.returncode, expected, actual.stderr)
                        self.assertEqual(actual.stderr, b"")
                        self.assertEqual(actual.stdout, reference.stdout)
                self.assertEqual(path.read_bytes(), raw)

    def test_malformed_utf8_is_refused_before_a_summary_under_lossy_stream_settings(self):
        valid = encoded(trace("MARKER"))
        for invalid in (b"\xff", b"\xe2\x82", b"\xc0\xaf"):
            raw = valid.replace(b"MARKER", invalid)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.json"
                path.write_bytes(raw)
                for encoding in ("cp1252:replace", "utf-8:ignore"):
                    for arguments, stdin in (([str(path)], None), (["-"], raw)):
                        with self.subTest(invalid=invalid, encoding=encoding, args=arguments):
                            actual = invoke(arguments, stdin, encoding)
                            self.assertEqual(actual.returncode, 2, actual.stderr)
                            self.assertEqual(actual.stdout, b"")
                            self.assertTrue(actual.stderr.startswith(b"error: cannot load audit events:"))
                            self.assertNotIn(b"Traceback", actual.stderr)
                self.assertEqual(path.read_bytes(), raw)

    def test_text_only_embedded_stdin_remains_supported(self):
        events = trace("café — 東京")
        source = io.StringIO(encoded(events).decode("utf-8"))
        with patch.object(audit_replay.sys, "stdin", source):
            self.assertEqual(audit_replay._load_events("-"), events)
        self.assertFalse(source.closed)

    def test_binary_stdin_does_not_use_its_text_wrappers_encoding(self):
        events = trace("café — 東京")
        raw = encoded(events)
        buffer = io.BytesIO(raw)
        wrapper = io.TextIOWrapper(buffer, encoding="cp1252", errors="replace")
        try:
            with patch.object(audit_replay.sys, "stdin", wrapper):
                self.assertEqual(audit_replay._load_events("-"), events)
            self.assertFalse(wrapper.closed)
            self.assertEqual(buffer.getvalue(), raw)
        finally:
            wrapper.close()


if __name__ == "__main__":
    unittest.main()
