"""Explain one saved synthetic encounter without planning or changing the world."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from plan_world import MAX_WORLD_BYTES, _argument_number, _check_policy, _number, parse_world
from towerops import Aircraft, SafetyPolicy


def _separation(
    first: Aircraft, second: Aircraft, policy: SafetyPolicy, minutes: int | float,
) -> dict[str, Any]:
    # Use relative motion, as the existing browser encounter consumer does.
    # Large shared motion must not erase the pair's initial separation.
    horizontal = math.hypot(
        first.x_nm - second.x_nm + (first.vx_nm_min - second.vx_nm_min) * minutes,
        first.y_nm - second.y_nm + (first.vy_nm_min - second.vy_nm_min) * minutes,
    )
    vertical = abs(
        first.altitude_ft - second.altitude_ft
        + (first.climb_ft_min - second.climb_ft_min) * minutes
    )
    horizontal_below = horizontal < policy.min_horizontal_nm
    vertical_below = vertical < policy.min_vertical_ft
    return {
        "minutes": minutes,
        "horizontal_nm": horizontal,
        "vertical_ft": vertical,
        "horizontal_below": horizontal_below,
        "vertical_below": vertical_below,
        "simultaneous": horizontal_below and vertical_below,
    }


def inspect_encounter(
    raw: bytes, first: str, second: str, *,
    at_min: int | float = 0, policy: SafetyPolicy | None = None,
) -> dict[str, Any]:
    """Explain a chosen pair using the unchanged native analytical intervals.

    The cursor is minutes after the saved observation, not a new observation
    clock or a freshness/approval check. No planner or ControlRoom is executed.
    """
    state = parse_world(raw)
    policy = SafetyPolicy() if policy is None else policy
    _check_policy(policy)
    minutes = _number(at_min, "at_min")
    if not 0 <= minutes <= policy.horizon_min:
        raise ValueError("at_min must be between zero and the projection horizon.")
    if not isinstance(first, str) or not isinstance(second, str):
        raise TypeError("Pair identifiers must be strings.")
    if first == second:
        raise ValueError("Choose two different aircraft identifiers.")
    try:
        a, b = state.get(first), state.get(second)
    except KeyError as exc:
        raise ValueError(f"Aircraft identifier is absent from the saved world: {exc.args[0]!r}.") from exc

    dx, dy = a.x_nm - b.x_nm, a.y_nm - b.y_nm
    dvx, dvy = a.vx_nm_min - b.vx_nm_min, a.vy_nm_min - b.vy_nm_min
    horizontal = policy._horizontal_unsafe_interval(
        dx, dy, dvx, dvy, policy.min_horizontal_nm, policy.horizon_min,
    )
    vertical = policy._linear_abs_unsafe_interval(
        a.altitude_ft - b.altitude_ft, a.climb_ft_min - b.climb_ft_min,
        policy.min_vertical_ft, policy.horizon_min,
    )
    overlap = None
    if horizontal is not None and vertical is not None:
        start, end = max(horizontal[0], vertical[0]), min(horizontal[1], vertical[1])
        if start < end:
            overlap = (start, end)
    speed_squared = dvx * dvx + dvy * dvy
    closest = (
        0 if speed_squared == 0
        else min(policy.horizon_min, max(0, -(dx * dvx + dy * dvy) / speed_squared))
    )
    return {
        "format": "towerops.encounter.v1",
        "simulation_only": True,
        "forecast_only": True,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "world": state.to_dict(),
        "world_hash": state.world_hash,
        "policy": asdict(policy),
        "aircraft_a": first,
        "aircraft_b": second,
        "horizontal_window_min": horizontal,
        "vertical_window_min": vertical,
        "overlap_window_min": overlap,
        "native_pair_conflict": policy._pair_conflict(a, b),
        "closest_horizontal": _separation(a, b, policy, closest),
        "cursor": _separation(a, b, policy, minutes),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explain a saved synthetic pair using native analytical separation windows.",
        epilog="See INSPECT_ENCOUNTER.md. Constant-rate forecast only; no planner, actuation or file write.",
    )
    parser.add_argument("world", help="Raw WorldState JSON path, or - to read stdin")
    parser.add_argument("first", help="Exact first aircraft identifier (case-sensitive)")
    parser.add_argument("second", help="Exact second aircraft identifier (case-sensitive)")
    parser.add_argument(
        "--at-min", type=_argument_number, default=0,
        help="Cursor minutes after the saved observation, within the horizon (default: 0)",
    )
    defaults = SafetyPolicy()
    parser.add_argument(
        "--horizontal-nm", type=_argument_number, default=defaults.min_horizontal_nm,
        help=f"Horizontal minimum in nautical miles (default: {defaults.min_horizontal_nm})",
    )
    parser.add_argument(
        "--vertical-ft", type=_argument_number, default=defaults.min_vertical_ft,
        help=f"Vertical minimum in feet (default: {defaults.min_vertical_ft})",
    )
    parser.add_argument(
        "--horizon-min", type=_argument_number, default=defaults.horizon_min,
        help=f"Projection horizon in minutes (default: {defaults.horizon_min})",
    )
    args = parser.parse_args(argv)
    try:
        policy = replace(
            defaults, min_horizontal_nm=args.horizontal_nm,
            min_vertical_ft=args.vertical_ft, horizon_min=args.horizon_min,
        )
        if args.world == "-":
            raw = sys.stdin.buffer.read(MAX_WORLD_BYTES + 1)
        else:
            with Path(args.world).open("rb") as stream:
                raw = stream.read(MAX_WORLD_BYTES + 1)
        result = inspect_encounter(raw, args.first, args.second, at_min=args.at_min, policy=policy)
        output = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"error: cannot inspect encounter: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except OSError as exc:
        print(f"error: cannot write report: {exc}", file=sys.stderr)
        try:
            sys.stdout.close()
        except OSError:
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
