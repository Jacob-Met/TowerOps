"""Bounded literal differences for the local synthetic Explorer replay command."""
import copy
import json
import math
import os
from pathlib import Path
import stat
import sys

from scenarios import json_equivalent, replay_result, run_scenario

DIFFERENCE_LIMIT = 32
_MISSING = object()


def _json_type(value):
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) in (int, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise TypeError("Expected a JSON value")


def _side(value):
    if value is _MISSING:
        return {"present": False}
    return {"present": True, "type": _json_type(value), "value": value}


def _pointer(parent, key):
    return parent + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _walk(expected, actual, pointer=""):
    if expected is _MISSING or actual is _MISSING:
        yield {
            "path": pointer,
            "kind": "unexpected" if expected is _MISSING else "missing",
            "expected": _side(expected),
            "actual": _side(actual),
        }
        return
    if json_equivalent(expected, actual):
        return
    expected_type, actual_type = _json_type(expected), _json_type(actual)
    if expected_type != actual_type:
        yield {"path": pointer, "kind": "type",
               "expected": _side(expected), "actual": _side(actual)}
    elif isinstance(expected, dict):
        for key in sorted(expected.keys() | actual.keys()):
            yield from _walk(expected.get(key, _MISSING),
                             actual.get(key, _MISSING), _pointer(pointer, key))
    elif isinstance(expected, list):
        for index in range(max(len(expected), len(actual))):
            left = expected[index] if index < len(expected) else _MISSING
            right = actual[index] if index < len(actual) else _MISSING
            yield from _walk(left, right, _pointer(pointer, index))
    else:
        yield {"path": pointer, "kind": "value",
               "expected": _side(expected), "actual": _side(actual)}


def explain_replay(value):
    """Return the ordinary replay reply plus at most 32 detached differences.

    Input is a finite decoded JSON export. This describes local reproduction,
    not provenance, causation or authority. Numeric comparison stays with the
    maintained Explorer comparator.
    """
    # Refuse nonfinite or excessively deep values before computing a report.
    json.dumps(value, allow_nan=False)
    actual = copy.deepcopy(value)
    reply = replay_result(actual)
    expected = run_scenario(**actual["request"])
    differences = []
    truncated = False
    for difference in _walk(expected, actual):
        if len(differences) == DIFFERENCE_LIMIT:
            truncated = True
            break
        differences.append(difference)
    return {**reply, "difference_limit": DIFFERENCE_LIMIT,
            "differences": differences, "differences_truncated": truncated}


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("Non-finite JSON numbers are not supported")
    return value


def _reject_constant(_text):
    raise ValueError("Non-finite JSON numbers are not supported")


def _read_export(path, max_bytes):
    # The descriptor check avoids consuming devices or pipes. It does not
    # promise exclusion of concurrent regular-file writers or directory races.
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Replay explanation requires a regular file")
        with os.fdopen(fd, "rb") as source:
            fd = None
            raw = source.read(max_bytes + 1)
    finally:
        if fd is not None:
            os.close(fd)
    if len(raw) > max_bytes:
        raise ValueError(f"Export exceeds {max_bytes} bytes")
    return json.loads(raw.decode("utf-8"), parse_float=_finite_float,
                      parse_constant=_reject_constant)


def run_explanation(path: Path, max_bytes: int, stdout=None, stderr=None):
    """Deliver one complete prepared report; 0 match, 1 mismatch, 2 refusal."""
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    try:
        reply = explain_replay(_read_export(path, max_bytes))
        text = json.dumps(reply, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(f"Replay explanation rejected: {exc}", file=errors)
        return 2
    try:
        count = output.write(text)
        if type(count) is not int or count != len(text):
            raise OSError("Incomplete stdout write")
        output.flush()
    except (OSError, ValueError, UnicodeError) as exc:
        # The CLI exits immediately. Closing only its actual stdout suppresses
        # a second shutdown flush; caller-supplied streams remain caller-owned.
        if output is sys.stdout:
            try:
                output.close()
            except OSError:
                pass
        print(f"Replay explanation output failed: {exc}", file=errors)
        return 2
    return 0 if reply["matches"] else 1
