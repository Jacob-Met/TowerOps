"""Reproducible synthetic WorldState fixtures for native TowerOps consumers.

All traffic is invented for research simulations. A seeded SHA-256 stream makes
fixture generation independent of Python's random-module implementation.
The unmodified native parser and conflict policy qualify every produced world.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from typing import Any

from plan_world import MAX_ABS_NUMBER, MAX_VERSION, parse_world
from towerops import SafetyPolicy

MAX_SEED = (1 << 64) - 1
MAX_AIRCRAFT = 60
MIN_AIRCRAFT = 2
MODES = ("encounter", "clear")


class _SeedStream:
    """Stable, labeled uniform integer draws for a 64-bit user seed."""

    def __init__(self, seed: int) -> None:
        self.key = seed.to_bytes(8, "big")
        self.counter = 0

    def draw(self, low: int, high: int) -> int:
        payload = self.key + self.counter.to_bytes(8, "big")
        self.counter += 1
        number = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
        return low + number % (high - low + 1)


def _number(value: Any, label: str) -> int | float:
    if type(value) not in (int, float) or (
        type(value) is float and not math.isfinite(value)
    ) or abs(value) > MAX_ABS_NUMBER:
        raise ValueError(f"{label} must be a finite number of absolute value at most {MAX_ABS_NUMBER}")
    return value


def _integer(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}")
    return value


def synthesize_world(
    seed: int,
    aircraft_count: int = 2,
    mode: str = "encounter",
    observed_at: float = 1000.0,
    version: int = 1,
) -> dict[str, Any]:
    """Make one bounded, native-admitted simulated world.

    ``encounter`` has a conflict in the default native five-minute policy;
    ``clear`` has none. Every synthesized aircraft is part of one independent
    WorldState; no approved action or real traffic is involved.
    """
    _integer(seed, "seed", 0, MAX_SEED)
    _integer(aircraft_count, "aircraft_count", MIN_AIRCRAFT, MAX_AIRCRAFT)
    _integer(version, "version", 0, MAX_VERSION)
    _number(observed_at, "observed_at")
    if type(mode) is not str or mode not in MODES:
        raise ValueError("mode must be 'encounter' or 'clear'")

    rng = _SeedStream(seed)
    center_x = rng.draw(-100, 100)
    center_y = rng.draw(-100, 100)
    altitude = rng.draw(8, 16) * 1000
    along_x = rng.draw(0, 1) == 0
    # The two aircraft start 20 NM apart and have 4 NM/min relative speed.
    # Closing means they coincide at minute 5; diverging means no approach.
    # These are synthetic test geometries, not real-world flight plans.
    movement = 2 if mode == "encounter" else -2

    def flight(identity: str, x: int, y: int, vx: int, vy: int, alt: int) -> dict[str, Any]:
        return {
            "aircraft_id": identity,
            "x_nm": x,
            "y_nm": y,
            "altitude_ft": alt,
            "vx_nm_min": vx,
            "vy_nm_min": vy,
            "climb_ft_min": 0,
        }

    if along_x:
        a = flight("SYN00", center_x - 10, center_y, movement, 0, altitude)
        b = flight("SYN01", center_x + 10, center_y, -movement, 0, altitude)
    else:
        a = flight("SYN00", center_x, center_y - 10, 0, movement, altitude)
        b = flight("SYN01", center_x, center_y + 10, 0, -movement, altitude)
    aircraft = [a, b]
    for i in range(2, aircraft_count):
        # Background tracks are > 100 NM apart horizontally even after all
        # permitted 5-minute motion, so only the authored primary pair can
        # create a default-policy conflict. Never modify the primary pair.
        aircraft.append(flight(
            f"SYN{i:02d}",
            center_x + 1000 + 120 * (i - 2),
            center_y + rng.draw(-50, 50),
            rng.draw(-2, 2),
            rng.draw(-2, 2),
            rng.draw(8, 16) * 1000,
        ))

    candidate = {"version": version, "observed_at": observed_at, "aircraft": aircraft}
    encoded = (json.dumps(candidate, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    state = parse_world(encoded)
    if SafetyPolicy().state_has_conflict(state) != (mode == "encounter"):
        raise RuntimeError("generated traffic did not match its native conflict label")
    return state.to_dict()


def _cli_integer(value: str, label: str, low: int, high: int) -> int:
    try:
        return _integer(int(value, 10), label, low, high)
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _cli_number(value: str) -> int | float:
    try:
        number = json.loads(value)
        return _number(number, "observed_at")
    except (ValueError, TypeError, OverflowError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a reproducible, fully synthetic native TowerOps world as JSON.",
        epilog="Research simulator only; pipe stdout to plan_world.py or save to a new file.",
    )
    parser.add_argument("--seed", required=True, type=lambda v: _cli_integer(v, "seed", 0, MAX_SEED))
    parser.add_argument("--aircraft-count", type=lambda v: _cli_integer(v, "aircraft_count", 2, 60), default=2)
    parser.add_argument("--mode", choices=MODES, default="encounter")
    parser.add_argument("--observed-at", type=_cli_number, default=1000.0)
    parser.add_argument("--version", type=lambda v: _cli_integer(v, "version", 0, MAX_VERSION), default=1)
    args = parser.parse_args(argv)
    try:
        world = synthesize_world(args.seed, args.aircraft_count, args.mode, args.observed_at, args.version)
        output = json.dumps(world, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n"
    except (OSError, TypeError, ValueError, OverflowError, RuntimeError, RecursionError) as error:
        print(f"error: cannot synthesize world: {error}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        print(f"error: cannot write world: {error}", file=sys.stderr)
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
