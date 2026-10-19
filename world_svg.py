"""Offline SVG view of a saved, strictly admitted synthetic TowerOps world.

The plotted XY coordinates are nautical-mile offsets, not latitude/longitude.
Altitude is reported textually, never inferred from 2D line crossings. No
advisory is generated, approved, or applied by this viewer.
"""

from __future__ import annotations

import argparse
import math
import sys
from html import escape
from typing import Any

MAX_HORIZON_MIN = 120.0
WIDTH = 1200
PLOT_LEFT = 80
PLOT_TOP = 116
PLOT_WIDTH = 1040
PLOT_HEIGHT = 550
LEGEND_TOP = 730
COLORS = (
    "#2769a5", "#bf4c37", "#26815d", "#7752a6", "#b47715", "#276b70",
    "#9b427b", "#586934", "#755847", "#4e64aa", "#a44141", "#337681",
)


def _fmt(number: float) -> str:
    """Bounded-size, locale-independent presentation of finite numeric input."""
    return format(0.0 if number == 0 else number, ".6g")


def _ticks(low: float, high: float) -> list[float]:
    """At most 16 round major ticks across a nonempty finite chart interval."""
    approximate = (high - low) / 7.0
    power = 10.0 ** math.floor(math.log10(approximate))
    step = next(factor * power for factor in (1, 2, 5, 10) if factor * power >= approximate)
    first = math.ceil(low / step) * step
    result: list[float] = []
    for index in range(16):
        value = first + index * step
        if value > high + step * 1e-8:
            break
        if low - step * 1e-8 <= value <= high + step * 1e-8:
            result.append(value)
    return result


