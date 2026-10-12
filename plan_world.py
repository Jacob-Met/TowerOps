"""Read-only native planner review for a saved synthetic WorldState.

This command returns individually screened alternatives. It never applies an
advisory or creates approval/readback fixtures. See PLAN_WORLD.md for the input
envelope and the distinction between a completed review and a resolved world.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from advisory_options import review_advisory_options
from towerops import Aircraft, GateRejected, SafetyPolicy, WorldState

MAX_WORLD_BYTES = 262144
MAX_AIRCRAFT = 60
MAX_ABS_NUMBER = 1_000_000_000_000
MIN_POLICY_VALUE = 0.000001
MAX_VERSION = 9_007_199_254_740_991
WORLD_FIELDS = frozenset(("version", "observed_at", "aircraft"))
AIRCRAFT_NUMBERS = (
    "x_nm", "y_nm", "altitude_ft", "vx_nm_min", "vy_nm_min", "climb_ft_min",
)
AIRCRAFT_FIELDS = frozenset(("aircraft_id", *AIRCRAFT_NUMBERS))


def _number(value: Any, label: str) -> int | float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be a JSON number, not a boolean or string.")
    if abs(value) > MAX_ABS_NUMBER or (type(value) is float and not math.isfinite(value)):
        raise ValueError(f"{label} must be finite and have absolute value at most {MAX_ABS_NUMBER}.")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields are not supported.")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("Non-finite JSON constants are not supported.")


def parse_world(raw: bytes) -> WorldState:
    """Admit one complete raw world without normalizing its numeric values/IDs."""
    if not isinstance(raw, bytes):
        raise TypeError("World input must be UTF-8 bytes.")
    if len(raw) > MAX_WORLD_BYTES:
        raise ValueError(f"World input exceeds {MAX_WORLD_BYTES} bytes.")
    try:
        data = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("World input must be readable UTF-8 JSON.") from exc
    if not isinstance(data, dict) or data.keys() != WORLD_FIELDS:
        raise ValueError("World must contain exactly version, observed_at and aircraft.")
    version = data["version"]
    if type(version) is not int or not 0 <= version <= MAX_VERSION:
        raise ValueError(f"version must be a JSON integer between 0 and {MAX_VERSION}.")
    observed_at = _number(data["observed_at"], "observed_at")
    entries = data["aircraft"]
    if not isinstance(entries, list) or len(entries) > MAX_AIRCRAFT:
        raise ValueError(f"aircraft must be a list of 0 to {MAX_AIRCRAFT} entries.")
    aircraft: list[Aircraft] = []
    for index, entry in enumerate(entries):
        label = f"aircraft[{index}]"
        if not isinstance(entry, dict) or entry.keys() != AIRCRAFT_FIELDS:
            raise ValueError(f"{label} must contain aircraft_id and all six kinematic fields only.")
        identity = entry["aircraft_id"]
        if not isinstance(identity, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,10}", identity) is None:
            raise ValueError(f"{label}.aircraft_id needs 1-10 ASCII letters, digits, _ or -.")
        values = {field: _number(entry[field], f"{label}.{field}") for field in AIRCRAFT_NUMBERS}
        aircraft.append(Aircraft(identity, **values))
    # The native constructor owns exact-identity duplicate refusal.
    return WorldState(version, observed_at, tuple(aircraft))


def _check_policy(policy: SafetyPolicy) -> None:
    if not isinstance(policy, SafetyPolicy):
        raise TypeError("policy must be a native SafetyPolicy.")
    for name, value in asdict(policy).items():
        if _number(value, f"policy.{name}") < MIN_POLICY_VALUE:
            raise ValueError(f"policy.{name} must be at least {MIN_POLICY_VALUE}.")


def review_world(
    raw: bytes, now: float | None = None, policy: SafetyPolicy | None = None,
) -> dict[str, Any]:
    """Return the original native options, in native order, for the exact input."""
    state = parse_world(raw)
    policy = SafetyPolicy() if policy is None else policy
    _check_policy(policy)
    reviewed_at = state.observed_at if now is None else _number(now, "now")
    options = review_advisory_options(state, reviewed_at, policy)
    conflicting = [aircraft.aircraft_id for aircraft in policy.conflicting_aircraft(state)]
    if not conflicting:
        status = "no_conflict"
    elif options.advisories:
        status = "options_available"
    else:
        status = "no_admitted_option"
    return {
        "format": "towerops.world-plan.v1",
        "simulation_only": True,
        "proposal_only": True,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "world": state.to_dict(),
        "world_hash": options.world_hash,
        "reviewed_at": options.reviewed_at,
        "policy": asdict(policy),
        "status": status,
        "conflicting_aircraft": conflicting,
        "candidate_count": options.candidate_count,
        "advisories": [
            {**asdict(advisory), "advisory_hash": advisory.advisory_hash}
            for advisory in options.advisories
        ],
    }


def _argument_number(value: str) -> int | float:
    try:
        return _number(json.loads(value, parse_constant=_reject_constant), "argument")
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a saved synthetic WorldState with the native planner; proposals only.",
        epilog="See PLAN_WORLD.md. No approval, readback, actuation, network or input-file write.",
    )
    parser.add_argument("world", help="Raw WorldState JSON path, or - to read stdin")
    parser.add_argument("--now", type=_argument_number, help="Synthetic review seconds; default: observed_at")
    defaults = SafetyPolicy()
    parser.add_argument(
        "--horizontal-nm", type=_argument_number, default=defaults.min_horizontal_nm,
        help=f"Horizontal separation minimum in nautical miles (default: {defaults.min_horizontal_nm})",
    )
    parser.add_argument(
        "--vertical-ft", type=_argument_number, default=defaults.min_vertical_ft,
        help=f"Vertical separation minimum in feet (default: {defaults.min_vertical_ft})",
    )
    parser.add_argument(
        "--horizon-min", type=_argument_number, default=defaults.horizon_min,
        help=f"Projection horizon in minutes (default: {defaults.horizon_min})",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Write a standalone offline alternative review instead of JSON",
    )
    args = parser.parse_args(argv)
    try:
        policy = replace(
            defaults, min_horizontal_nm=args.horizontal_nm,
            min_vertical_ft=args.vertical_ft, horizon_min=args.horizon_min,
        )
        _check_policy(policy)
        if args.world == "-":
            raw = sys.stdin.buffer.read(MAX_WORLD_BYTES + 1)
        else:
            with Path(args.world).open("rb") as stream:
                raw = stream.read(MAX_WORLD_BYTES + 1)
        result = review_world(raw, args.now, policy)
        output = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        if args.html:
            from world_plan_html import render_plan_html

            output = render_plan_html(output)
    except GateRejected as exc:
        print(f"error: native review refused: {exc.reason}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"error: cannot review world: {exc}", file=sys.stderr)
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
