"""Portable presentation of the saved-world planner's freshly serialized result.

This is the optional producer format, not a saved-report importer. The original
native planner owns admission, screening, proposal order and every result value.
"""

from __future__ import annotations

import base64
import html
import json
from typing import Any

STATUS_TEXT = {
    "no_conflict": (
        "No conflict in this snapshot and horizon",
        "The native policy found no conflicting aircraft. No proposal is needed.",
    ),
    "options_available": (
        "Individually screened alternatives available",
        "Each listed alternative passed native screening separately. Review one "
        "proposal at a time; the alternatives are not a simultaneous batch.",
    ),
    "no_admitted_option": (
        "Conflict found; no admitted alternative",
        "The native policy found a conflict, but its bounded candidate menu "
        "contained no individually admitted alternative.",
    ),
}

POLICY_LABELS = {
    "min_horizontal_nm": "Horizontal minimum (nm)",
    "min_vertical_ft": "Vertical minimum (ft)",
    "horizon_min": "Look-ahead horizon (min)",
    "sample_step_min": "Native sample step (min)",
    "max_state_age_sec": "Maximum state age (s)",
    "max_speed_nm_min": "Maximum horizontal speed (nm/min)",
    "max_climb_ft_min": "Maximum climb magnitude (ft/min)",
}

STYLE = """
:root{color-scheme:light;font:16px/1.55 system-ui,sans-serif;color:#17283c;background:#f3f6fa}
*{box-sizing:border-box}body{margin:0}main{max-width:76rem;margin:auto;padding:1.25rem}
h1{font-size:clamp(1.8rem,5vw,2.7rem);line-height:1.15;margin:.5rem 0 1rem}
h2{font-size:1.35rem}h3{font-size:1.08rem}a{color:#075a8c;text-underline-offset:.2em}
a:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid #c46200;
outline-offset:4px}nav{display:flex;gap:.5rem 1rem;flex-wrap:wrap;margin:1rem 0}
.eyebrow{font-weight:750;color:#42627d;font-size:.85rem;letter-spacing:.08em}
.lead{max-width:70ch}.panel,.alternative{background:white;border:1px solid #cedae5;
border-radius:.7rem;padding:1.2rem;margin:1rem 0;min-width:0}
.notice{border-left:4px solid #a3630a;background:#fff5dd;padding:.85rem 1rem}
.download{display:inline-block;background:#075a8c;color:white;border-radius:.35rem;
padding:.6rem .85rem;font-weight:650}.muted{color:#4e6377}
dl{display:grid;grid-template-columns:minmax(10rem,1fr) minmax(0,3fr);gap:.4rem 1rem}
dt{font-weight:650}dd{margin:0;min-width:0}code,pre{font: .9rem/1.5 ui-monospace,
SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;white-space:pre-wrap}
pre{padding:.85rem;background:#f2f5f8;border:1px solid #d8e1e9;border-radius:.35rem}
.table-scroll{overflow-x:auto;max-width:100%;border:1px solid #d8e1e9;border-radius:.35rem}
table{width:100%;border-collapse:collapse;min-width:28rem;font-size:.94rem}
th,td{text-align:left;padding:.55rem .7rem;border-bottom:1px solid #e2e8ee}
thead{background:#eaf0f5}th{font-weight:700}td{font-variant-numeric:tabular-nums}
caption{text-align:left;padding:.5rem .7rem;font-weight:650}
#world table{min-width:64rem}summary{cursor:pointer;font-weight:700;padding:.25rem 0}
summary .muted{font-weight:400}details[open]>summary{margin-bottom:1rem}
.changed{background:#fff5dd}.changed::after{content:" · changed";font-size:.82em;color:#805300}
.hash{word-break:break-all}.option-heading{font-size:1.08rem}
.back{display:inline-block;margin-top:1rem}footer{font-size:.88rem;color:#4e6377;margin:2rem 0}
@media(max-width:38rem){main{padding:.75rem}.panel,.alternative{padding:.9rem}
dl{grid-template-columns:minmax(0,1fr);gap:.2rem}dd{margin-bottom:.65rem}}
@media print{body{background:white}main{max-width:none;padding:0}.panel,.alternative{
break-inside:avoid;border-color:#777}nav,.download,.back{display:none}
details::details-content{content-visibility:visible}details>:not(summary){display:block}
.table-scroll{overflow:visible}table,#world table{min-width:0;font-size:.72rem}
th,td{padding:.25rem}a{color:inherit}h1{font-size:1.7rem}}
"""


