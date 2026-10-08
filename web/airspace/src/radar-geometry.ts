import { SafetyPolicy, WorldState, projected } from './core';

export interface RadarFrame {
  center_x_nm: number;
  center_y_nm: number;
  half_range_nm: number;
}
export interface RadarViewport extends RadarFrame {
  width: number;
  height: number;
  scale: number;
  min_x_nm: number;
  max_x_nm: number;
  min_y_nm: number;
  max_y_nm: number;
}

/** Fit current traffic and its existing look-ahead, without changing the world. */
export function fitRadar(state: WorldState, policy: SafetyPolicy): RadarFrame | null {
  if (!Number.isFinite(policy.horizon_min) || policy.horizon_min < 0) return null;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const a of state.aircraft) {
    const end = projected(a, policy.horizon_min);
    for (const [x, y] of [[a.x_nm, a.y_nm], [end.x_nm, end.y_nm]]) {
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
      minX = Math.min(minX, x!); maxX = Math.max(maxX, x!);
      minY = Math.min(minY, y!); maxY = Math.max(maxY, y!);
    }
  }
  if (!state.aircraft.length) minX = maxX = minY = maxY = 0;
  // Half-sums and half-differences avoid overflowing otherwise usable bounds.
  const center_x_nm = minX / 2 + maxX / 2;
  const center_y_nm = minY / 2 + maxY / 2;
  const halfSpan = Math.max(maxX / 2 - minX / 2, maxY / 2 - minY / 2);
  const half_range_nm = Math.ceil(Math.max(15, halfSpan + Math.max(2, halfSpan * .1)) / 5) * 5;
  const edges = [center_x_nm - half_range_nm, center_x_nm + half_range_nm,
    center_y_nm - half_range_nm, center_y_nm + half_range_nm];
  if (![center_x_nm, center_y_nm, half_range_nm, ...edges].every(Number.isFinite) ||
      half_range_nm <= 0 || edges[0] === edges[1] || edges[2] === edges[3]) return null;
  return { center_x_nm, center_y_nm, half_range_nm };
}

/** One NM has the same screen length on both axes, including rectangular canvases. */
export function radarViewport(frame: RadarFrame, width: number, height: number): RadarViewport | null {
  if (![width, height].every(Number.isFinite) || width <= 0 || height <= 0) return null;
  const scale = Math.min(width, height) / frame.half_range_nm / 2;
  const halfWidth = width / 2 / scale, halfHeight = height / 2 / scale;
  const bounds = {
    min_x_nm: frame.center_x_nm - halfWidth, max_x_nm: frame.center_x_nm + halfWidth,
    min_y_nm: frame.center_y_nm - halfHeight, max_y_nm: frame.center_y_nm + halfHeight,
  };
  if (!Number.isFinite(scale) || scale <= 0 || !Object.values(bounds).every(Number.isFinite) ||
      bounds.min_x_nm >= bounds.max_x_nm || bounds.min_y_nm >= bounds.max_y_nm) return null;
  return { ...frame, ...bounds, width, height, scale };
}

export function radarPoint(view: RadarViewport, x: number, y: number): readonly [number, number] {
  return [view.width / 2 + (x - view.center_x_nm) * view.scale,
    view.height / 2 - (y - view.center_y_nm) * view.scale];
}

/** A counted loop stays bounded even where adding a small step loses precision. */
export function radarTicks(min: number, max: number, targetIntervals: number): number[] {
  if (![min, max, targetIntervals].every(Number.isFinite) || min >= max) return [];
  const intervals = Math.max(2, Math.min(12, Math.floor(targetIntervals)));
  const rawStep = (max / 2 - min / 2) / intervals * 2;
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const ratio = rawStep / magnitude;
  const step = Math.max(5, (ratio <= 1 ? 1 : ratio <= 2 ? 2 : ratio <= 5 ? 5 : 10) * magnitude);
  const first = Math.ceil(min / step) * step;
  if (![step, first].every(Number.isFinite)) return [];
  const ticks: number[] = [];
  for (let i = 0; i < 64; i++) {
    const value = first + i * step;
    if (!Number.isFinite(value) || value > max) break;
    if (value >= min && (!ticks.length || value > ticks[ticks.length - 1]!)) ticks.push(value === 0 ? 0 : value);
  }
  return ticks;
}

export function radarNumber(value: number): string {
  return value === 0 ? '0' : String(value);
}

export function radarRangeLabel(state: WorldState, policy: SafetyPolicy): string {
  const frame = fitRadar(state, policy);
  return frame ? 'AUTO FIT +/- '+radarNumber(frame.half_range_nm)+' NM' : 'RADAR VIEW UNAVAILABLE';
}
