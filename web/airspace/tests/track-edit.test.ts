import { describe, expect, it } from 'vitest';
import { DEFAULT_POLICY, WorldState, canonicalJson, conflictPairs } from '../src/core';
import { applyTrackEdit, beginTrackEdit, previewTrackEdit } from '../src/track-edit';

function crossing(): WorldState {
  return {
    version: 7, observed_at: 1000,
    aircraft: [
      { aircraft_id: 'EAST1', x_nm: -6, y_nm: 0, altitude_ft: 10000, vx_nm_min: 1, vy_nm_min: 0, climb_ft_min: 0 },
      { aircraft_id: 'WEST1', x_nm: 6, y_nm: 0, altitude_ft: 10000, vx_nm_min: -1, vy_nm_min: 0, climb_ft_min: 0 },
    ],
  };
}

describe('selected-flight what-if edits', () => {
  it.each([
    [0, 1, 0], [1, 0, 90], [0, -1, 180], [-1, 0, 270], [0, 0, 0],
  ])('prefills vector (%s, %s) with bearing %s degrees', (vx, vy, expected) => {
    const state = crossing();
    state.aircraft[0]!.vx_nm_min = vx;
    state.aircraft[0]!.vy_nm_min = vy;
    const session = beginTrackEdit(state, 'EAST1', DEFAULT_POLICY, 1002);
    expect(session.input.bearing_deg).toBeCloseTo(expected);
    expect(session.input.speed_kt).toBeCloseTo(Math.hypot(vx, vy) * 60);
    expect(session.input.flight_level).toBe(100);
    expect(session.aircraft_id).toBe('EAST1');
  });

  it('previews a resolved crossing without mutating the original world', () => {
    const state = crossing();
    const before = canonicalJson(state);
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    const input = { ...session.input, flight_level: 120 };
    const preview = previewTrackEdit(session, input, state, DEFAULT_POLICY, 1002);
    expect(canonicalJson(state)).toBe(before);
    expect(preview.before).toHaveLength(1);
    expect(preview.before[0]!.start_min).toBeCloseTo(3.5);
    expect(preview.after).toEqual([]);
    expect(preview.world.aircraft[0]).toEqual(state.aircraft[0]);
    expect(preview.world.aircraft[1]!.aircraft_id).toBe('WEST1');
    expect(preview.world.aircraft[1]!.altitude_ft).toBe(12000);
    expect(preview.world.version).toBe(8);
    expect(preview.world.observed_at).toBe(1002);
  });

  it('shows introduced conflicts as editable scenario data', () => {
    const state = crossing();
    state.aircraft[1]!.altitude_ft = 12000;
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    const input = { ...session.input, flight_level: 100 };
    const preview = previewTrackEdit(session, input, state, DEFAULT_POLICY, 1002);
    expect(preview.before).toEqual([]);
    expect(preview.after).toHaveLength(1);
    const applied = applyTrackEdit(session, preview, input, state, DEFAULT_POLICY, 1002);
    expect(conflictPairs(applied, DEFAULT_POLICY)).toEqual([['EAST1', 'WEST1']]);
    expect(state.aircraft[1]!.altitude_ft).toBe(12000);
  });

  it('changes bearing and speed using the same conversion as the flight builder', () => {
    const state = crossing();
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    const input = { ...session.input, bearing_deg: 90, speed_kt: 120, climb_ft_min: 500 };
    const preview = previewTrackEdit(session, input, state, DEFAULT_POLICY, 1002);
    const track = preview.world.aircraft[1]!;
    expect(track.vx_nm_min).toBeCloseTo(2);
    expect(track.vy_nm_min).toBeCloseTo(0);
    expect(track.climb_ft_min).toBe(500);
  });

  it('retains untouched vectors and numeric values exactly during an unrelated edit', () => {
    const state = crossing();
    Object.assign(state.aircraft[0]!, {
      x_nm: -0, altitude_ft: 12345.6789012345,
      vx_nm_min: 0.123456789012345, vy_nm_min: -2.34567890123456,
      climb_ft_min: -0,
    });
    const session = beginTrackEdit(state, 'EAST1', DEFAULT_POLICY, 1002);
    // A numeric input renders -0 as 0. That must not alter untouched source bytes.
    const input = { ...session.input, x_nm: 0, climb_ft_min: 0, y_nm: 4 };
    const preview = previewTrackEdit(session, input, state, DEFAULT_POLICY, 1002);
    const expected = { ...state.aircraft[0]!, y_nm: 4 };
    expect(canonicalJson(preview.world.aircraft[0])).toBe(canonicalJson(expected));
  });

  it('treats equivalent full-turn bearings as unchanged', () => {
    const state = crossing();
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    const input = { ...session.input, bearing_deg: session.input.bearing_deg + 360, y_nm: 3 };
    const preview = previewTrackEdit(session, input, state, DEFAULT_POLICY, 1002);
    expect(preview.world.aircraft[1]!.vx_nm_min).toBe(-1);
    expect(Object.is(preview.world.aircraft[1]!.vy_nm_min, 0)).toBe(true);
  });

  it('refuses a no-op instead of advancing the world version', () => {
    const state = crossing();
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    expect(() => previewTrackEdit(session, session.input, state, DEFAULT_POLICY, 1002)).toThrow(/Change at least one/);
    expect(state.version).toBe(7);
  });

  it.each([
    ['x_nm', NaN], ['y_nm', Infinity], ['flight_level', -1],
    ['flight_level', Number.MAX_VALUE], ['bearing_deg', NaN],
    ['speed_kt', -1], ['speed_kt', 361], ['climb_ft_min', 3001],
  ])('refuses invalid %s=%s and retains the source', (field, value) => {
    const state = crossing();
    const before = canonicalJson(state);
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    expect(() => previewTrackEdit(session, { ...session.input, [field]: value }, state, DEFAULT_POLICY, 1002)).toThrow();
    expect(canonicalJson(state)).toBe(before);
  });

  it('requires an existing unambiguous target', () => {
    const state = crossing();
    expect(() => beginTrackEdit(state, 'MISSING', DEFAULT_POLICY, 1002)).toThrow(/existing flight/);
    state.aircraft.push({ ...state.aircraft[1]! });
    expect(() => beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002)).toThrow(/existing flight/);
  });

  it.each([Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER + 1])('refuses version %s rather than reuse its identity', version => {
    const state = crossing();
    state.version = version;
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    expect(() => previewTrackEdit(session, { ...session.input, flight_level: 120 }, state, DEFAULT_POLICY, 1002)).toThrow(/incremented exactly/);
  });

  it('requires another preview when edited values change after review', () => {
    const state = crossing();
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    const input = { ...session.input, flight_level: 120 };
    const preview = previewTrackEdit(session, input, state, DEFAULT_POLICY, 1002);
    expect(() => applyTrackEdit(session, preview, { ...input, flight_level: 125 }, state, DEFAULT_POLICY, 1002)).toThrow(/changed after preview/);
    expect(state.version).toBe(7);
  });

  it('refuses another flight\'s preview even when the snapshot and numeric fields match', () => {
    const state = crossing();
    const first = beginTrackEdit(state, 'EAST1', DEFAULT_POLICY, 1002);
    const second = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    const input = { ...first.input, flight_level: 120, x_nm: 3 };
    const preview = previewTrackEdit(first, input, state, DEFAULT_POLICY, 1002);
    expect(() => applyTrackEdit(second, preview, input, state, DEFAULT_POLICY, 1002)).toThrow(/changed after preview/);
    expect(state.version).toBe(7);
    expect(state.aircraft.every(a => a.altitude_ft === 10000)).toBe(true);
  });

  it.each(['world', 'version', 'policy', 'clock', 'removed target'])('refuses a preview after a changed %s', change => {
    const state = crossing();
    const policy = { ...DEFAULT_POLICY };
    const session = beginTrackEdit(state, 'WEST1', policy, 1002);
    const input = { ...session.input, flight_level: 120 };
    const preview = previewTrackEdit(session, input, state, policy, 1002);
    let now = 1002;
    if (change === 'world') state.aircraft[0]!.x_nm += 0.1;
    if (change === 'version') state.version++;
    if (change === 'policy') policy.horizon_min++;
    if (change === 'clock') now++;
    if (change === 'removed target') state.aircraft.pop();
    const afterChange = canonicalJson(state);
    expect(() => applyTrackEdit(session, preview, input, state, policy, now)).toThrow(/world, clock or policy changed/);
    expect(canonicalJson(state)).toBe(afterChange);
  });

  it('isolates preview data and reconstructs the reviewed candidate at apply', () => {
    const state = crossing();
    const original = canonicalJson(state);
    const session = beginTrackEdit(state, 'WEST1', DEFAULT_POLICY, 1002);
    const input = { ...session.input, flight_level: 120 };
    const preview = previewTrackEdit(session, input, state, DEFAULT_POLICY, 1002);
    preview.world.aircraft[0]!.x_nm = 999;
    preview.world.aircraft[1]!.altitude_ft = 1;
    expect(canonicalJson(state)).toBe(original);
    const applied = applyTrackEdit(session, preview, input, state, DEFAULT_POLICY, 1002);
    expect(applied.aircraft[0]).toEqual(state.aircraft[0]);
    expect(applied.aircraft[1]!.altitude_ft).toBe(12000);
    expect(applied.version).toBe(8);
    expect(() => applyTrackEdit(session, preview, input, applied, DEFAULT_POLICY, 1002)).toThrow(/world, clock or policy changed/);
  });
});
