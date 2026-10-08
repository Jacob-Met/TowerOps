"""Compare already recorded TowerOps policy experiments without planning again."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

from plan_world import MAX_ABS_NUMBER, MAX_VERSION, MIN_POLICY_VALUE, parse_world
from towerops import Advisory, canonical_bytes

MAX_REPORT_BYTES = 4 * 1024 * 1024
REPORT_FIELDS = frozenset((
    "format", "simulation_only", "proposal_only", "input_sha256", "world",
    "world_hash", "reviewed_at", "policy", "status", "conflicting_aircraft",
    "candidate_count", "advisories",
))
POLICY_FIELDS = (
    "min_horizontal_nm", "min_vertical_ft", "horizon_min", "sample_step_min",
    "max_state_age_sec", "max_speed_nm_min", "max_climb_ft_min",
)
POLICY_UNITS = (
    "NM", "ft", "min", "min", "sec", "NM/min", "ft/min",
)
ADVISORY_FIELDS = frozenset((
    "aircraft_id", "world_hash", "set_vx_nm_min", "set_vy_nm_min",
    "set_climb_ft_min", "issued_at", "expires_at", "rationale", "advisory_hash",
))
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def _fields(value: Any, expected: frozenset[str], location: str) -> None:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{location} must contain exactly its documented fields")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object field")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON numbers are not supported")


def _number(value: Any, location: str, limit: float = MAX_ABS_NUMBER) -> None:
    if (
        type(value) not in (int, float)
        or (type(value) is float and not math.isfinite(value))
        or abs(value) > limit
    ):
        raise ValueError(f"{location} must be a finite bounded JSON number")


def _hash(value: Any, location: str) -> None:
    if type(value) is not str or HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{location} must be a lowercase SHA256")


def _parse_report(raw: bytes) -> tuple[dict[str, Any], bytes]:
    if type(raw) is not bytes:
        raise ValueError("report input must be UTF-8 bytes")
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError(f"report exceeds {MAX_REPORT_BYTES} bytes")
    try:
        report = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValueError(f"invalid report JSON: {error}") from error

    _fields(report, REPORT_FIELDS, "Report")
    if report["format"] != "towerops.world-plan.v1":
        raise ValueError("unsupported report format; use towerops.world-plan.v1")
    if report["simulation_only"] is not True or report["proposal_only"] is not True:
        raise ValueError("report must explicitly describe synthetic proposals only")
    _hash(report["input_sha256"], "Reported original-input identity")
    _hash(report["world_hash"], "World identity")

    state = parse_world(canonical_bytes(report["world"]))
    world = state.to_dict()
    world_bytes = canonical_bytes(world)
    if state.world_hash != report["world_hash"]:
        raise ValueError("world_hash does not match the complete native world")
    _number(report["reviewed_at"], "Review clock")

    policy = report["policy"]
    _fields(policy, frozenset(POLICY_FIELDS), "Policy")
    for field in POLICY_FIELDS:
        _number(policy[field], f"Policy {field}")
        if policy[field] < MIN_POLICY_VALUE:
            raise ValueError(f"Policy {field} is below the native positive limit")

    identities = {aircraft.aircraft_id for aircraft in state.aircraft}
    conflicts = report["conflicting_aircraft"]
    if (
        type(conflicts) is not list
        or any(type(value) is not str or value not in identities for value in conflicts)
        or len(set(conflicts)) != len(conflicts)
    ):
        raise ValueError("conflicting_aircraft must list distinct native world identities")

    count = report["candidate_count"]
    if type(count) is not int or not 0 <= count <= MAX_VERSION:
        raise ValueError("candidate_count must be a bounded nonnegative JSON integer")
    advisories = report["advisories"]
    if type(advisories) is not list or len(advisories) > count:
        raise ValueError("advisories must be a list no larger than candidate_count")

    seen: set[str] = set()
    for index, row in enumerate(advisories, start=1):
        location = f"Advisory {index}"
        _fields(row, ADVISORY_FIELDS, location)
        if type(row["aircraft_id"]) is not str or row["aircraft_id"] not in conflicts:
            raise ValueError(f"{location} must target a reported conflicting aircraft")
        if row["world_hash"] != report["world_hash"]:
            raise ValueError(f"{location} has a different world identity")
        for field in ("set_vx_nm_min", "set_vy_nm_min", "set_climb_ft_min", "issued_at"):
            _number(row[field], f"{location} {field}")
        # Native v1 emits reviewed_at + 8.0, including the admitted 1e12 boundary.
        _number(row["expires_at"], f"{location} expires_at", MAX_ABS_NUMBER + 8.0)
        if canonical_bytes(row["issued_at"]) != canonical_bytes(report["reviewed_at"]):
            raise ValueError(f"{location} issued_at differs from the exact review clock")
        if row["expires_at"] < row["issued_at"]:
            raise ValueError(f"{location} expires before it was issued")
        rationale = row["rationale"]
        if type(rationale) is not str or not 0 < len(rationale) <= 4096:
            raise ValueError(f"{location} rationale must be nonempty bounded text")
        try:
            rationale.encode("utf-8")
        except UnicodeError as error:
            raise ValueError(f"{location} rationale contains invalid Unicode") from error
        _hash(row["advisory_hash"], f"{location} identity")
        body = {key: value for key, value in row.items() if key != "advisory_hash"}
        if Advisory(**body).advisory_hash != row["advisory_hash"]:
            raise ValueError(f"{location} advisory_hash does not match its complete body")
        if row["advisory_hash"] in seen:
            raise ValueError("duplicate advisory identity in a saved menu")
        seen.add(row["advisory_hash"])

    status = report["status"]
    if status == "no_conflict":
        consistent = not conflicts and count == 0 and not advisories
    elif status == "no_admitted_option":
        consistent = bool(conflicts) and count > 0 and not advisories
    elif status == "options_available":
        consistent = bool(conflicts) and bool(advisories)
    else:
        raise ValueError("unsupported saved planning status")
    if not consistent:
        raise ValueError("saved status, conflicting identities and menu counts disagree")

    # Array ordering follows the original native world identity, without
    # changing any numeric type, signed zero, aircraft identity or setpoint.
    report["world"] = world
    return report, world_bytes


def _summary(report: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "reported_input_sha256": report["input_sha256"],
        "policy": report["policy"],
        "status": report["status"],
        "conflicting_aircraft": report["conflicting_aircraft"],
        "candidate_count": report["candidate_count"],
        "advisory_count": len(report["advisories"]),
        "first_advisory_hash": (
            report["advisories"][0]["advisory_hash"] if report["advisories"] else None
        ),
    }


def compare_reports(left_raw: bytes, right_raw: bytes) -> dict[str, Any]:
    """Compare complete saved reports; never invoke the planner or its gate.

    Hashes are internal consistency checks, not authentication or a new safety
    decision. All inputs are admitted before a comparison is returned.
    """
    try:
        left, left_world = _parse_report(left_raw)
    except (ValueError, TypeError, RecursionError, OverflowError) as error:
        raise ValueError(f"Left report: {error}") from error
    try:
        right, right_world = _parse_report(right_raw)
    except (ValueError, TypeError, RecursionError, OverflowError) as error:
        raise ValueError(f"Right report: {error}") from error
    if left_world != right_world:
        raise ValueError("reports describe different exact native worlds")
    if canonical_bytes(left["reviewed_at"]) != canonical_bytes(right["reviewed_at"]):
        raise ValueError("reports have different exact native review clocks")

    left_menu = left["advisories"]
    right_menu = right["advisories"]
    left_positions = {row["advisory_hash"]: rank for rank, row in enumerate(left_menu, 1)}
    right_positions = {row["advisory_hash"]: rank for rank, row in enumerate(right_menu, 1)}
    entries = []
    for rank, row in enumerate(left_menu, 1):
        other_rank = right_positions.get(row["advisory_hash"])
        if other_rank is not None:
            other = right_menu[other_rank - 1]
            if canonical_bytes(row) != canonical_bytes(other):
                raise ValueError("matching advisory hashes have different complete bodies")
        entries.append({
            "membership": "retained" if other_rank is not None else "left_only",
            "left_rank": rank, "right_rank": other_rank, "advisory": row,
        })
    for rank, row in enumerate(right_menu, 1):
        if row["advisory_hash"] not in left_positions:
            entries.append({
                "membership": "right_only", "left_rank": None,
                "right_rank": rank, "advisory": row,
            })

    counts = {kind: sum(row["membership"] == kind for row in entries)
              for kind in ("retained", "left_only", "right_only")}
    counts["rank_changed"] = sum(
        row["membership"] == "retained" and row["left_rank"] != row["right_rank"]
        for row in entries
    )
    return {
        "format": "towerops.plan-comparison.v1",
        "simulation_only": True,
        "proposal_only": True,
        "world": left["world"],
        "world_hash": left["world_hash"],
        "reviewed_at": left["reviewed_at"],
        "left": _summary(left, left_raw),
        "right": _summary(right, right_raw),
        "policy_changes": [
            {"field": field, "unit": unit, "left": left["policy"][field],
             "right": right["policy"][field]}
            for field, unit in zip(POLICY_FIELDS, POLICY_UNITS, strict=True)
            if canonical_bytes(left["policy"][field]) != canonical_bytes(right["policy"][field])
        ],
        "counts": counts,
        "entries": entries,
    }


def _shown(value: Any) -> str:
    """Keep literal text and numeric identity readable without terminal controls."""
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


def render_text(result: dict[str, Any], left_name: str, right_name: str) -> str:
    lines = [
        "TowerOps saved policy comparison",
        "Synthetic proposals only. Recorded results; no new planning, approval or actuation.",
        "No policy preference, menu-completeness verification or producer authentication.",
        "",
        f"World SHA256: {result['world_hash']}",
        f"Exact review clock (sec): {_shown(result['reviewed_at'])}",
    ]
    for label, name, side in (("Left", left_name, result["left"]),
                              ("Right", right_name, result["right"])):
        lines.extend([
            "",
            f"{label} file: {_shown(name)}",
            f"  Report SHA256: {side['report_sha256']}",
            f"  Original-input SHA256 (reported): {side['reported_input_sha256']}",
            f"  Recorded status: {side['status']}",
            f"  Reported conflicting aircraft: {_shown(side['conflicting_aircraft'])}",
            f"  Recorded candidates: {side['candidate_count']}; saved alternatives: {side['advisory_count']}",
        ])
    lines.extend(["", "Exact saved policy changes (left -> right):"])
    if result["policy_changes"]:
        for change in result["policy_changes"]:
            lines.append(
                f"  {change['field']} ({change['unit']}): "
                f"{_shown(change['left'])} -> {_shown(change['right'])}"
            )
    else:
        lines.append("  None.")
    changed_fields = {change["field"] for change in result["policy_changes"]}
    lines.extend(["", "Other identical saved policy values:"])
    common = [(field, unit) for field, unit in zip(POLICY_FIELDS, POLICY_UNITS, strict=True)
              if field not in changed_fields]
    if not common:
        lines.append("  None.")
    for field, unit in common:
        lines.append(f"  {field} ({unit}): {_shown(result['left']['policy'][field])}")
    counts = result["counts"]
    lines.extend([
        "",
        (
            f"Saved alternatives: {counts['retained']} retained; "
            f"{counts['left_only']} left only; {counts['right_only']} right only."
        ),
        f"Retained alternatives with a different menu rank: {counts['rank_changed']}.",
        "Ranks are original 1-based menu positions, not a new recommendation.",
        "L/R show the left/right rank; '-' means absent. Units: vx/vy NM/min, climb ft/min.",
        "",
    ])
    for heading, kinds in (
        ("Left menu in its original order:", {"retained", "left_only"}),
        ("Right-only alternatives in their original right order:", {"right_only"}),
    ):
        lines.append(heading)
        rows = [row for row in result["entries"] if row["membership"] in kinds]
        if not rows:
            lines.append("  None.")
        for entry in rows:
            row = entry["advisory"]
            left_rank = "-" if entry["left_rank"] is None else str(entry["left_rank"])
            right_rank = "-" if entry["right_rank"] is None else str(entry["right_rank"])
            lines.append(
                f"  L{left_rank}/R{right_rank} [{entry['membership']}] "
                f"{_shown(row['aircraft_id'])}: vx={_shown(row['set_vx_nm_min'])}, "
                f"vy={_shown(row['set_vy_nm_min'])}, climb={_shown(row['set_climb_ft_min'])}"
            )
            lines.append(f"    Advisory SHA256: {row['advisory_hash']}")
            lines.append(
                f"    Issued/expires (sec): {_shown(row['issued_at'])} / "
                f"{_shown(row['expires_at'])}; rationale: {_shown(row['rationale'])}"
            )
        lines.append("")
    lines.append("These are individually recorded alternatives, never a simultaneous batch.")
    return "\n".join(lines) + "\n"


def _read_report(path: Path) -> bytes:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("report paths must be direct regular files, not links or special files")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("opened report is not a regular file")
        if info.st_size > MAX_REPORT_BYTES:
            raise ValueError(f"report exceeds {MAX_REPORT_BYTES} bytes")
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        with stream:
            raw = stream.read(MAX_REPORT_BYTES + 1)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError(f"report exceeds {MAX_REPORT_BYTES} bytes")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare saved TowerOps policy experiments for one exact world and review clock.",
        epilog="See COMPARE_PLANS.md. Reads regular report files only; no planning or actuation.",
    )
    parser.add_argument("left", type=Path, help="First towerops.world-plan.v1 JSON report")
    parser.add_argument("right", type=Path, help="Second towerops.world-plan.v1 JSON report")
    parser.add_argument("--json", action="store_true", help="Emit complete comparison records as JSON")
    args = parser.parse_args(argv)
    try:
        result = compare_reports(_read_report(args.left), _read_report(args.right))
        result["sources"] = {"left": str(args.left), "right": str(args.right)}
        output = (
            json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
            if args.json else render_text(result, str(args.left), str(args.right))
        )
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as error:
        message = _shown(str(error))[1:-1]
        print(f"error: cannot compare saved plans: {message}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        message = _shown(str(error))[1:-1]
        print(f"error: cannot write comparison: {message}", file=sys.stderr)
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
