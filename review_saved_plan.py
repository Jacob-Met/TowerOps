"""Compact read-only review of one already recorded TowerOps plan report."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from compare_plans import POLICY_FIELDS, POLICY_UNITS, _parse_report, _read_report


def summarize_report(raw: bytes) -> dict[str, Any]:
    """Admit and summarize saved rows; do not plan or screen their proposals.

    The existing comparator owns report admission and internal body-hash checks.
    Counts describe the admitted saved rows, not a newly verified native menu.
    """
    report, _world_bytes = _parse_report(raw)
    conflicts = list(report["conflicting_aircraft"])
    counts = dict.fromkeys(conflicts, 0)
    for advisory in report["advisories"]:
        counts[advisory["aircraft_id"]] += 1
    return {
        "format": "towerops.saved-plan-summary.v1",
        "simulation_only": True,
        "proposal_only": True,
        "validation": "internal_consistency_only",
        "report_bytes": len(raw),
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "reported_input_sha256": report["input_sha256"],
        "recorded": {
            "status": report["status"],
            "world_hash": report["world_hash"],
            "version": report["world"]["version"],
            "observed_at": report["world"]["observed_at"],
            "reviewed_at": report["reviewed_at"],
            "candidate_count": report["candidate_count"],
            "conflicting_aircraft": conflicts,
        },
        "counts": {
            "aircraft": len(report["world"]["aircraft"]),
            "conflicting_aircraft": len(conflicts),
            "saved_alternatives": len(report["advisories"]),
        },
        "policy": {field: report["policy"][field] for field in POLICY_FIELDS},
        "saved_alternative_counts": [
            {"aircraft_id": identity, "count": counts[identity]}
            for identity in conflicts
        ],
    }


def _shown(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


def render_text(summary: dict[str, Any]) -> str:
    """Render a completed summary, with recorded values and explicit limits."""
    recorded = summary["recorded"]
    counts = summary["counts"]
    lines = [
        "TowerOps recorded plan summary",
        f"Recorded status: {_shown(recorded['status'])}",
        f"Recorded review time (synthetic sec): {_shown(recorded['reviewed_at'])}",
        "Recorded data only. No new planning, screening, selection or application.",
        "",
    ]
    if "source_path" in summary:
        lines.append(f"Source path: {_shown(summary['source_path'])}")
    lines.extend([
        f"Report bytes: {summary['report_bytes']}",
        f"Report SHA256: {summary['report_sha256']}",
        f"Original-input SHA256 (reported): {summary['reported_input_sha256']}",
        f"Recorded world SHA256: {recorded['world_hash']}",
        f"Recorded world version: {_shown(recorded['version'])}",
        f"Recorded observation time (synthetic sec): {_shown(recorded['observed_at'])}",
        "",
        f"Saved aircraft: {counts['aircraft']}",
        f"Recorded conflicting aircraft count: {counts['conflicting_aircraft']}",
        f"Recorded conflicting aircraft (original order): {_shown(recorded['conflicting_aircraft'])}",
        f"Recorded candidate count: {recorded['candidate_count']}",
        f"Saved alternative count: {counts['saved_alternatives']}",
        "",
        "Saved alternatives per recorded conflicting aircraft (original order):",
    ])
    if not summary["saved_alternative_counts"]:
        lines.append("  None.")
    for row in summary["saved_alternative_counts"]:
        lines.append(f"  {_shown(row['aircraft_id'])}: {row['count']}")
    lines.extend(["", "Complete recorded policy:"])
    for field, unit in zip(POLICY_FIELDS, POLICY_UNITS, strict=True):
        lines.append(f"  {field} ({unit}): {_shown(summary['policy'][field])}")
    lines.extend([
        "",
        "Admission checks internal structure and body hashes only.",
        "It does not establish producer authenticity, freshness, policy correctness,",
        "candidate-menu completeness or safety approval.",
        "Derived counts count admitted saved rows; the candidate count remains a recorded claim.",
        "Saved alternatives were recorded individually, not as a simultaneous batch.",
        "No alternative is selected or applied. Research simulation only.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize one recorded TowerOps plan without planning again.",
        epilog="See REVIEW_SAVED_PLAN.md. Reads a saved report, not a raw world or live state.",
    )
    parser.add_argument("report", type=Path, help="Saved towerops.world-plan.v1 JSON report")
    parser.add_argument("--json", action="store_true", help="Emit the complete summary projection as JSON")
    args = parser.parse_args(argv)
    try:
        result = summarize_report(_read_report(args.report))
        result["source_path"] = str(args.report)
        output = (
            json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
            if args.json else render_text(result)
        )
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as error:
        print(f"error: cannot summarize saved plan: {_shown(str(error))[1:-1]}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        print(f"error: cannot write summary: {_shown(str(error))[1:-1]}", file=sys.stderr)
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
