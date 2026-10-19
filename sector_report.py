"""Read-only rectangular sector contact intervals for synthetic TowerOps worlds.

A straight, constant-velocity track has at most one contiguous contact interval
with a closed, axis-aligned rectangle. This deliberately does not invoke the
planner, issue a clearance, or modify a world.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

# Keep CLI geometry inputs within the saved-world parser's numerical envelope.
MAX_ABS_NUMBER = 1_000_000_000_000


def axis_interval(position: float, velocity: float, lower: float, upper: float) -> tuple[float, float] | None:
    """Closed interval of minutes inside [lower, upper], unbounded in time."""
    if velocity == 0:
        return (-math.inf, math.inf) if lower <= position <= upper else None
    first = (lower - position) / velocity
    second = (upper - position) / velocity
    return (min(first, second), max(first, second))


def sector_interval(
    x_nm: float,
    y_nm: float,
    vx_nm_min: float,
    vy_nm_min: float,
    west_nm: float,
    east_nm: float,
    south_nm: float,
    north_nm: float,
    horizon_min: float,
) -> tuple[float, float] | None:
    """Inclusive [entry, exit] minute offsets; a point contact is permitted.

    Inputs are admitted at the CLI/report boundary. This lower-level geometry
    function assumes finite, ordered bounds and nonnegative finite horizon.
    """
    east_west = axis_interval(x_nm, vx_nm_min, west_nm, east_nm)
    north_south = axis_interval(y_nm, vy_nm_min, south_nm, north_nm)
    if east_west is None or north_south is None:
        return None
    start = max(0.0, east_west[0], north_south[0])
    finish = min(float(horizon_min), east_west[1], north_south[1])
    return (start, finish) if start <= finish else None


def sector_report(
    raw: bytes,
    *,
    west_nm: float,
    east_nm: float,
    south_nm: float,
    north_nm: float,
    horizon_min: float = 5.0,
) -> dict[str, Any]:
    """Admit a real native world and report contacts without mutating it."""
    from plan_world import parse_world

    for label, value in (
        ("west_nm", west_nm), ("east_nm", east_nm),
        ("south_nm", south_nm), ("north_nm", north_nm),
        ("horizon_min", horizon_min),
    ):
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > MAX_ABS_NUMBER:
            raise ValueError(f"{label} must be a finite JSON number with absolute value at most {MAX_ABS_NUMBER}.")
    if west_nm >= east_nm or south_nm >= north_nm:
        raise ValueError("Sector must have west < east and south < north.")
    if horizon_min < 0:
        raise ValueError("horizon_min must be nonnegative.")

    state = parse_world(raw)
    tracks: list[dict[str, Any]] = []
    for aircraft in state.aircraft:
        interval = sector_interval(
            aircraft.x_nm, aircraft.y_nm, aircraft.vx_nm_min, aircraft.vy_nm_min,
            west_nm, east_nm, south_nm, north_nm, horizon_min,
        )
        if interval is None:
            continue
        entry, exit_ = interval
        tracks.append({
            "aircraft_id": aircraft.aircraft_id,
            "entry_after_min": entry,
            "exit_after_min": exit_,
            "inside_at_observation": west_nm <= aircraft.x_nm <= east_nm and south_nm <= aircraft.y_nm <= north_nm,
            "contact_only": entry == exit_,
        })
    tracks.sort(key=lambda track: (track["entry_after_min"], track["aircraft_id"]))
    return {
        "format": "towerops.sector-report.v1",
        "simulation_only": True,
        "read_only": True,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "world_hash": state.world_hash,
        "world_version": state.version,
        "observed_at": state.observed_at,
        "sector": {"west_nm": west_nm, "east_nm": east_nm, "south_nm": south_nm, "north_nm": north_nm},
        "horizon_min": horizon_min,
        "contacts": tracks,
        "contact_count": len(tracks),
    }


def _argument_number(value: str) -> int | float:
    try:
        parsed = json.loads(value, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite number")))
        if type(parsed) not in (int, float) or not math.isfinite(parsed) or abs(parsed) > MAX_ABS_NUMBER:
            raise ValueError("expected a finite JSON number within the input envelope")
        return parsed
    except (ValueError, TypeError, RecursionError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report read-only sector contacts in a saved synthetic TowerOps world.",
        epilog="No real traffic feed, planning, safety assurance, approval or actuation.",
    )
    parser.add_argument("world", help="Raw WorldState JSON file, or - for stdin")
    parser.add_argument("--west-nm", type=_argument_number, required=True)
    parser.add_argument("--east-nm", type=_argument_number, required=True)
    parser.add_argument("--south-nm", type=_argument_number, required=True)
    parser.add_argument("--north-nm", type=_argument_number, required=True)
    parser.add_argument("--horizon-min", type=_argument_number, default=5)
    args = parser.parse_args(argv)
    try:
        # Import the existing bounded regular-file reader only after parsing
        # arguments. The stdin path uses the same maximum read length.
        from plan_world import MAX_WORLD_BYTES, _read_world_file

        raw = sys.stdin.buffer.read(MAX_WORLD_BYTES + 1) if args.world == "-" else _read_world_file(Path(args.world))
        result = sector_report(
            raw, west_nm=args.west_nm, east_nm=args.east_nm,
            south_nm=args.south_nm, north_nm=args.north_nm,
            horizon_min=args.horizon_min,
        )
        output = json.dumps(result, allow_nan=False, ensure_ascii=False, indent=2) + "\n"
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"error: cannot inspect sector: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except OSError as exc:
        print(f"error: cannot write sector report: {exc}", file=sys.stderr)
        try:
            sys.stdout.close()
        except OSError:
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
