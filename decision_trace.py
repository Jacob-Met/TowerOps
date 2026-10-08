"""Bounded, read-only delivery of the native audit replay result to Airspace Lab.

The JSON text is parsed in Python so the original integer/float distinction is
retained. This adapter never applies an advisory or installs a world or audit.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from audit_replay import replay_audit

MAX_TRACE_BYTES = 2 * 1024 * 1024
MAX_TRACE_EVENTS = 5000


def review_trace(raw: str) -> dict[str, Any]:
    """Review a native event list or a demo document containing ``audit_events``."""
    if not isinstance(raw, str):
        raise TypeError("Decision trace must be JSON text.")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("Decision trace must contain valid UTF-8 text.") from exc
    if size > MAX_TRACE_BYTES:
        raise ValueError("Decision trace exceeds the 2 MiB file limit.")
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ValueError("Decision trace is not readable JSON.") from exc
    if isinstance(data, dict):
        data = data.get("audit_events")
    if not isinstance(data, list):
        raise TypeError("Expected an event list or an object with audit_events.")
    if len(data) > MAX_TRACE_EVENTS:
        raise ValueError("Decision trace exceeds the 5,000 event limit.")

    try:
        report = replay_audit(data)
        result = {
            "chain_valid": report.chain_valid,
            "ok": report.ok,
            "event_count": len(data),
            "advisories": [asdict(advisory) for advisory in report.advisories.values()],
            "rejects": report.rejects,
            "issues": report.issues,
        }
        # Confirm the result can cross the same strict JSON boundary as the UI.
        json.dumps(result, allow_nan=False)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError) as exc:
        raise ValueError("Decision trace has malformed event data and could not be reviewed.") from exc
    return result