def _text(value: Any) -> str:
    """Keep native JSON scalar spelling, including integer/float and signed zero."""
    if isinstance(value, str):
        return html.escape(value, quote=True)
    return html.escape(json.dumps(value, ensure_ascii=False, allow_nan=False), quote=True)


def _entry(label: str, key: str, value: Any) -> str:
    return f'<dt>{html.escape(label)}</dt><dd data-field="{key}"><code>{_text(value)}</code></dd>'


def _alternative(rank: int, advisory: dict[str, Any], current: dict[str, Any]) -> str:
    rows = []
    for field, proposed, label in (
        ("vx_nm_min", "set_vx_nm_min", "Horizontal x velocity (nm/min)"),
        ("vy_nm_min", "set_vy_nm_min", "Horizontal y velocity (nm/min)"),
        ("climb_ft_min", "set_climb_ft_min", "Climb (ft/min)"),
    ):
        old, new = _text(current[field]), _text(advisory[proposed])
        changed = ' class="changed"' if current[field] != advisory[proposed] else ""
        rows.append(
            f'<tr data-component="{field}"><th scope="row">{label}</th>'
            f'<td data-value="current"><code>{old}</code></td>'
            f'<td data-value="proposed"{changed}><code>{new}</code></td></tr>'
        )
    metadata = "".join(
        _entry(label, key, advisory[key])
        for key, label in (
            ("aircraft_id", "Target flight"),
            ("advisory_hash", "Native advisory hash"),
            ("world_hash", "Bound world hash"),
            ("issued_at", "Issued at (synthetic seconds)"),
            ("expires_at", "Expires at (synthetic seconds)"),
            ("rationale", "Native rationale"),
        )
    )
    body = _text(json.dumps(advisory, ensure_ascii=False, allow_nan=False, indent=2))
    identity = _text(advisory["aircraft_id"])
    return (
        f'<details class="alternative" id="alternative-{rank}" data-rank="{rank}" '
        f'data-aircraft-id="{identity}"><summary class="option-heading">'
        f'Alternative {rank} — {identity} <span class="muted"> · inspect setpoints</span></summary>'
        '<div class="table-scroll" role="region" tabindex="0" '
        f'aria-label="Alternative {rank} current and proposed setpoints">'
        '<table><caption>Current flight versus this proposal</caption>'
        '<thead><tr><th scope="col">Component</th><th scope="col">Current</th>'
        '<th scope="col">Proposed</th></tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table></div><dl>'
        + metadata
        + '</dl><details><summary>Full native advisory body</summary>'
        f'<pre data-field="advisory_json">{body}</pre></details>'
        '<a class="back" href="#alternatives">Back to alternatives</a></details>'
    )


