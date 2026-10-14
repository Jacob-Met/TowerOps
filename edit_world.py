"""Author one explicit synthetic aircraft edit into a new raw WorldState file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path

from plan_world import (
    AIRCRAFT_NUMBERS, MAX_VERSION, _argument_number, _number,
    _read_world_file, parse_world,
)
from towerops import canonical_bytes


def _changed_fields(before, after) -> list[str]:
    return [
        field for field in AIRCRAFT_NUMBERS
        if canonical_bytes(getattr(before, field)) != canonical_bytes(getattr(after, field))
    ]


def edit_world(raw: bytes, aircraft_id: str, changes: dict[str, int | float]) -> bytes:
    """Keep source order/time and use native version+1 for one exact-ID edit.

    This authors a counterfactual only. It does not screen the resulting world
    or carry forward any prior plan, approval, freshness or safety conclusion.
    """
    source = parse_world(raw)
    if not isinstance(aircraft_id, str):
        raise TypeError("aircraft_id must be an exact string ID.")
    try:
        original = source.get(aircraft_id)
    except KeyError as exc:
        raise ValueError(f"Unknown aircraft_id: {aircraft_id!r}.") from exc
    if type(changes) is not dict or not changes:
        raise ValueError("Supply a nonempty dictionary of explicit aircraft fields.")
    if any(field not in AIRCRAFT_NUMBERS for field in changes):
        raise ValueError("Only the six native numeric aircraft fields may be edited.")
    for field, value in changes.items():
        _number(value, field)
    updated = replace(original, **changes)
    if not _changed_fields(original, updated):
        raise ValueError("Change at least one aircraft field's native representation.")
    if source.version >= MAX_VERSION:
        raise ValueError("The source version cannot be incremented within the native limit.")
    edited = source.replace_aircraft(updated, observed_at=source.observed_at)
    # Native to_dict sorts aircraft. Authoring must preserve the admitted tuple order.
    result = {
        "version": edited.version,
        "observed_at": edited.observed_at,
        "aircraft": [asdict(aircraft) for aircraft in edited.aircraft],
    }
    output = (json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    parse_world(output)
    return output


class _OneFieldValue(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"{option_string} may be supplied only once")
        setattr(namespace, self.dest, values)


def _write_new(path: Path, data: bytes) -> None:
    # Refuse existing entries before opening, including a dangling link. The
    # exclusive create separately protects against an ordinary intervening file.
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(f"Output already exists: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o666)
    try:
        stream = os.fdopen(descriptor, "wb")
        descriptor = None
        with stream:
            stream.write(data)
            stream.flush()
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _diagnostic(message: str) -> None:
    try:
        sys.stderr.write("error: " + message + "\n")
        sys.stderr.flush()
    except (OSError, UnicodeError):
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Edit one exact aircraft in a saved synthetic world; create a new WorldState file.",
        epilog="See EDIT_WORLD.md. No planning, time advance, approval, actuation or input-file write.",
    )
    parser.add_argument("world", help="One saved raw WorldState JSON file")
    parser.add_argument("--aircraft", required=True, help="Exact existing case-sensitive aircraft ID")
    parser.add_argument("--out", required=True, help="New output path; parent directory must exist")
    for field in AIRCRAFT_NUMBERS:
        parser.add_argument(
            "--" + field.replace("_", "-"), dest=field, type=_argument_number,
            action=_OneFieldValue, default=None, metavar="JSON_NUMBER",
            help=f"Replace {field}; retain the original value when omitted",
        )
    args = parser.parse_args(argv)
    changes = {field: getattr(args, field) for field in AIRCRAFT_NUMBERS if getattr(args, field) is not None}
    if not changes:
        parser.error("supply at least one aircraft field option")
    try:
        raw = _read_world_file(Path(args.world))
        output = edit_world(raw, args.aircraft, changes)
        before, after = parse_world(raw), parse_world(output)
        receipt = {
            "format": "towerops.world-edit-created.v1",
            "source": {"path": args.world, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
            "output": {"path": args.out, "bytes": len(output), "sha256": hashlib.sha256(output).hexdigest()},
            "aircraft_id": args.aircraft,
            "changed_fields": _changed_fields(before.get(args.aircraft), after.get(args.aircraft)),
            "source_version": before.version,
            "version": after.version,
            "observed_at": after.observed_at,
        }
        text = json.dumps(receipt, allow_nan=False) + "\n"
        _write_new(Path(args.out), output)
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        _diagnostic(f"cannot create edited world: {exc}")
        return 2
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except (OSError, UnicodeError) as exc:
        _diagnostic(f"edited world was saved, but its receipt could not be delivered: {exc}")
        # This failed CLI stream cannot be flushed again successfully at shutdown.
        try:
            sys.stdout.close()
        except (OSError, UnicodeError):
            pass
        sys.stdout = None
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
