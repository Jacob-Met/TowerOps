"""Consumer qualification for read-only saved-world proximity ranking."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from proximity_report import MAX_PAIRS, report_proximity
from plan_world import parse_world


ROOT = Path(__file__).resolve().parents[1]


def world(*aircraft, version=4, observed_at=1000):
    return (json.dumps({"version": version, "observed_at": observed_at,
                        "aircraft": list(aircraft)}) + "\n").encode()


def flight(name, x, y=0, altitude=10000, vx=0, vy=0, climb=0):
    return {"aircraft_id": name, "x_nm": x, "y_nm": y,
            "altitude_ft": altitude, "vx_nm_min": vx,
            "vy_nm_min": vy, "climb_ft_min": climb}


def test_head_on_conflict_at_different_times_and_read_only_evidence():
    raw = world(flight("Z", -5, vx=1), flight("A", 5, vx=-1))
    original = bytes(raw)
    result = report_proximity(raw)
    pair = result["pairs"][0]
    assert result["native_conflict_pair_count"] == 1
    assert result["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["world_hash"] == parse_world(raw).world_hash
    assert (pair["aircraft_a"], pair["aircraft_b"]) == ("A", "Z")
    assert pair["native_conflict"] is True
    assert pair["closest_time_min"] == pytest.approx(5)
    assert pair["proximity_ratio"] == pytest.approx(0, abs=1e-9)
    assert raw == original


def test_nonconflicting_vertical_near_miss_is_not_classified_unsafe():
    raw = world(flight("A", -5, vx=1), flight("B", 5, altitude=12000, vx=-1))
    pair = report_proximity(raw)["pairs"][0]
    assert pair["native_conflict"] is False
    # Score is a flat minimum (2) across the interval, so the earliest tie wins.
    assert pair["closest_time_min"] == pytest.approx(0)
    assert pair["proximity_ratio"] == pytest.approx(2)
    assert pair["horizontal_cpa_nm"] == pytest.approx(0)
    assert pair["vertical_cpa_ft"] == pytest.approx(2000)


def test_conflict_and_near_misses_are_consistently_ranked():
    raw = world(flight("A", -5, vx=1), flight("B", 5, vx=-1),
                flight("C", 100, y=100, altitude=25000),
                flight("D", 30, altitude=20000))
    result = report_proximity(raw, limit=2)
    assert result["total_pair_count"] == 6
    assert result["returned_pair_count"] == 2
    assert result["truncated"] is True
    assert result["native_conflict_pair_count"] == 1
    assert (result["pairs"][0]["aircraft_a"], result["pairs"][0]["aircraft_b"]) == ("A", "B")
    assert result["pairs"][0]["native_conflict"] is True


def test_horizontal_and_vertical_closest_times_can_differ():
    # Horizontal passes closest at t=5, vertical reaches same level at t=0.
    raw = world(flight("A", 0, altitude=10000, vx=1, climb=0),
                flight("B", 10, altitude=10000, vx=-1, climb=1000))
    pair = report_proximity(raw)["pairs"][0]
    assert pair["horizontal_cpa_time_min"] == pytest.approx(5)
    assert pair["vertical_cpa_time_min"] == pytest.approx(0)
    assert pair["native_conflict"] is False
    assert 0 < pair["closest_time_min"] < 5
    assert pair["proximity_ratio"] > 1


def test_exact_tangent_is_not_reported_as_native_strict_conflict():
    raw = world(flight("A", 0), flight("B", 5))
    pair = report_proximity(raw)["pairs"][0]
    assert pair["proximity_ratio"] == pytest.approx(1)
    assert pair["native_conflict"] is False


def test_zero_or_one_aircraft_produces_no_pairs():
    for raw in (world(), world(flight("ONE", 0))):
        result = report_proximity(raw)
        assert result["total_pair_count"] == 0
        assert result["pairs"] == []
        assert result["truncated"] is False


def test_refuses_duplicate_ids_invalid_numbers_and_bad_arguments():
    cases = [
        world(flight("DUP", 0), flight("DUP", 5)),
        world(flight("A", 0))[:-2] + b',"aircraft": []}',
        world(flight("A", 0, vx=float("nan"))),
    ]
    for raw in cases:
        with pytest.raises((ValueError, TypeError)):
            report_proximity(raw)
    valid = world(flight("ONE", 0))
    for options in ({"limit": 0}, {"limit": True}, {"limit": MAX_PAIRS + 1},
                    {"horizon_min": 0}, {"horizon_min": 121},
                    {"horizontal_nm": -1}, {"vertical_ft": float("inf")}):
        with pytest.raises((ValueError, TypeError)):
            report_proximity(valid, **options)


def test_stdin_cli_is_a_real_read_only_consumer(tmp_path):
    raw = world(flight("A", -5, vx=1), flight("B", 5, vx=-1))
    source = tmp_path / "input.json"
    source.write_bytes(raw)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "proximity_report.py"), "-", "--limit", "1"],
        input=raw, capture_output=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    result = json.loads(proc.stdout)
    assert result["native_conflict_pair_count"] == 1
    assert result["returned_pair_count"] == 1
    assert proc.stderr == b""
    assert source.read_bytes() == raw


def test_bad_stdin_does_not_emit_partial_json():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "proximity_report.py"), "-"],
        input=b'{"invalid":true}', capture_output=True, check=False,
    )
    assert proc.returncode == 2
    assert proc.stdout == b""
    assert b"error: cannot review proximity" in proc.stderr
