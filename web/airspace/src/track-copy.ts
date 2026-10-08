import { SafetyPolicy, WorldState, canonicalJson } from './core';
import { ConflictWindow, conflictWindows } from './world-tools';

export interface TrackCopyInput {
  aircraft_id: string;
  east_nm: number;
  north_nm: number;
  altitude_ft: number;
}
export interface TrackCopySession { source_id: string; baseline_key: string }
export interface TrackCopyPreview {
  source_id: string;
  baseline_key: string;
  input_key: string;
  world: WorldState;
  before: ConflictWindow[];
  after: ConflictWindow[];
}
const snapshotKey = (world: WorldState, policy: SafetyPolicy, now: number): string =>
  canonicalJson({ world, policy, now });

export function beginTrackCopy(
  world: WorldState, source_id: string, policy: SafetyPolicy, now: number,
): TrackCopySession {
  if (world.aircraft.filter(a => a.aircraft_id === source_id).length !== 1) {
    throw new Error('Select one existing flight to copy.');
  }
  return { source_id, baseline_key: snapshotKey(world, policy, now) };
}

export function previewTrackCopy(
  session: TrackCopySession, input: TrackCopyInput,
  world: WorldState, policy: SafetyPolicy, now: number,
): TrackCopyPreview {
  if (snapshotKey(world, policy, now) !== session.baseline_key) {
    throw new Error('The world, clock or policy changed. Start a fresh copy.');
  }
  if (!Number.isSafeInteger(world.version) || world.version < 0 || world.version >= Number.MAX_SAFE_INTEGER) {
    throw new Error('This world version cannot be incremented exactly.');
  }
  if (world.aircraft.length >= 60) throw new Error('A world can contain at most 60 flights. Remove one before copying.');
  const id = input.aircraft_id.trim().toUpperCase();
  if (!/^[A-Z0-9_-]{1,10}$/.test(id)) throw new Error('Use a callsign of 1–10 letters, digits, underscores or hyphens.');
  if (world.aircraft.some(a => a.aircraft_id === id)) throw new Error(`Callsign ${id} already exists.`);
  if (![input.east_nm, input.north_nm, input.altitude_ft, now].every(Number.isFinite)) {
    throw new Error('Every offset and the current clock must be a finite number.');
  }
  const original = world.aircraft.find(a => a.aircraft_id === session.source_id);
  if (!original) throw new Error('The source flight is no longer available.');
  // Copy the native vector directly. Bearing/speed conversion would introduce drift.
  // A zero offset retains the source numeric value, including signed zero.
  const offset = (value: number, delta: number) => delta === 0 ? value : value + delta;
  const aircraft = {
    ...original, aircraft_id: id,
    x_nm: offset(original.x_nm, input.east_nm),
    y_nm: offset(original.y_nm, input.north_nm),
    altitude_ft: offset(original.altitude_ft, input.altitude_ft),
  };
  if (![aircraft.x_nm, aircraft.y_nm, aircraft.altitude_ft, aircraft.vx_nm_min, aircraft.vy_nm_min, aircraft.climb_ft_min].every(Number.isFinite)) {
    throw new Error('The copied track must have finite position and velocity values.');
  }
  if (aircraft.altitude_ft < 0) throw new Error('The copied altitude must be zero or above.');
  const candidate = {
    ...world, version: world.version + 1, observed_at: now,
    aircraft: [...world.aircraft.map(a => ({ ...a })), aircraft],
  };
  return {
    source_id: session.source_id, baseline_key: session.baseline_key,
    input_key: canonicalJson(input), world: candidate,
    before: conflictWindows(world, policy), after: conflictWindows(candidate, policy),
  };
}

export function applyTrackCopy(
  session: TrackCopySession, preview: TrackCopyPreview, input: TrackCopyInput,
  world: WorldState, policy: SafetyPolicy, now: number,
): WorldState {
  if (preview.source_id !== session.source_id || preview.baseline_key !== session.baseline_key || preview.input_key !== canonicalJson(input)) {
    throw new Error('The copy changed after preview. Preview the current fields again.');
  }
  // Commit from current, revalidated inputs; never trust a mutable preview world.
  return previewTrackCopy(session, input, world, policy, now).world;
}
