"""The audit command admits one source before it reads or reviews anything."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_with_input_sentinel(tmp_path, arguments):
    sentinel = tmp_path / "stdin-sentinel.json"
    raw = b"[]\n"
    sentinel.write_bytes(raw)
    with sentinel.open("rb", buffering=0) as stream:
        process = subprocess.run(
            [sys.executable, str(REPO_ROOT / "audit_replay.py"), *arguments],
            stdin=stream,
            capture_output=True,
            check=False,
            timeout=10,
            cwd=tmp_path,
        )
        consumed = stream.tell()
    assert sentinel.read_bytes() == raw
    return process, consumed


@pytest.mark.parametrize(
    "case", ["extra_input", "extra_flag", "two_files", "unknown_flag"]
)
def test_invalid_arguments_refuse_before_reading_stdin(tmp_path, case):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first_raw = b"[]\n"
    second_raw = b"this is not an audit trace\n"
    first.write_bytes(first_raw)
    second.write_bytes(second_raw)
    arguments = {
        "extra_input": ["-", str(second)],
        "extra_flag": ["-", "--unexpected"],
        "two_files": [str(first), str(second)],
        "unknown_flag": ["--unexpected"],
    }[case]

    process, consumed = _run_with_input_sentinel(tmp_path, arguments)

    assert process.returncode == 2, process.stderr.decode("utf-8", errors="replace")
    assert process.stdout == b""
    assert b"usage:" in process.stderr.lower()
    assert b"error:" in process.stderr.lower()
    assert b"Traceback" not in process.stderr
    assert consumed == 0
    assert first.read_bytes() == first_raw
    assert second.read_bytes() == second_raw


@pytest.mark.parametrize("option", ["-h", "--help"])
def test_help_explains_the_input_without_reading_stdin(tmp_path, option):
    process, consumed = _run_with_input_sentinel(tmp_path, [option])

    assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
    assert process.stderr == b""
    assert process.stdout.lower().startswith(b"usage:")
    assert b"source" in process.stdout.lower()
    assert b"stdin" in process.stdout.lower()
    assert b"audit" in process.stdout.lower()
    assert consumed == 0


@pytest.mark.parametrize("arguments", [[], ["-"]], ids=["default", "explicit"])
def test_stdin_source_forms_keep_the_normal_summary(tmp_path, arguments):
    process, consumed = _run_with_input_sentinel(tmp_path, arguments)

    assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
    assert process.stderr == b""
    assert json.loads(process.stdout) == {
        "ok": True,
        "chain_valid": True,
        "advisories": 0,
        "actuated": 0,
        "rejects": 0,
        "issues": [],
    }
    assert consumed == 3


def test_separator_allows_a_filename_that_looks_like_help(tmp_path):
    path = tmp_path / "--help"
    raw = b"[ ]\n"
    path.write_bytes(raw)

    process, consumed = _run_with_input_sentinel(tmp_path, ["--", path.name])

    assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
    assert process.stderr == b""
    assert json.loads(process.stdout)["ok"] is True
    assert consumed == 0
    assert path.read_bytes() == raw
