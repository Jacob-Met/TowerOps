"""Writer failures must leave the audit CLI with its explicit error status."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("unbuffered", [False, True], ids=["flush", "write"])
@pytest.mark.parametrize("sink_kind", ["full", "closed_pipe"])
def test_report_output_refusal_has_no_uncaught_error(
    tmp_path, source, unbuffered, sink_kind
):
    # A small buffered report fails at flush; -u makes the same destination
    # refuse the write itself. A pipe with no readers works without /dev/full.
    if sink_kind == "full":
        if not Path("/dev/full").is_char_device():
            pytest.skip("requires the Linux /dev/full character device")
        output_fd = os.open("/dev/full", os.O_WRONLY)
    else:
        reader, output_fd = os.pipe()
        os.close(reader)

    raw = b"[ ]\n"
    path = tmp_path / "trace.json"
    repo_root = Path(__file__).resolve().parents[1]
    try:
        if source == "file":
            path.write_bytes(raw)
        process = subprocess.run(
            [
                sys.executable,
                *(["-u"] if unbuffered else []),
                str(repo_root / "audit_replay.py"),
                str(path) if source == "file" else "-",
            ],
            input=raw if source == "stdin" else None,
            stdout=output_fd,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
            cwd=repo_root,
        )
    finally:
        os.close(output_fd)

    assert process.returncode == 2, process.stderr.decode("utf-8", errors="replace")
    assert process.stderr.startswith(b"error: cannot write audit summary:")
    assert b"Traceback" not in process.stderr
    assert b"Exception ignored" not in process.stderr
    if source == "file":
        assert path.read_bytes() == raw
