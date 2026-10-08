import { Aircraft, SafetyPolicy, WorldState, canonicalJson, replaceAircraft } from './core';
import { ConflictWindow, conflictWindows, createAircraft } from './world-tools';

export interface TrackEditInput {
  x_nm: number;
  y_nm: number;
  flight_level: number;
  bearing_deg: number;
  speed_kt: number;
  climb_ft_min: number;
}

export interface TrackEditSession {
  aircraft_id: string;
  original: Aircraft;
  input: TrackEditInput;
  baseline_key: string;
}

export interface TrackEditPreview {
  aircraft_id: string;
  baseline_key: string;
  input_key: string;
  world: WorldState;
  before: ConflictWindow[];
  after: ConflictWindow[];
}

const bearing = (degrees: number): number => ((degrees % 360) + 360) % 360;
const snapshotKey = (state: WorldState, policy: SafetyPolicy, now: number): string =>
  canonicalJson({ state, policy, now });

export function beginTrackEdit(
  state: WorldState, aircraft_id: string, policy: SafetyPolicy, now: number,
): TrackEditSession {
  const matches = state.aircraft.filter(a => a.aircraft_id === aircraft_id);
  if (matches.length !== 1) throw new Error('Select one existing flight to edit.');
  const original = { ...matches[0]! };
  return {
    aircraft_id,
    original,
    input: {
      x_nm: original.x_nm,
      y_nm: original.y_nm,
      flight_level: original.altitude_ft / 100,
      bearing_deg: bearing(Math.atan2(original.vx_nm_min, original.vy_nm_min) * 180 / Math.PI),
      speed_kt: Math.hypot(original.vx_nm_min, original.vy_nm_min) * 60,
      climb_ft_min: original.climb_ft_min,
    },
    baseline_key: snapshotKey(state, policy, now),
  };
}

export function previewTrackEdit(
  session: TrackEditSession, input: TrackEditInput,
  state: WorldState, policy: SafetyPolicy, now: number,
): TrackEditPreview {
  if (snapshotKey(state, policy, now) !== session.baseline_key) {
    throw new Error('The world, clock or policy changed. Cancel and start a fresh edit.');
  }
  if (!Number.isSafeInteger(state.version) || state.version >= Number.MAX_SAFE_INTEGER) {
    throw new Error('This world version cannot be incremented exactly. Load a lower version before editing.');
  }
  const fields = ['x_nm', 'y_nm', 'flight_level', 'bearing_deg', 'speed_kt', 'climb_ft_min'] as const;
  if (fields.some(field => !Number.isFinite(input[field]))) {
    throw new Error('Every flight field must be a finite number.');
  }
  const original = session.original;
  const updated = createAircraft({
    aircraft_id: session.aircraft_id,
    x_nm: input.x_nm,
    y_nm: input.y_nm,
    altitude_ft: input.flight_level * 100,
    heading_deg: input.bearing_deg,
    speed_kt: input.speed_kt,
    climb_ft_min: input.climb_ft_min,
  });
  // Keep untouched values exact: converting a vector to bearing/speed and back
  // can otherwise introduce drift during an unrelated position or altitude edit.
  if (input.x_nm === session.input.x_nm) updated.x_nm = original.x_nm;
  if (input.y_nm === session.input.y_nm) updated.y_nm = original.y_nm;
  if (input.flight_level === session.input.flight_level) updated.altitude_ft = original.altitude_ft;
  if (input.climb_ft_min === session.input.climb_ft_min) updated.climb_ft_min = original.climb_ft_min;
  if (bearing(input.bearing_deg) === bearing(session.input.bearing_deg) && input.speed_kt === session.input.speed_kt) {
    updated.vx_nm_min = original.vx_nm_min;
    updated.vy_nm_min = original.vy_nm_min;
  }
  if (canonicalJson(updated) === canonicalJson(original)) {
    throw new Error('Change at least one flight field before previewing.');
  }
  const snapshot = { ...state, aircraft: state.aircraft.map(a => ({ ...a })) };
  const world = replaceAircraft(snapshot, updated, now);
  return {
    aircraft_id: session.aircraft_id,
    baseline_key: session.baseline_key,
    input_key: canonicalJson(input),
    world,
    before: conflictWindows(state, policy),
    after: conflictWindows(world, policy),
  };
}

export function applyTrackEdit(
  session: TrackEditSession, preview: TrackEditPreview, input: TrackEditInput,
  state: WorldState, policy: SafetyPolicy, now: number,
): WorldState {
  if (preview.aircraft_id !== session.aircraft_id || preview.baseline_key !== session.baseline_key || preview.input_key !== canonicalJson(input)) {
    throw new Error('The edit changed after preview. Preview the current fields before applying.');
  }
  // Recheck the live snapshot at commitment and rebuild the candidate from the
  // reviewed fields. An exported or mutated preview object is never the write source.
  return previewTrackEdit(session, input, state, policy, now).world;
}