def render_svg(world: Any, horizon_min: float = 5.0) -> str:
    """Render a native WorldState as a deterministic, self-contained SVG string.

    ``world`` must already have passed the native ``parse_world`` admission gate.
    This pure renderer requires the ordinary WorldState ``aircraft`` and
    ``observed_at``/``version`` attributes; it never mutates the supplied world.
    """
    if type(horizon_min) not in (int, float) or not math.isfinite(horizon_min) or not 0 < horizon_min <= MAX_HORIZON_MIN:
        raise ValueError(f"horizon_min must be greater than zero and at most {MAX_HORIZON_MIN} minutes")
    tracks = sorted(world.aircraft, key=lambda aircraft: aircraft.aircraft_id)
    coordinates = []
    for aircraft in tracks:
        projected_x = aircraft.x_nm + aircraft.vx_nm_min * horizon_min
        projected_y = aircraft.y_nm + aircraft.vy_nm_min * horizon_min
        projected_altitude = aircraft.altitude_ft + aircraft.climb_ft_min * horizon_min
        if not all(math.isfinite(value) for value in (
            aircraft.x_nm, aircraft.y_nm, aircraft.altitude_ft,
            projected_x, projected_y, projected_altitude,
        )):
            raise ValueError("world has a non-finite projected track")
        coordinates.append((aircraft, projected_x, projected_y, projected_altitude))

    all_x = [value for aircraft, x, _, _ in coordinates for value in (aircraft.x_nm, x)] or [0.0]
    all_y = [value for aircraft, _, y, _ in coordinates for value in (aircraft.y_nm, y)] or [0.0]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    center_x, center_y = min_x / 2 + max_x / 2, min_y / 2 + max_y / 2
    visible_x = max(max_x - min_x, 10.0) * 1.20
    visible_y = max(max_y - min_y, 10.0) * 1.20
    scale = min(PLOT_WIDTH / visible_x, PLOT_HEIGHT / visible_y)
    west, east = center_x - PLOT_WIDTH / (2 * scale), center_x + PLOT_WIDTH / (2 * scale)
    south, north = center_y - PLOT_HEIGHT / (2 * scale), center_y + PLOT_HEIGHT / (2 * scale)

    def px(x_nm: float) -> float:
        return PLOT_LEFT + (x_nm - west) * scale

    def py(y_nm: float) -> float:
        return PLOT_TOP + (north - y_nm) * scale

    rows = max(1, (len(tracks) + 1) // 2)
    height = LEGEND_TOP + 38 + rows * 27 + 48
    result = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">TowerOps synthetic world tracks</title>',
        '<desc id="desc">Static XY nautical-mile projections of synthetic aircraft. Filled circles indicate starting locations; outlined squares indicate projected locations. Altitudes appear in the legend. No real air-traffic or clearance authority.</desc>',
        '<style>text{font-family:system-ui,Arial,sans-serif;fill:#172b3d}.muted{fill:#536778}.axis{font-size:13px}.track-label{font-size:13px;fill:#172b3d}.legend{font-size:14px}.small{font-size:12px}</style>',
        f'<rect width="{WIDTH}" height="{height}" fill="#fff"/>',
        '<text x="80" y="43" font-size="26" font-weight="700">TowerOps · Synthetic track overview</text>',
        f'<text x="80" y="72" class="muted" font-size="15">World version {escape(str(world.version))} · observed at {escape(_fmt(world.observed_at))} s · projection {escape(_fmt(horizon_min))} min · {len(tracks)} aircraft</text>',
        '<text x="80" y="96" class="muted" font-size="13">XY offsets in nautical miles. Diagram is not geographical; crossing lines do not by themselves establish a separation violation.</text>',
        f'<rect x="{PLOT_LEFT}" y="{PLOT_TOP}" width="{PLOT_WIDTH}" height="{PLOT_HEIGHT}" fill="#f8fafc" stroke="#7a8b98"/>',
    ]
    for x in _ticks(west, east):
        plot_x = px(x)
        result.append(f'<line x1="{plot_x:.3f}" x2="{plot_x:.3f}" y1="{PLOT_TOP}" y2="{PLOT_TOP + PLOT_HEIGHT}" stroke="#dce4e9"/>')
        result.append(f'<text class="axis muted" x="{plot_x:.3f}" y="{PLOT_TOP + PLOT_HEIGHT + 20}" text-anchor="middle">{_fmt(x)}</text>')
    for y in _ticks(south, north):
        plot_y = py(y)
        result.append(f'<line x1="{PLOT_LEFT}" x2="{PLOT_LEFT + PLOT_WIDTH}" y1="{plot_y:.3f}" y2="{plot_y:.3f}" stroke="#dce4e9"/>')
        result.append(f'<text class="axis muted" x="{PLOT_LEFT - 12}" y="{plot_y + 4:.3f}" text-anchor="end">{_fmt(y)}</text>')
    result.append(f'<text x="{PLOT_LEFT + PLOT_WIDTH / 2:.3f}" y="{PLOT_TOP + PLOT_HEIGHT + 43}" class="axis muted" text-anchor="middle">X (NM, increasing right)</text>')
    result.append(f'<text transform="translate(23 {PLOT_TOP + PLOT_HEIGHT / 2:.3f}) rotate(-90)" class="axis muted" text-anchor="middle">Y (NM, increasing upward)</text>')
    if not tracks:
        result.append(f'<text x="{PLOT_LEFT + PLOT_WIDTH / 2:.3f}" y="{PLOT_TOP + PLOT_HEIGHT / 2:.3f}" class="muted" text-anchor="middle" font-size="22">No aircraft in this saved world</text>')
    for index, (aircraft, end_x, end_y, end_altitude) in enumerate(coordinates):
        color = COLORS[index % len(COLORS)]
        start_x, start_y = px(aircraft.x_nm), py(aircraft.y_nm)
        projected_x, projected_y = px(end_x), py(end_y)
        title = escape(f'{aircraft.aircraft_id}: ({_fmt(aircraft.x_nm)}, {_fmt(aircraft.y_nm)}) to ({_fmt(end_x)}, {_fmt(end_y)}) NM; altitude {_fmt(aircraft.altitude_ft)} to {_fmt(end_altitude)} ft')
        label = escape(aircraft.aircraft_id)
        result.append(f'<g data-aircraft="{label}"><title>{title}</title>')
        result.append(f'<line x1="{start_x:.3f}" y1="{start_y:.3f}" x2="{projected_x:.3f}" y2="{projected_y:.3f}" stroke="{color}" stroke-width="2.8" stroke-linecap="round"/>')
        result.append(f'<rect x="{projected_x - 4:.3f}" y="{projected_y - 4:.3f}" width="8" height="8" fill="#fff" stroke="{color}" stroke-width="2"/>')
        result.append(f'<circle cx="{start_x:.3f}" cy="{start_y:.3f}" r="4.5" fill="{color}" stroke="#fff" stroke-width="1"/>')
        result.append(f'<rect x="{start_x + 5:.3f}" y="{start_y - 27:.3f}" width="{max(24, len(aircraft.aircraft_id) * 8 + 10)}" height="19" rx="3" fill="#fff" fill-opacity="0.9"/>')
        result.append(f'<text x="{start_x + 10:.3f}" y="{start_y - 13:.3f}" class="track-label">{label}</text></g>')

    result.extend((
        f'<text x="{PLOT_LEFT}" y="{LEGEND_TOP}" font-size="18" font-weight="600">Aircraft · altitude at start → projection</text>',
        f'<text x="{PLOT_LEFT}" y="{LEGEND_TOP + 21}" class="small muted">● starting XY position    □ projected XY position    ·    FT = feet</text>',
    ))
    for index, (aircraft, _, _, end_altitude) in enumerate(coordinates):
        column = index // rows
        row = index % rows
        text_x = PLOT_LEFT + column * 545
        text_y = LEGEND_TOP + 49 + row * 27
        color = COLORS[index % len(COLORS)]
        legend = f'{aircraft.aircraft_id} · {_fmt(aircraft.altitude_ft)} → {_fmt(end_altitude)} FT'
        result.append(f'<rect x="{text_x}" y="{text_y - 11}" width="12" height="12" rx="2" fill="{color}"/>')
        result.append(f'<text class="legend" x="{text_x + 19}" y="{text_y}">{escape(legend)}</text>')
    result.append(f'<text x="{PLOT_LEFT}" y="{height - 18}" class="small muted">Synthetic constant-velocity projection only · no advisories, approvals, acknowledgements, actuation or aviation assurance</text>')
    result.append('</svg>')
    return '\n'.join(result) + '\n'


def _horizon_argument(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('horizon must be a finite number of minutes') from exc
    if not math.isfinite(value) or not 0 < value <= MAX_HORIZON_MIN:
        raise argparse.ArgumentTypeError(f'horizon must be > 0 and <= {MAX_HORIZON_MIN} minutes')
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Render a strictly admitted synthetic TowerOps WorldState as a standalone SVG.')
    parser.add_argument('world', help='Raw WorldState JSON file or - for stdin')
    parser.add_argument('--horizon-min', type=_horizon_argument, default=5.0, help='Projection interval in minutes (0, 120], default 5')
    args = parser.parse_args(argv)
    try:
        # Reuse the maintained native input admission and file-read limits.
        from pathlib import Path
        from plan_world import MAX_WORLD_BYTES, _read_world_file, parse_world
        raw = sys.stdin.buffer.read(MAX_WORLD_BYTES + 1) if args.world == '-' else _read_world_file(Path(args.world))
        svg = render_svg(parse_world(raw), args.horizon_min)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        print(f'error: cannot render synthetic world: {exc}', file=sys.stderr)
        return 2
    try:
        sys.stdout.write(svg)
        sys.stdout.flush()
    except OSError as exc:
        print(f'error: cannot write SVG: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
