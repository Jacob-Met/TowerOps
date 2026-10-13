"""The audit CLI keeps input failures separate from rejected audit reports."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("source", ["file", "stdin"])
def test_deep_trace_reports_input_error_without_traceback(tmp_path, source):
    # CPython 3.12 refuses this depth while decoding. Runtimes able to decode
    # it still receive an invalid event shape and must use the same CLI error
    # status. Do not assume the decoder follows sys.getrecursionlimit().
    raw = ("[" * 10_000 + "0" + "]" * 10_000).encode("ascii")
    path = tmp_path / "deep-trace.json"
    if source == "file":
        path.write_bytes(raw)
    repo_root = Path(__file__).resolve().parents[1]
    process = subprocess.run(
        [sys.executable, str(repo_root / "audit_replay.py"),
         str(path) if source == "file" else "-"],
        input=raw if source == "stdin" else None,
        capture_output=True,
        check=False,
        timeout=10,
        cwd=repo_root,
    )
    assert process.returncode == 2, process.stderr.decode("utf-8", errors="replace")
    assert process.stdout == b""
    assert process.stderr.startswith(b"error: ")
    assert b"Traceback" not in process.stderr
    if source == "file":
        assert path.read_bytes() == raw
