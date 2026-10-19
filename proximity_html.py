"""Create a self-contained offline proximity-review page for a saved synthetic world.

The reader is for research visualization only: native SafetyPolicy owns conflict
classification, and no proposal, actuation or outside endpoint is available.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from plan_world import MAX_WORLD_BYTES, _argument_number, _read_world_file
from proximity_report import report_proximity


_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>TowerOps | Proximity Review</title>
<style>
:root {color-scheme:dark; font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif; background:#080f1d; color:#e6ecf5;}
* {box-sizing:border-box;} body {margin:0; min-height:100vh; background:radial-gradient(ellipse at 88% -8%,#1e3b52 0,transparent 45%),#080f1d;}
a {color:#88d5df;} button,input,select {font:inherit;} button {cursor:pointer;}
.wrap {width:min(1232px,calc(100% - 40px)); margin:auto;}
header {border-bottom:1px solid #24344e;} .header {display:flex; align-items:center; justify-content:space-between; gap:18px; padding:22px 0;}
.brand {font-size:1.05rem; letter-spacing:.22em; font-weight:760; color:#fcffff;} .subbrand {letter-spacing:.12em; color:#87a1b9; font-size:.69rem;}
.flag {font-size:.72rem; letter-spacing:.08em; font-weight:750; text-transform:uppercase; padding:7px 11px; border:1px solid #47716d; border-radius:40px; color:#bcf0d7; white-space:nowrap;}
h1 {font-size:clamp(2.2rem,5vw,4rem); letter-spacing:-.045em; font-weight:720; line-height:1.07; margin:35px 0 12px;}
.lead {max-width:840px; color:#adc0d4; line-height:1.55; margin:0 0 27px;}
.metric-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:27px;}
.metric {border:1px solid #2b3b53; background:#121f32de; padding:18px 20px; border-radius:12px; min-height:104px;}
.metric small {display:block; text-transform:uppercase; letter-spacing:.12em; font-size:.68rem; color:#96afc6;}
.metric b {font-size:1.8rem; font-weight:680;letter-spacing:-.025em; display:block; padding-top:4px;}
section {border:1px solid #2a3a50;background:#101b2ccf;border-radius:14px;overflow:hidden;margin-bottom:22px;}
.section-head {display:flex; align-items:center; justify-content:space-between;gap:18px;padding:20px 23px;border-bottom:1px solid #253449; flex-wrap:wrap;}
h2 {font-size:1.15rem;letter-spacing:-.012em;margin:0;} .small {color:#94aac0;font-size:.84rem;}
.controls {display:flex;gap:9px;align-items:center;flex-wrap:wrap;}
.controls input,.controls select {background:#17273c;border:1px solid #41516b;color:#e7f0fa;border-radius:8px;padding:10px 11px;min-width:120px;}
.controls input {width:240px;} .controls :focus-visible,button:focus-visible {outline:2px solid #8ce6ed;outline-offset:2px;}
.scroll {overflow:auto;} table {width:100%;border-collapse:collapse;text-align:left;min-width:760px;}
th {font-size:.7rem;text-transform:uppercase;letter-spacing:.085em;color:#9eb1c6;background:#142237;padding:13px 19px;text-wrap:nowrap;}
td {border-top:1px solid #233248;padding:14px 19px;color:#d9e5ef;font-variant-numeric:tabular-nums;}
tbody tr {transition:background .15s;} tbody tr:hover {background:#1a2f48;} tbody tr.active {background:#214052;}
.pair-btn {border:0;background:transparent;color:#fafcff;text-decoration:underline;text-decoration-color:#6b91a9;text-underline-offset:4px;padding:4px 2px;font-weight:680;letter-spacing:.02em;}
.pill {display:inline-block;border:1px solid #3e6370;border-radius:5px;padding:2px 7px;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.055em;color:#a4dde7;}
.pill.alert {color:#ffcec2;border-color:#925746;background:#382b33;} .pill.near {color:#b9d9dc;}
.empty {padding:26px 23px;color:#a9bdd2;display:none;}
.detail {padding:24px;display:grid;grid-template-columns:1fr 1fr;gap:28px;} .detail p {color:#a9bed1;margin:6px 0 16px;}
.detail h3 {margin:0;font-size:1.4rem;letter-spacing:-.015em;} .bar-label {display:flex;justify-content:space-between;font-size:.78rem;color:#bacbdb;margin:17px 0 8px;}
.meter {height:8px;background:#21374e;border-radius:8px;overflow:hidden;} .meter > span {display:block;height:100%;background:#67c8d2;width:0%;}
.meter > span.warning {background:#eb966e;} .timeline {position:relative;height:12px;border-radius:12px;background:#294058;margin:23px 2px 8px;}
.timeline:after {content:'';position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent,transparent calc(25% - 1px),#8aa2b2 25%);opacity:.35;}
.timeline-pin {position:absolute;top:-6px;left:0;width:4px;height:24px;background:#b0f0de;border-radius:2px;box-shadow:0 0 0 3px #263a43;z-index:2;}
.timeline-labels {display:flex;justify-content:space-between;color:#9cb5c8;font-size:.75rem;}
.note {border-top:1px solid #26384e;color:#a9bdd1;font-size:.83rem;padding:18px 22px;}
footer {color:#839bb1;font-size:.75rem;overflow-wrap:anywhere;margin:21px 0 40px;}
footer code {color:#adc9db;} .visually-hidden {position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;}
@media(max-width:800px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.detail{grid-template-columns:1fr;}.section-head{align-items:stretch;}.controls{width:100%;}.controls input{flex:1;min-width:150px;}}
@media(max-width:500px){.wrap{width:calc(100% - 24px)}.header{padding:16px 0}.metric{padding:12px 15px;min-height:88px}.metric b{font-size:1.5rem}.controls input,.controls select{width:100%;}.controls{display:grid;grid-template-columns:1fr;}.detail{padding:16px}.section-head{padding:16px}}
@media(prefers-reduced-motion:reduce){tbody tr{transition:none}}
</style>
</head>
<body>
<header><div class="wrap header"><div><div class="brand">TOWEROPS <span style="color:#69bac8">/</span> LAB</div><div class="subbrand">SAVED WORLD FORECAST</div></div><div class="flag">Synthetic research only</div></div></header>
<main class="wrap">
<h1>Proximity review<span style="color:#8ccac9">.</span></h1>
<p class="lead">Explore the closest synthetic traffic pairs in a frozen WorldState. Native conflict classifications are kept distinct from diagnostic proximity scoring. This report cannot authorize a maneuver or control any aircraft.</p>
<div class="metric-grid" aria-label="Report summary">
<div class="metric"><small>Pairs evaluated</small><b id="total">—</b></div>
<div class="metric"><small>Native conflict pairs</small><b id="conflicts">—</b></div>
<div class="metric"><small>Forecast horizon</small><b id="horizon">—</b></div>
<div class="metric"><small>Saved world version</small><b id="version">—</b></div>
</div>
<section aria-labelledby="pairs-title"><div class="section-head"><div><h2 id="pairs-title">Closest pairs</h2><span class="small" id="count" aria-live="polite"></span></div>
<div class="controls"><label for="search" class="visually-hidden">Search callsign</label><input id="search" type="search" placeholder="Search callsign…" autocomplete="off">
<label for="filter" class="visually-hidden">Pair filter</label><select id="filter"><option value="all">All pairs</option><option value="conflict">Native conflicts</option><option value="clear">Non-conflicts</option></select>
<label for="order" class="visually-hidden">Sort pairs</label><select id="order"><option value="rank">Native conflict → proximity</option><option value="time">Closest time</option><option value="id">Callsign</option></select></div></div>
<div class="scroll"><table><thead><tr><th scope="col">Aircraft pair</th><th scope="col">Native status</th><th scope="col">Proximity ratio</th><th scope="col">Closest at</th><th scope="col">Horizontal</th><th scope="col">Vertical</th></tr></thead><tbody id="rows"></tbody></table></div><div class="empty" id="empty">No saved pairs match these filters.</div>
<div class="note">Conflict status uses the original native SafetyPolicy. A ratio is a diagnostic rank, not a clearance decision or independent safety verdict. Only the first <strong id="limit">—</strong> saved pairs are available in this view.</div>
</section>
<section aria-labelledby="detail-title"><div class="section-head"><h2 id="detail-title">Selected pair</h2><span id="detail-status" class="small">Choose a row to inspect</span></div>
<div class="detail"><div><h3 id="selected">Select a pair above</h3><p id="ratio-note">Closest combined normalized separation</p>
<div class="bar-label"><span>Horizontal at closest time</span><span id="horizontal-value">—</span></div><div class="meter"><span id="horizontal-bar"></span></div>
<div class="bar-label"><span>Vertical at closest time</span><span id="vertical-value">—</span></div><div class="meter"><span id="vertical-bar"></span></div>
<p class="small" id="separate">—</p></div>
<div><span class="small">Forecast time of closest combined proximity</span><div class="timeline" aria-hidden="true"><div id="time-pin" class="timeline-pin"></div></div>
<div class="timeline-labels"><span>0 min</span><span id="time-end">—</span></div><p id="selected-time">—</p><p class="small">Thresholds are horizontal <span id="h-limit">—</span> NM and vertical <span id="v-limit">—</span> ft. Bars reach their full width at the configured minimum and do not convey operational safety.</p></div></div>
</section>
<footer id="provenance">—</footer>
<noscript><div class="wrap">JavaScript is needed for interactive local review; no network calls are made.</div></noscript>
</main>
<script id="report-data" type="application/json">__REPORT_JSON__</script>
<script>
'use strict';
const report = JSON.parse(document.getElementById('report-data').textContent);
const $ = (id) => document.getElementById(id);
const fmt = (n, digits=2) => Number.isFinite(n) ? n.toLocaleString('en-US',{maximumFractionDigits:digits}) : '—';
const original = Object.freeze(report.pairs.map((row,index) => Object.freeze({...row,sourceIndex:index})));
$('total').textContent = fmt(report.total_pair_count,0);
$('conflicts').textContent = fmt(report.native_conflict_pair_count,0);
$('horizon').textContent = fmt(report.horizon_min)+' min';
$('version').textContent = fmt(report.world_version,0);
$('limit').textContent = String(report.returned_pair_count);
$('time-end').textContent = fmt(report.horizon_min)+' min';
$('h-limit').textContent = fmt(report.thresholds.horizontal_nm,3);
$('v-limit').textContent = fmt(report.thresholds.vertical_ft,2);
$('provenance').textContent = 'World SHA-256: '+report.world_hash+'  •  Input SHA-256: '+report.input_sha256+'  •  Observed at: '+String(report.observed_at)+' synthetic seconds  •  '+report.format;
let selected = original.length ? original[0].sourceIndex : -1;
function txt(node,value){node.textContent=String(value);}
function textCell(row,content,klass=''){
  const td=document.createElement('td');td.textContent=String(content);if(klass)td.className=klass;row.appendChild(td);return td;
}
function show(row){
  selected=row.sourceIndex;
  txt($('selected'),row.aircraft_a+'  /  '+row.aircraft_b);
  txt($('detail-status'),row.native_conflict ? 'Native conflict within horizon' : 'No native conflict in horizon');
  txt($('ratio-note'),'Normalized closest proximity ratio '+fmt(row.proximity_ratio,3)+' (diagnostic)');
  const h=report.thresholds.horizontal_nm,v=report.thresholds.vertical_ft;
  txt($('horizontal-value'),fmt(row.horizontal_nm_at_closest,3)+' NM');
  txt($('vertical-value'),fmt(row.vertical_ft_at_closest,1)+' ft');
  for(const [id,ratio] of [['horizontal-bar',row.horizontal_nm_at_closest/h],['vertical-bar',row.vertical_ft_at_closest/v]]){
    $(id).style.width=Math.min(100,Math.max(0,ratio*100))+'%';
    $(id).classList.toggle('warning',ratio<1);
  }
  txt($('separate'),'Horizontal CPA: '+fmt(row.horizontal_cpa_nm,3)+' NM at '+fmt(row.horizontal_cpa_time_min,3)+' min · Vertical CPA: '+fmt(row.vertical_cpa_ft,1)+' ft at '+fmt(row.vertical_cpa_time_min,3)+' min');
  const fraction=report.horizon_min ? row.closest_time_min/report.horizon_min : 0;
  $('time-pin').style.left=(Math.max(0,Math.min(1,fraction))*100)+'%';
  txt($('selected-time'),fmt(row.closest_time_min,3)+' minutes after observation');
  for(const btn of $('rows').querySelectorAll('button')){
    const isSelected=Number(btn.dataset.id)===selected;
    btn.setAttribute('aria-pressed',isSelected?'true':'false');
    btn.closest('tr').classList.toggle('active',isSelected);
  }
}
function populate(){
  const query=$('search').value.trim().toLowerCase(), filter=$('filter').value,order=$('order').value;
  const view=original.filter(row=>(filter==='all'||(filter==='conflict')===row.native_conflict)
                 &&(!query||row.aircraft_a.toLowerCase().includes(query)||row.aircraft_b.toLowerCase().includes(query)));
  if(order==='time')view.sort((a,b)=>a.closest_time_min-b.closest_time_min||a.sourceIndex-b.sourceIndex);
  if(order==='id')view.sort((a,b)=>a.aircraft_a.localeCompare(b.aircraft_a)||a.aircraft_b.localeCompare(b.aircraft_b));
  const body=$('rows');body.replaceChildren();
  for(const row of view){
    const tr=document.createElement('tr');if(row.sourceIndex===selected)tr.classList.add('active');
    const td=document.createElement('td'),btn=document.createElement('button');
    btn.className='pair-btn';btn.textContent=row.aircraft_a+' / '+row.aircraft_b;
    btn.dataset.id=String(row.sourceIndex);btn.setAttribute('aria-pressed',row.sourceIndex===selected?'true':'false');
    btn.setAttribute('aria-label','Inspect '+row.aircraft_a+' and '+row.aircraft_b);
    btn.addEventListener('click',()=>show(row));td.appendChild(btn);tr.appendChild(td);
    const status=document.createElement('td'),pill=document.createElement('span');pill.className='pill '+(row.native_conflict?'alert':'near');
    pill.textContent=row.native_conflict?'CONFLICT':'NO CONFLICT';status.appendChild(pill);tr.appendChild(status);
    textCell(tr,fmt(row.proximity_ratio,3)+' ×');textCell(tr,fmt(row.closest_time_min,3)+' min');
    textCell(tr,fmt(row.horizontal_nm_at_closest,3)+' NM');textCell(tr,fmt(row.vertical_ft_at_closest,1)+' ft');
    body.appendChild(tr);
  }
  $('empty').style.display=view.length?'none':'block';
  const omission=report.truncated?' (truncated source report)':'';
  txt($('count'),view.length+' of '+original.length+' saved pairs'+omission);
  if(view.length&&!view.some(row=>row.sourceIndex===selected))show(view[0]);
  if(!view.length){txt($('detail-status'),'No matching pair');txt($('selected'),'Adjust the filters');}
}
for(const id of ['search','filter','order'])$(id).addEventListener(id==='search'?'input':'change',populate);
populate();
if(original.length)show(original[0]);
</script>
</body></html>
'''


def render_html(report: dict) -> str:
    """Render an inert, offline HTML shell with escaped first-party JSON data."""
    if type(report) is not dict or report.get("format") != "towerops.proximity-report.v1":
        raise ValueError("Only towerops.proximity-report.v1 inputs can be rendered.")
    safe_json = json.dumps(report, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    # Prevent embedded JSON strings from closing script or entering HTML/CSS.
    safe_json = (safe_json.replace("&", "\\u0026").replace("<", "\\u003c")
                 .replace(">", "\\u003e").replace("\u2028", "\\u2028")
                 .replace("\u2029", "\\u2029"))
    return _HTML.replace("__REPORT_JSON__", safe_json)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a standalone offline HTML review of one synthetic WorldState.")
    parser.add_argument("world", help="Raw WorldState JSON path, or - for stdin")
    parser.add_argument("--horizontal-nm", type=_argument_number, default=5.0)
    parser.add_argument("--vertical-ft", type=_argument_number, default=1000.0)
    parser.add_argument("--horizon-min", type=_argument_number, default=5.0)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        raw = (sys.stdin.buffer.read(MAX_WORLD_BYTES + 1) if args.world == "-"
               else _read_world_file(Path(args.world)))
        report = report_proximity(raw, horizontal_nm=args.horizontal_nm,
                                  vertical_ft=args.vertical_ft,
                                  horizon_min=args.horizon_min, limit=args.limit)
        page = render_html(report)
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"error: cannot create proximity review: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(page)
        sys.stdout.flush()
    except (OSError, UnicodeError) as exc:
        print(f"error: cannot write proximity review: {exc}", file=sys.stderr)
        try:
            sys.stdout.close()
        except (OSError, UnicodeError):
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
