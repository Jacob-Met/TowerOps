"""Check one recorded TowerOps world-plan report against an explicit raw world.

This is a read-only provenance *comparison*, not producer authentication,
new screening, clearance authority, or an operational air-traffic decision.
See CHECK_PLAN_SOURCE.md for statuses and precise identity limits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from compare_plans import _parse_report, _read_report
from plan_world import _read_world_file, parse_world


def verify_plan_source(report_raw: bytes, world_raw: bytes) -> dict[str, Any]:
    """Admit both originals and compare raw-byte and native-world identities.

    Exact input-byte identity and native-world identity are separate checks.
    The existing strict admissions own all saved schema/body hashes, numeric
    limits, JSON field uniqueness, and native identity construction.
    """
    try:
        report, _ = _parse_report(report_raw)
    except (ValueError, TypeError, RecursionError, OverflowError) as error:
        raise ValueError(f"Saved report: {error}") from error
    try:
        source_world = parse_world(world_raw)
    except (ValueError, TypeError, RecursionError, OverflowError) as error:
        raise ValueError(f"Raw source world: {error}") from error

    source_sha256 = hashlib.sha256(world_raw).hexdigest()
    raw_match = source_sha256 == report["input_sha256"]
    world_match = source_world.world_hash == report["world_hash"]
    if raw_match and world_match:
        status = "exact_bytes_and_world"
    elif world_match:
        status = "same_native_world_different_bytes"
    elif raw_match:
        status = "reported_bytes_but_different_world"
    else:
        status = "different_bytes_and_world"

    return {
        "format": "towerops.plan-source-binding.v1",
        "simulation_only": True,
        "proposal_only": True,
        "validation": "internal_consistency_and_explicit_source_comparison_only",
        "binding_status": status,
        "matched": raw_match and world_match,
        "checks": {
            "input_bytes_sha256_match": raw_match,
            "native_world_hash_match": world_match,
        },
        "report": {
            "bytes": len(report_raw),
            "sha256": hashlib.sha256(report_raw).hexdigest(),
            "reported_input_sha256": report["input_sha256"],
            "world_hash": report["world_hash"],
            "status": report["status"],
            "reviewed_at": report["reviewed_at"],
        },
        "source": {
            "bytes": len(world_raw),
            "sha256": source_sha256,
            "world_hash": source_world.world_hash,
            "version": source_world.version,
            "observed_at": source_world.observed_at,
            "aircraft_count": len(source_world.aircraft),
        },
    }


def _shown(value: Any) -> str:
    """Keep filename/control characters out of ordinary terminal rendering."""
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


def render_text(result: dict[str, Any]) -> str:
    """Render a complete immutable binding assessment with explicit limits."""
    report = result["report"]
    source = result["source"]
    lines = [
        "TowerOps saved plan / raw world binding",
        "Research simulation only. No planning, selection, approval or actuation.",
        "",
        f"Binding status: {result['binding_status']}",
        f"Exact original bytes and native world both match: {_shown(result['matched'])}",
        f"Original-input SHA256 matches: {_shown(result['checks']['input_bytes_sha256_match'])}",
        f"Native world SHA256 matches: {_shown(result['checks']['native_world_hash_match'])}",
        "",
    ]
    for label, key in (("Saved report", "report_path"), ("Raw world", "world_path")):
        if key in result:
            lines.append(f"{label} path: {_shown(result[key])}")
    lines.extend([
        "",
        f"Report bytes: {report['bytes']}",
        f"Report SHA256: {report['sha256']}",
        f"Report original-input SHA256 (recorded): {report['reported_input_sha256']}",
        f"Report world SHA256 (recorded): {report['world_hash']}",
        f"Report status (recorded): {_shown(report['status'])}",
        f"Report review clock (synthetic sec): {_shown(report['reviewed_at'])}",
        "",
        f"Source bytes: {source['bytes']}",
        f"Source SHA256: {source['sha256']}",
        f"Source native world SHA256: {source['world_hash']}",
        f"Source version: {_shown(source['version'])}",
        f"Source observation clock (synthetic sec): {_shown(source['observed_at'])}",
        f"Source aircraft: {source['aircraft_count']}",
        "",
        "Internal hashes and a selected source-file comparison do not authenticate",
        "the saved producer, recompute screening, establish freshness, prove candidate",
        "completeness or provide operational aviation assurance.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Match a saved synthetic plan to an explicitly selected raw WorldState.",
        epilog="See CHECK_PLAN_SOURCE.md. No planner run, writes, external data, or actuation.",
    )
    parser.add_argument("report", help="Saved towerops.world-plan.v1 JSON file")
    parser.add_argument("world", help="Original raw WorldState JSON file to compare")
    parser.add_argument("--json", action="store_true", help="Return structured JSON instead of text")
    args = parser.parse_args(argv)

    try:
        report_raw = _read_report(Path(args.report))
        world_raw = _read_world_file(Path(args.world))
        result = verify_plan_source(report_raw, world_raw)
        # Keep the caller's operand spelling. Neither file is opened through
        # a normalized or derived name, and no output is emitted until ready.
        result["report_path"] = args.report
        result["world_path"] = args.world
        output = (
            json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
            if args.json else render_text(result)
        )
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as error:
        print(f"error: cannot check plan source: {_shown(str(error))[1:-1]}", file=sys.stderr)
        return 2

    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        print(f"error: cannot write binding result: {_shown(str(error))[1:-1]}", file=sys.stderr)
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
        return 2
    return 0 if result["matched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
