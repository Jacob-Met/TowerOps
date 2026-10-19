"""Review simultaneous synthetic-sector occupancy from a saved sector report.

This is a read-only *consumer* of sector_report.py JSON, not an independent
trajectory solver, conflict predictor, clearance tool or proof of source custody.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

MAX_REPORT_BYTES = 262_144
MAX_CONTACTS = 60
MAX_ABS_NUMBER = 1_000_000_000_000
MAX_VERSION = 9_007_199_254_740_991
TRACK_FIELDS = frozenset({
    "aircraft_id", "entry_after_min", "exit_after_min", "entry_window_clipped",
    "exit_window_clipped", "inside_at_observation", "contact_only",
})
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
ID_RE = re.compile(r"[A-Za-z0-9_-]{1,10}\Z")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key!r}.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Nonfinite JSON constant {value} is unsupported.")


def _number(value: Any, label: str) -> int | float:
    if type(value) not in (int, float) or abs(value) > MAX_ABS_NUMBER or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite JSON number within +/-{MAX_ABS_NUMBER}.")
    return value


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a JSON boolean.")
    return value


def _admit_report(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        raise TypeError("Saved sector report must be UTF-8 bytes.")
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError(f"Saved sector report exceeds {MAX_REPORT_BYTES} bytes.")
    try:
        source = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Saved sector report must be readable UTF-8 JSON.") from exc
    if not isinstance(source, dict) or source.get("format") != "towerops.sector-report.v1":
        raise ValueError("Expected a towerops.sector-report.v1 object.")
    if _bool(source.get("simulation_only"), "simulation_only") is not True or _bool(source.get("read_only"), "read_only") is not True:
        raise ValueError("Expected a read-only, simulation-only sector report.")
    for key in ("input_sha256", "world_hash"):
        if type(source.get(key)) is not str or HASH_RE.fullmatch(source[key]) is None:
            raise ValueError(f"{key} must be a lowercase SHA-256 hex identifier.")
    version = source.get("world_version")
    if type(version) is not int or not 0 <= version <= MAX_VERSION:
        raise ValueError("world_version must be a supported nonnegative JSON integer.")
    _number(source.get("observed_at"), "observed_at")
    sector = source.get("sector")
    if not isinstance(sector, dict) or set(sector) != {"west_nm", "east_nm", "south_nm", "north_nm"}:
        raise ValueError("sector requires the four native rectangle bounds.")
    for key in sector:
        _number(sector[key], f"sector.{key}")
    if not (sector["west_nm"] < sector["east_nm"] and sector["south_nm"] < sector["north_nm"]):
        raise ValueError("Sector rectangle bounds must be strictly ordered.")
    horizon = _number(source.get("horizon_min"), "horizon_min")
    if horizon < 0:
        raise ValueError("horizon_min cannot be negative.")
    contacts = source.get("contacts")
    if not isinstance(contacts, list) or len(contacts) > MAX_CONTACTS:
        raise ValueError(f"contacts must be a list with at most {MAX_CONTACTS} tracks.")
    count = source.get("contact_count")
    if type(count) is not int or count != len(contacts):
        raise ValueError("contact_count must equal the saved contacts length.")
    seen: set[str] = set()
    for index, row in enumerate(contacts):
        label = f"contacts[{index}]"
        if not isinstance(row, dict) or set(row) != TRACK_FIELDS:
            raise ValueError(f"{label} must contain the seven native contact fields.")
        aircraft_id = row["aircraft_id"]
        if type(aircraft_id) is not str or ID_RE.fullmatch(aircraft_id) is None or aircraft_id in seen:
            raise ValueError(f"{label}.aircraft_id is invalid or repeated.")
        seen.add(aircraft_id)
        entry = _number(row["entry_after_min"], f"{label}.entry_after_min")
        exit_ = _number(row["exit_after_min"], f"{label}.exit_after_min")
        if not 0 <= entry <= exit_ <= horizon:
            raise ValueError(f"{label} interval must be within the closed horizon.")
        for key in ("entry_window_clipped", "exit_window_clipped", "inside_at_observation", "contact_only"):
            _bool(row[key], f"{label}.{key}")
        if row["contact_only"] != (entry == exit_):
            raise ValueError(f"{label}.contact_only contradicts the saved interval.")
        if row["entry_window_clipped"] and entry != 0:
            raise ValueError(f"{label}.entry_window_clipped requires entry at 0.")
        if row["exit_window_clipped"] and exit_ != horizon:
            raise ValueError(f"{label}.exit_window_clipped requires exit at the horizon.")
        if row["inside_at_observation"] and entry != 0:
            raise ValueError(f"{label}.inside_at_observation requires entry at 0.")
    return source


def summarize_occupancy(raw: bytes) -> dict[str, Any]:
    """Build exact event contacts and positive-width occupancy segments.

    Open-interval counts exclude zero-duration touches and do not double count
    distinct tracks merely meeting at a shared endpoint. Instant counts use
    the source report's inclusive (closed) interval semantics at exact times.
    """
    source = _admit_report(raw)
    contacts = source["contacts"]
    horizon = source["horizon_min"]
    times = sorted({0, horizon, *(t for row in contacts for t in (row["entry_after_min"], row["exit_after_min"]))})
    segments = []
    for left, right in zip(times, times[1:]):
        if left == right:
            continue
        ids = sorted(row["aircraft_id"] for row in contacts if row["entry_after_min"] <= left and row["exit_after_min"] >= right)
        segments.append({"start_after_min": left, "end_after_min": right, "aircraft_ids": ids, "count": len(ids)})
    events = []
    for t in times:
        ids = sorted(row["aircraft_id"] for row in contacts if row["entry_after_min"] <= t <= row["exit_after_min"])
        events.append({"at_after_min": t, "aircraft_ids": ids, "count": len(ids)})
    peak_open = max((s["count"] for s in segments), default=0)
    peak_exact = max((e["count"] for e in events), default=0)
    return {
        "format": "towerops.sector-occupancy.v1",
        "simulation_only": True,
        "read_only": True,
        "source_verified": False,
        "source_sector_report_sha256": hashlib.sha256(raw).hexdigest(),
        "source_world_input_sha256": source["input_sha256"],
        "source_world_hash": source["world_hash"],
        "world_version": source["world_version"],
        "observed_at": source["observed_at"],
        "sector": source["sector"],
        "horizon_min": horizon,
        "contact_count": len(contacts),
        "contact_only_count": sum(row["contact_only"] for row in contacts),
        "peak_open_interval_count": peak_open,
        "peak_open_windows": [s for s in segments if peak_open > 0 and s["count"] == peak_open],
        "peak_instantaneous_count": peak_exact,
        "peak_instantaneous_times_min": [e["at_after_min"] for e in events if peak_exact > 0 and e["count"] == peak_exact],
        "segments": segments,
        "boundary_events": events,
        "contacts": contacts,
    }


def render_html(summary: dict[str, Any]) -> str:
    """Offline, script-free timeline from an admitted summary; no online assets."""
    horizon = summary["horizon_min"]
    lines = []
    for row in sorted(summary["contacts"], key=lambda r: (r["entry_after_min"], r["aircraft_id"])):
        aircraft_id = html.escape(row["aircraft_id"], quote=True)
        left = 100 * row["entry_after_min"] / horizon if horizon else 0
        width = 100 * (row["exit_after_min"] - row["entry_after_min"]) / horizon if horizon else 0
        point = row["contact_only"] or horizon == 0
        kind = "point" if point else "bar"
        text = "instant contact" if row["contact_only"] else "occupancy"
        graphic = f'<span class="{kind}" style="left:{left:.10g}%;' + (f'width:{width:.10g}%;' if not point else '') + '"></span>'
        clip = ("earlier" if row["entry_window_clipped"] else "observed entry") + "; " + ("later" if row["exit_window_clipped"] else "observed exit")
        lines.append(
            f'<tr><th scope="row">{aircraft_id}</th><td>{row["entry_after_min"]:g}</td>'
            f'<td>{row["exit_after_min"]:g}</td><td class="timeline" aria-label="{aircraft_id} {text}">{graphic}</td>'
            f'<td>{clip}</td></tr>'
        )
    if not lines:
        lines.append('<tr><td colspan="5">No reported sector contacts in the selected horizon.</td></tr>')
    peak = summary["peak_open_interval_count"]
    inst = summary["peak_instantaneous_count"]
    intervals = ", ".join(f'{x["start_after_min"]:g}–{x["end_after_min"]:g} min' for x in summary["peak_open_windows"]) or "None"
    instantaneous = ", ".join(f"{t:g}" for t in summary["peak_instantaneous_times_min"]) or "None"
    occupancy_bars = []
    for segment in summary["segments"]:
        if segment["count"] == 0:
            continue
        left = 100 * segment["start_after_min"] / horizon if horizon else 0
        width = 100 * (segment["end_after_min"] - segment["start_after_min"]) / horizon if horizon else 0
        opacity = 0.4 + 0.6 * segment["count"] / max(1, peak)
        label = f'{segment["start_after_min"]:g} to {segment["end_after_min"]:g} minutes: {segment["count"]} tracks'
        occupancy_bars.append(
            f'<span class="occ-block" style="left:{left:.10g}%;width:{width:.10g}%;opacity:{opacity:.3g}" title="{label}"></span>'
        )
    sector = summary["sector"]
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>TowerOps synthetic sector occupancy</title>
<style>
:root{font:16px system-ui,sans-serif;color-scheme:light dark}body{max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.5}
h1{font-size:1.7rem}p{max-width:85ch}.notice{border-left:4px solid #b47800;padding:.6rem 1rem;background:rgba(180,120,0,.08)}
.metrics{display:flex;flex-wrap:wrap;gap:1rem;margin:1.5rem 0}.metric{border:1px solid #8887;border-radius:.5rem;padding:1rem;min-width:11rem}
.metric strong{display:block;font-size:1.7rem}table{width:100%;border-collapse:collapse;min-width:660px;text-align:left}
th,td{border-bottom:1px solid #8885;padding:.55rem;text-align:left}th{font-weight:650}.scroll{overflow-x:auto}
.timeline{width:45%;min-width:220px;position:relative;background:linear-gradient(90deg,transparent 24.8%,#8883 25%,transparent 25.2%,transparent 49.8%,#8883 50%,transparent 50.2%,transparent 74.8%,#8883 75%,transparent 75.2%)}
.timeline::before{content:"";display:block;height:1.2rem}.bar,.point{position:absolute;top:50%;display:block;background:#207a9b;transform:translateY(-50%);height:.85rem;border-radius:2px;min-width:1px}
.point{height:1rem;width:.45rem;background:#d15c30;transform:translate(-50%,-50%);border-radius:1rem}
.occ-strip{position:relative;height:2rem;border:1px solid #8887;border-radius:.4rem;background:repeating-linear-gradient(90deg,transparent 0,transparent 24.8%,#8883 25%,transparent 25.2%)}
.occ-block{position:absolute;top:0;bottom:0;background:#207a9b}.occ-legend{font-size:.85rem;opacity:.82;margin-top:.3rem}
footer{margin-top:2rem;font-size:.85rem;opacity:.82}
</style></head><body>
<h1>Sector occupancy timeline</h1>
<p class="notice"><strong>Synthetic research only.</strong> The saved report is not independently authenticated. This review neither validates real aircraft movements nor issues safety guidance or clearances. Closed-interval boundary touches are counted separately from sustained occupancy.</p>
""" + f"""<p>Sector bounds (NM): west {sector['west_nm']:g}, east {sector['east_nm']:g}, south {sector['south_nm']:g}, north {sector['north_nm']:g}. Horizon: {horizon:g} minutes after synthetic observation.</p>
<div class="metrics"><div class="metric"><strong>{summary['contact_count']}</strong>tracks contacted</div><div class="metric"><strong>{peak}</strong>peak between-event tracks</div><div class="metric"><strong>{inst}</strong>peak at exact event time</div><div class="metric"><strong>{summary['contact_only_count']}</strong>instant-only contacts</div></div>
<p><strong>Peak sustained windows:</strong> {intervals}. <strong>Peak exact instants (minutes):</strong> {instantaneous}.</p>
<h2>Between-event occupancy</h2>
<div class="occ-strip" role="img" aria-label="Synthetic positive-duration occupancy shown as horizontal blocks; opacity increases with track count">{''.join(occupancy_bars)}</div>
<p class="occ-legend">0 to {horizon:g} minutes, left to right. Taller occupancy counts are darker; exact-instant touches are excluded. Full values are in the JSON report.</p>
<div class="scroll"><table><caption>Synthetic contact intervals in minutes, with native horizon clipping labels</caption><thead><tr><th>Track</th><th>Enter</th><th>Exit</th><th>Timeline</th><th>Cutoff interpretation</th></tr></thead><tbody>{''.join(lines)}</tbody></table></div>
<footer>Generated from a saved towerops.sector-report.v1 report. SHA-256 of report bytes: {summary['source_sector_report_sha256']}. No external scripts, fonts, images or network requests.</footer>
</body></html>\n"""


def _read_named_file(path: Path) -> bytes:
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Report input must resolve to a regular file.")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Opened input must be a regular file.")
        if info.st_size > MAX_REPORT_BYTES:
            raise ValueError(f"Report exceeds {MAX_REPORT_BYTES} bytes.")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            return stream.read(MAX_REPORT_BYTES + 1)
    finally:
        if fd is not None:
            os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize overlap of saved synthetic TowerOps sector contacts; never actuates.",
        epilog="No network, live aircraft data, planner, approval or operational safety authority.",
    )
    parser.add_argument("report", help="Saved towerops.sector-report.v1 JSON, or - for stdin")
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(MAX_REPORT_BYTES + 1) if args.report == "-" else _read_named_file(Path(args.report))
        result = summarize_occupancy(raw)
        output = render_html(result) if args.format == "html" else json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"error: cannot review sector occupancy: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except OSError as exc:
        print(f"error: cannot write occupancy review: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
