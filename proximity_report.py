"""Read-only proximity ranking for an explicitly supplied synthetic TowerOps world.

This is a diagnostic scenario-authoring tool, never a safety gate. The native
SafetyPolicy remains the sole source of projected-conflict classification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from plan_world import (
    MAX_AIRCRAFT,
    MAX_WORLD_BYTES,
    _argument_number,
    _check_policy,
    _read_world_file,
    parse_world,
)
from towerops import Aircraft, SafetyPolicy

MAX_PAIRS = MAX_AIRCRAFT * (MAX_AIRCRAFT - 1) // 2
MAX_HORIZON_MIN = 120.0


def _clamp(value: float, horizon: float) -> float:
    return min(horizon, max(0.0, value))


def _proximity(a: Aircraft, b: Aircraft, horizon: float, horizontal: float,
               vertical: float) -> dict[str, float]:
    """Find the minimum simultaneous normalized horizontal/vertical distance.

    max(horizontal_distance / horizontal_limit, vertical_distance / vertical_limit)
    is convex in time for constant-velocity tracks. Ternary search on [0,H]
    is a read-only diagnostic approximation; boundary and separate horizontal/
    vertical extrema are checked too. It MUST NOT classify native conflicts.
    """
    dx, dy = a.x_nm - b.x_nm, a.y_nm - b.y_nm
    dz = a.altitude_ft - b.altitude_ft
    dvx, dvy = a.vx_nm_min - b.vx_nm_min, a.vy_nm_min - b.vy_nm_min
    dvz = a.climb_ft_min - b.climb_ft_min

    def distances(t: float) -> tuple[float, float]:
        return math.hypot(dx + dvx * t, dy + dvy * t), abs(dz + dvz * t)

    def score(t: float) -> float:
        h, v = distances(t)
        return max(h / horizontal, v / vertical)

    speed_sq = dvx * dvx + dvy * dvy
    h_time = _clamp(-(dx * dvx + dy * dvy) / speed_sq, horizon) if speed_sq else 0.0
    v_time = _clamp(-dz / dvz, horizon) if dvz else 0.0

    left, right = 0.0, horizon
    for _ in range(96):
        first = left + (right - left) / 3.0
        second = right - (right - left) / 3.0
        if score(first) <= score(second):
            right = second
        else:
            left = first

    best_time = min((0.0, horizon, h_time, v_time, (left + right) / 2.0),
                    key=lambda t: (score(t), t))
    h_best, v_best = distances(best_time)
    return {
        "closest_time_min": best_time,
        "proximity_ratio": score(best_time),
        "horizontal_nm_at_closest": h_best,
        "vertical_ft_at_closest": v_best,
        "horizontal_cpa_time_min": h_time,
        "horizontal_cpa_nm": distances(h_time)[0],
        "vertical_cpa_time_min": v_time,
        "vertical_cpa_ft": distances(v_time)[1],
    }


def report_proximity(raw: bytes, *, horizontal_nm: float = 5.0,
                     vertical_ft: float = 1000.0, horizon_min: float = 5.0,
                     limit: int = 20) -> dict[str, Any]:
    """Rank native pairs by actual conflict first, then diagnostic proximity.

    Input bytes are not changed. Results use exact native aircraft identities;
    a tied proximity score is ordered by the pair of callsigns.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_PAIRS:
        raise ValueError(f"limit must be an integer from 1 to {MAX_PAIRS}.")
    policy = replace(
        SafetyPolicy(), min_horizontal_nm=horizontal_nm,
        min_vertical_ft=vertical_ft, horizon_min=horizon_min,
    )
    _check_policy(policy)
    if policy.horizon_min > MAX_HORIZON_MIN:
        raise ValueError(f"horizon_min must be at most {MAX_HORIZON_MIN} minutes.")
    state = parse_world(raw)
    aircraft = sorted(state.aircraft, key=lambda a: a.aircraft_id)
    rows: list[dict[str, Any]] = []
    for i, a in enumerate(aircraft):
        for b in aircraft[i + 1:]:
            metrics = _proximity(a, b, policy.horizon_min,
                                 policy.min_horizontal_nm, policy.min_vertical_ft)
            rows.append({
                "aircraft_a": a.aircraft_id,
                "aircraft_b": b.aircraft_id,
                "native_conflict": policy._pair_conflict(a, b),
                **metrics,
            })
    rows.sort(key=lambda row: (
        not row["native_conflict"], row["proximity_ratio"],
        row["aircraft_a"], row["aircraft_b"],
    ))
    total = len(rows)
    return {
        "format": "towerops.proximity-report.v1",
        "simulation_only": True,
        "proposal_only": True,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "world_hash": state.world_hash,
        "world_version": state.version,
        "observed_at": state.observed_at,
        "horizon_min": policy.horizon_min,
        "thresholds": {
            "horizontal_nm": policy.min_horizontal_nm,
            "vertical_ft": policy.min_vertical_ft,
        },
        "total_pair_count": total,
        "native_conflict_pair_count": sum(row["native_conflict"] for row in rows),
        "returned_pair_count": min(limit, total),
        "truncated": total > limit,
        "pairs": rows[:limit],
        "diagnostic_note": "Proximity ratio is not a safety decision. Native conflict classification uses SafetyPolicy; no proposal is screened or applied.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rank synthetic traffic pairs by native conflict and closest normalized proximity.",
        epilog="Read-only diagnostic, not aviation assurance. See PROXIMITY_REPORT.md.",
    )
    parser.add_argument("world", help="Raw saved WorldState JSON path or - for stdin")
    parser.add_argument("--horizontal-nm", type=_argument_number, default=5.0)
    parser.add_argument("--vertical-ft", type=_argument_number, default=1000.0)
    parser.add_argument("--horizon-min", type=_argument_number, default=5.0)
    parser.add_argument("--limit", type=int, default=20, help=f"Return 1..{MAX_PAIRS} pairs, default 20")
    args = parser.parse_args(argv)
    try:
        raw = (sys.stdin.buffer.read(MAX_WORLD_BYTES + 1) if args.world == "-"
               else _read_world_file(Path(args.world)))
        report = report_proximity(
            raw, horizontal_nm=args.horizontal_nm, vertical_ft=args.vertical_ft,
            horizon_min=args.horizon_min, limit=args.limit,
        )
        output = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"error: cannot review proximity: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except (OSError, UnicodeError) as exc:
        print(f"error: cannot write proximity report: {exc}", file=sys.stderr)
        try:
            sys.stdout.close()
        except (OSError, UnicodeError):
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