def render_plan_html(report_json: str) -> str:
    """Render the exact JSON produced by plan_world.main; never run the planner.

    Callers of this presentation helper must provide the fresh producer result.
    It is not a public admission API for arbitrary saved planning reports.
    """
    if not isinstance(report_json, str):
        raise TypeError("The native planner report must be serialized text.")
    report = json.loads(report_json)
    if report["format"] != "towerops.world-plan.v1":
        raise ValueError("Unsupported native planner report format.")
    title, status_explanation = STATUS_TEXT[report["status"]]
    world = report["world"]
    aircraft = {row["aircraft_id"]: row for row in world["aircraft"]}
    alternatives = "".join(
        _alternative(rank, item, aircraft[item["aircraft_id"]])
        for rank, item in enumerate(report["advisories"], 1)
    )
    if not alternatives:
        alternatives = '<p id="empty-alternatives">No admitted alternatives in this review.</p>'
    summary = "".join(
        _entry(label, key, value)
        for label, key, value in (
            ("Recorded status", "status", report["status"]),
            ("Candidates examined", "candidate_count", report["candidate_count"]),
            ("Admitted alternatives", "admitted_count", len(report["advisories"])),
            ("Conflicting aircraft", "conflicting_aircraft", report["conflicting_aircraft"]),
            ("Review time (synthetic seconds)", "reviewed_at", report["reviewed_at"]),
            ("World version", "version", world["version"]),
            ("Observed at (synthetic seconds)", "observed_at", world["observed_at"]),
            ("Original input SHA-256", "input_sha256", report["input_sha256"]),
            ("Native world hash", "world_hash", report["world_hash"]),
        )
    )
    policy = "".join(
        f'<dt>{label}</dt><dd data-policy-field="{key}"><code>{_text(report["policy"][key])}'
        '</code></dd>'
        for key, label in POLICY_LABELS.items()
    )
    fields = (
        ("aircraft_id", "Flight"), ("x_nm", "x (nm)"), ("y_nm", "y (nm)"),
        ("altitude_ft", "Altitude (ft)"), ("vx_nm_min", "x velocity (nm/min)"),
        ("vy_nm_min", "y velocity (nm/min)"), ("climb_ft_min", "Climb (ft/min)"),
    )
    headers = "".join(f'<th scope="col">{label}</th>' for _, label in fields)
    world_rows = "".join(
        f'<tr data-aircraft-id="{_text(row["aircraft_id"])}">'
        + "".join(f'<td data-field="{key}"><code>{_text(row[key])}</code></td>' for key, _ in fields)
        + "</tr>" for row in world["aircraft"]
    )
    if not world_rows:
        world_rows = '<tr><td colspan="7">This is an empty world.</td></tr>'
    encoded = base64.b64encode(report_json.encode("utf-8")).decode("ascii")
    download = (
        '<a class="download" id="download-json" download="world-plan.json" '
        f'href="data:application/json;charset=utf-8;base64,{encoded}">Download exact JSON report</a>'
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>TowerOps · Native world-plan review</title>'
        f'<style>{STYLE}</style></head><body><main id="top">'
        '<header><p class="eyebrow">TOWEROPS / SYNTHETIC WORLD REVIEW</p>'
        '<h1>Compare the native alternatives</h1>'
        '<p class="lead">Inspect each proposed setpoint beside the target flight’s current '
        'velocity and climb. Every alternative below keeps its original native menu position.</p>'
        + download
        + '<nav aria-label="Report sections"><a href="#summary">Review summary</a>'
        '<a href="#alternatives">Alternatives</a><a href="#world">World snapshot</a>'
        '<a href="#policy">Policy</a><a href="#report-json">Original JSON</a></nav></header>'
        '<p class="notice">Research simulation only. These are individually screened proposals, '
        'not approvals or an executable batch. An option can leave unrelated aircraft in conflict. '
        'This review does not establish operational aviation safety.</p>'
        f'<section class="panel" id="summary" aria-labelledby="summary-heading"><h2 id="summary-heading">'
        f'{title}</h2><p>{status_explanation}</p><dl>{summary}</dl></section>'
        '<section id="alternatives" aria-labelledby="alternatives-heading">'
        '<h2 id="alternatives-heading">All admitted alternatives, in native order</h2>'
        '<p>The first alternative retains the planner’s first-choice priority. No new score or '
        'sorting is applied. Expand any alternative to compare exact current and proposed '
        'components; each proposal was screened on its own against the same recorded world.</p>'
        + alternatives
        + '</section><section class="panel" id="world" aria-labelledby="world-heading">'
        '<h2 id="world-heading">World snapshot</h2>'
        '<p>Recorded native values, in native identifier order. Position is a snapshot; no new '
        'trajectory is projected here. Scroll the table horizontally to inspect all components.</p>'
        '<div class="table-scroll" tabindex="0" role="region" aria-label="Complete world snapshot">'
        f'<table><thead><tr>{headers}</tr></thead><tbody>{world_rows}</tbody></table></div></section>'
        '<section class="panel" id="policy" aria-labelledby="policy-heading">'
        f'<h2 id="policy-heading">Complete screening policy</h2><dl>{policy}</dl></section>'
        '<details class="panel" id="report-json"><summary>Original native JSON report</summary>'
        '<p>The download contains these exact UTF-8 bytes, including original numeric spelling '
        'and final newline. The input SHA-256 identifies the original world bytes; that input file '
        'is not embedded separately. Hashes identify bodies, not an external signature or approval.</p>'
        f'<pre>{_text(report_json)}</pre></details>'
        '<footer>Created by the optional native saved-world planner format. One review, one '
        'recorded result. No JavaScript, service, or external asset is required to read this file.</footer>'
        '</main></body></html>\n'
    )
