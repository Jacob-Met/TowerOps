"""Extract one raw synthetic world from a completely replayed Explorer export."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from plan_world import parse_world
from scenarios import replay_result

MAX_EXPORT_BYTES = 262144


class ReplayMismatch(ValueError):
    """The saved result differs from the complete native fixture replay."""


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON fields are not supported.")
        value[key] = item
    return value


def _constant(_value: str) -> None:
    raise ValueError("Non-finite JSON constants are not supported.")


def extract_world(raw: bytes, phase: str) -> dict[str, Any]:
    """Return the selected decoded world only after complete replay and admission.

    The input is a saved fixed-fixture Explorer result, not arbitrary traffic.
    Native replay recomputes that fixture; it proves local reproducibility only.
    The returned object is decoded from this call's bytes and has no caller-owned
    input graph. Numeric values and aircraft order come from the selected export.
    """
    if phase not in ("before", "after") or type(phase) is not str:
        raise ValueError("phase must be before or after.")
    if not isinstance(raw, bytes):
        raise TypeError("Explorer input must be UTF-8 bytes.")
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError(f"Explorer input exceeds {MAX_EXPORT_BYTES} bytes.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                           parse_constant=_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Explorer input must be readable UTF-8 JSON.") from exc
    replay = replay_result(value)
    if not replay["matches"]:
        raise ReplayMismatch("Saved Explorer result does not match complete native replay.")
    selected = value[phase]
    # Keep the existing native raw-world contract as the receiving boundary.
    parse_world(json.dumps(selected, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    return selected


def _read_export(path: Path) -> bytes:
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Explorer input path must resolve to a regular file.")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
                         | getattr(os, "O_BINARY", 0))
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Opened Explorer input is not a regular file.")
        if info.st_size > MAX_EXPORT_BYTES:
            raise ValueError(f"Explorer input exceeds {MAX_EXPORT_BYTES} bytes.")
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        with stream:
            return stream.read(MAX_EXPORT_BYTES + 1)
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reuse the before or after world from a verified synthetic Explorer export.",
        epilog="Fixed local replay only. See EXPLORER_WORLD.md; no live inputs or authority.",
    )
    parser.add_argument("export", help="Saved Explorer JSON path, or - for stdin")
    parser.add_argument("--phase", required=True, choices=("before", "after"),
                        help="Explicitly choose the saved world to emit")
    args = parser.parse_args(argv)
    try:
        raw = (sys.stdin.buffer.read(MAX_EXPORT_BYTES + 1) if args.export == "-"
               else _read_export(Path(args.export)))
        world = extract_world(raw, args.phase)
        output = json.dumps(world, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    except ReplayMismatch as exc:
        print(f"error: replay mismatch: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
        print(f"error: cannot extract world: {exc}", file=sys.stderr)
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
