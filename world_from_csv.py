"""Author a synthetic raw WorldState from explicitly denominated CSV rows."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from plan_world import AIRCRAFT_NUMBERS, MAX_AIRCRAFT, MAX_WORLD_BYTES, parse_world
from towerops import WorldState

COLUMNS = ("aircraft_id", *AIRCRAFT_NUMBERS)


def _json_number(text: str, label: str) -> int | float:
    try:
        value = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise ValueError(f"{label} must contain a JSON number.") from exc
    if type(value) not in (int, float):
        raise ValueError(f"{label} must contain a JSON number.")
    return value


def world_from_csv(raw: bytes, *, observed_at: float, version: int = 0) -> WorldState:
    """Read every row, then admit the complete world through the native consumer.

    The header may reorder the seven exact native column names. Numeric cells
    follow JSON number interpretation; identity cells are never trimmed or
    normalized. Native WorldState serialization sorts aircraft by exact ID.
    """
    if not isinstance(raw, bytes):
        raise TypeError("CSV input must be UTF-8 bytes.")
    if len(raw) > MAX_WORLD_BYTES:
        raise ValueError(f"CSV input exceeds {MAX_WORLD_BYTES} bytes.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ValueError("CSV input must be readable UTF-8.") from exc
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, None)
        if header is None or len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
            raise ValueError("CSV header must contain each of these columns once: " + ",".join(COLUMNS))
        aircraft = []
        for index, row in enumerate(reader, 1):
            if index > MAX_AIRCRAFT:
                raise ValueError(f"CSV must contain at most {MAX_AIRCRAFT} aircraft records.")
            if len(row) != len(COLUMNS):
                raise ValueError(f"CSV record {index} must contain exactly {len(COLUMNS)} cells.")
            entry = dict(zip(header, row))
            for field in AIRCRAFT_NUMBERS:
                entry[field] = _json_number(entry[field], f"CSV record {index}.{field}")
            aircraft.append(entry)
    except csv.Error as exc:
        raise ValueError(f"Cannot read CSV near physical line {reader.line_num}: {exc}") from exc
    # No second world schema, normalization, policy or decision path is added.
    encoded = json.dumps(
        {"version": version, "observed_at": observed_at, "aircraft": aircraft},
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return parse_world(encoded)


def _argument_number(text: str) -> int | float:
    try:
        return _json_number(text, "argument")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert synthetic aircraft CSV into native raw WorldState JSON.",
        epilog="See WORLD_FROM_CSV.md. No policy, approval, actuation or input-file write.",
    )
    parser.add_argument("csv", help="UTF-8 CSV path, or - to read stdin")
    parser.add_argument("--observed-at", required=True, type=_argument_number, help="Explicit synthetic observation seconds")
    parser.add_argument("--version", type=_argument_number, default=0, help="Native nonnegative integer revision (default: 0)")
    args = parser.parse_args(argv)
    try:
        if args.csv == "-":
            raw = sys.stdin.buffer.read(MAX_WORLD_BYTES + 1)
        else:
            with Path(args.csv).open("rb") as stream:
                raw = stream.read(MAX_WORLD_BYTES + 1)
        world = world_from_csv(raw, observed_at=args.observed_at, version=args.version)
        output = json.dumps(world.to_dict(), ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"error: cannot convert traffic CSV: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except OSError as exc:
        print(f"error: cannot write world: {exc}", file=sys.stderr)
        try:
            sys.stdout.close()
        except OSError:
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
