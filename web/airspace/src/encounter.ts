import {
  Aircraft, Interval, SafetyPolicy, WorldState,
  horizontalUnsafeInterval, linearAbsUnsafeInterval, projected,
} from './core';

export interface SeparationPoint {
  minutes: number;
  horizontal_nm: number;
  vertical_ft: number;
  horizontal_below: boolean;
  vertical_below: boolean;
  simultaneous: boolean;
}
export interface Encounter {
  aircraft_a: string;
  aircraft_b: string;
  horizon_min: number;
  horizontal_window: Interval | null;
  vertical_window: Interval | null;
  overlap: Interval | null;
  closest_horizontal_min: number;
  samples: SeparationPoint[];
}

function finite(values: number[], label: string): void {
  if (values.some(value => typeof value !== 'number' || !Number.isFinite(value))) {
    throw new Error(`${label} must be finite numbers.`);
  }
}
function checkedPair(state: WorldState, first: string, second: string, policy: SafetyPolicy): [Aircraft, Aircraft] {
  if (first === second) throw new Error('Choose two different flights.');
  const a = state.aircraft.find(item => item.aircraft_id === first);
  const b = state.aircraft.find(item => item.aircraft_id === second);
  if (!a || !b) throw new Error('Both flights must exist in the current world.');
  for (const item of [a, b]) {
    finite([item.x_nm, item.y_nm, item.altitude_ft, item.vx_nm_min, item.vy_nm_min, item.climb_ft_min], 'Flight coordinates and rates');
  }
  finite([policy.min_horizontal_nm, policy.min_vertical_ft, policy.horizon_min], 'The separation envelope and look-ahead');
  if (policy.min_horizontal_nm <= 0 || policy.min_vertical_ft <= 0 || policy.horizon_min <= 0) {
    throw new Error('The separation envelope and look-ahead must be positive.');
  }
  return [a, b];
}
function measure(a: Aircraft, b: Aircraft, minutes: number, policy: SafetyPolicy): SeparationPoint {
  const pa = projected(a, minutes), pb = projected(b, minutes);
  finite([pa.x_nm, pa.y_nm, pa.altitude_ft, pb.x_nm, pb.y_nm, pb.altitude_ft], 'Projected coordinates');
  // Work in the pair's relative frame so large shared motion cannot erase a gap.
  // Keep the existing guard against unrepresentable absolute projections above.
  const horizontal_nm = Math.hypot(
    a.x_nm - b.x_nm + (a.vx_nm_min - b.vx_nm_min) * minutes,
    a.y_nm - b.y_nm + (a.vy_nm_min - b.vy_nm_min) * minutes,
  );
  const vertical_ft = Math.abs(a.altitude_ft - b.altitude_ft + (a.climb_ft_min - b.climb_ft_min) * minutes);
  finite([horizontal_nm, vertical_ft], 'Projected separation');
  const horizontal_below = horizontal_nm < policy.min_horizontal_nm;
  const vertical_below = vertical_ft < policy.min_vertical_ft;
  return { minutes, horizontal_nm, vertical_ft, horizontal_below, vertical_below, simultaneous: horizontal_below && vertical_below };
}

/** Evaluate an exact cursor time; this never advances or writes the source world. */
export function separationAt(
  state: WorldState, first: string, second: string, policy: SafetyPolicy, minutes: number,
): SeparationPoint {
  const [a, b] = checkedPair(state, first, second, policy);
  finite([minutes], 'Forecast time');
  if (minutes < 0 || minutes > policy.horizon_min) throw new Error('Forecast time is outside the current look-ahead.');
  return measure(a, b, minutes, policy);
}

/** Analytical windows use the existing policy functions; samples are for drawing only. */
export function analyzeEncounter(state: WorldState, first: string, second: string, policy: SafetyPolicy): Encounter {
  const [a, b] = checkedPair(state, first, second, policy);
  const dx = a.x_nm - b.x_nm, dy = a.y_nm - b.y_nm;
  const dvx = a.vx_nm_min - b.vx_nm_min, dvy = a.vy_nm_min - b.vy_nm_min;
  const dz = a.altitude_ft - b.altitude_ft, dvz = a.climb_ft_min - b.climb_ft_min;
  const speed2 = dvx * dvx + dvy * dvy, dot = dx * dvx + dy * dvy;
  finite([dx, dy, dvx, dvy, dz, dvz, speed2, dot, dx * dx + dy * dy, policy.min_horizontal_nm ** 2], 'Relative geometry');
  finite([(2 * dot) ** 2, 4 * speed2 * (dx * dx + dy * dy - policy.min_horizontal_nm ** 2)], 'Analytical interval arithmetic');
  const horizontal_window = horizontalUnsafeInterval(dx, dy, dvx, dvy, policy.min_horizontal_nm, policy.horizon_min);
  const vertical_window = linearAbsUnsafeInterval(dz, dvz, policy.min_vertical_ft, policy.horizon_min);
  for (const interval of [horizontal_window, vertical_window]) {
    if (interval) finite([...interval], 'Encounter interval');
  }
  const start = Math.max(horizontal_window?.[0] ?? Infinity, vertical_window?.[0] ?? Infinity);
  const end = Math.min(horizontal_window?.[1] ?? -Infinity, vertical_window?.[1] ?? -Infinity);
  const overlap: Interval | null = start < end ? [start, end] : null;
  const closest_horizontal_min = speed2 === 0 ? 0 : Math.min(policy.horizon_min, Math.max(0, -dot / speed2));
  const samples = Array.from({ length: 81 }, (_, index) => measure(a, b, policy.horizon_min * index / 80, policy));
  return { aircraft_a: first, aircraft_b: second, horizon_min: policy.horizon_min, horizontal_window, vertical_window, overlap, closest_horizontal_min, samples };
}
