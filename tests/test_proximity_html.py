"""Native-report-to-offline-page receiving without a browser dependency."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from proximity_html import render_html
from proximity_report import report_proximity
from tests.test_proximity_report import flight, world


ROOT = Path(__file__).resolve().parents[1]


def test_render_is_self_contained_and_retains_native_evidence():
    raw = world(flight("A", -5, vx=1), flight("B", 5, vx=-1),
                flight("C", 15, altitude=18000))
    report = report_proximity(raw)
    html = render_html(report)
    assert html.startswith("<!doctype html>")
    assert html.count("<script id=\"report-data\" type=\"application/json\">") == 1
    assert report["world_hash"] in html
    assert hashlib.sha256(raw).hexdigest() in html
    assert "connect-src 'none'" in html
    assert "http://" not in html and "https://" not in html
    assert "Native conflict" in html


def test_data_string_cannot_escape_json_script():
    report = report_proximity(world(flight("A", 0)))
    hostile = '</script><img src=x onerror="alert(1)">&\u2028'
    report["diagnostic_note"] = hostile
    html = render_html(report)
    assert hostile not in html
    assert html.count("</script>") == 2
    assert "\\u003c/script\\u003e" in html
    assert "\\u0026" in html
    assert "\\u2028" in html


def test_wrong_report_format_is_refused():
    with pytest.raises(ValueError, match="Only towerops"):
        render_html({"format": "unknown"})


def test_html_cli_from_stdin_preserves_original_input_and_writes_no_other_file(tmp_path):
    raw = world(flight("F-7", -5, vx=1), flight("F-8", 5, vx=-1))
    source = tmp_path / "before.json"
    source.write_bytes(raw)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "proximity_html.py"), "-", "--limit", "1"],
        input=raw, capture_output=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stdout.startswith(b"<!doctype html>")
    assert b"report-data" in proc.stdout
    assert source.read_bytes() == raw
    assert {p.name for p in tmp_path.iterdir()} == {"before.json"}


def test_html_cli_refuses_bad_state_without_partial_document():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "proximity_html.py"), "-"],
        input=b"{}", capture_output=True, check=False,
    )
    assert proc.returncode == 2
    assert proc.stdout == b""
    assert b"error: cannot create proximity review:" in proc.stderr
