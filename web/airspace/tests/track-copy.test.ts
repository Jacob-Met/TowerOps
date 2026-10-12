import { describe, expect, it } from 'vitest';
import { DEFAULT_POLICY, WorldState } from '../src/core';
import { TrackCopyInput, applyTrackCopy, beginTrackCopy, previewTrackCopy } from '../src/track-copy';

const original = (): WorldState => ({
  version: 7, observed_at: 1000,
  aircraft: [
    { aircraft_id: 'LEAD', x_nm: -6.125, y_nm: -0, altitude_ft: 10123.75, vx_nm_min: 1.234567890123, vy_nm_min: -0.375, climb_ft_min: 75.25 },
    { aircraft_id: 'OTHER', x_nm: 40, y_nm: 30, altitude_ft: 15000, vx_nm_min: -1, vy_nm_min: 0.5, climb_ft_min: 0 },
  ],
});
const input: TrackCopyInput = { aircraft_id: 'FOLLOW', east_nm: 2, north_nm: -1.5, altitude_ft: 1234.5 };
const preview = (world = original(), fields = input) => previewTrackCopy(beginTrackCopy(world, 'LEAD', DEFAULT_POLICY, 1002), fields, world, DEFAULT_POLICY, 1002);

describe('copy a selected trajectory', () => {
  it('adds one independent translated track without changing original flights or their order', () => {
    const world = original(), before = structuredClone(world), result = preview(world);
    expect(world).toEqual(before); expect(result.world.aircraft.slice(0, 2)).toEqual(before.aircraft);
    expect(result.world.version).toBe(8); expect(result.world.observed_at).toBe(1002);
    expect(result.world.aircraft[2]).toEqual({ ...before.aircraft[0], aircraft_id: 'FOLLOW', x_nm: -4.125, y_nm: -1.5, altitude_ft: 11358.25 });
    result.world.aircraft[0]!.x_nm = 200; result.world.aircraft[2]!.vx_nm_min = 900;
    expect(world).toEqual(before);
  });
  it('keeps zero offsets and the exact vector, including signed zeros and unusual imported speeds', () => {
    const world = original(); world.aircraft[0]!.vx_nm_min = 7.123456789012345; world.aircraft[0]!.vy_nm_min = -0;
    const copied = preview(world, { ...input, east_nm: 0, north_nm: -0, altitude_ft: 0 }).world.aircraft[2]!;
    for (const key of ['x_nm', 'y_nm', 'altitude_ft', 'vx_nm_min', 'vy_nm_min', 'climb_ft_min'] as const) expect(Object.is(copied[key], world.aircraft[0]![key])).toBe(true);
  });
  it('normalizes a new callsign and accepts zero final altitude', () => {
    expect(preview(original(), { ...input, aircraft_id: ' new_2-x ', altitude_ft: -10123.75 }).world.aircraft[2]!.aircraft_id).toBe('NEW_2-X');
    expect(preview(original(), { ...input, altitude_ft: -10123.75 }).world.aircraft[2]!.altitude_ft).toBe(0);
  });
  it('shows introduced conflicts, retaining current intervals and the complete policy calculation', () => {
    const result = preview(original(), { ...input, east_nm: 0, north_nm: 0, altitude_ft: 0 });
    expect(result.before).toEqual([]); expect(result.after).toHaveLength(1);
    expect(result.after[0]).toMatchObject({ aircraft_a: 'LEAD', aircraft_b: 'FOLLOW', start_min: 0, end_min: DEFAULT_POLICY.horizon_min });
  });
  it.each(['LEAD', ' lead ', '', 'TOO-LONG-123', '<script>', 'é'])('rejects unavailable or invalid callsign %s', id => {
    const world = original(), before = structuredClone(world);
    expect(() => preview(world, { ...input, aircraft_id: id })).toThrow(); expect(world).toEqual(before);
  });
  it.each(['east_nm', 'north_nm', 'altitude_ft'] as const)('rejects non-finite %s without a partial addition', key => {
    for (const number of [NaN, Infinity, -Infinity]) expect(() => preview(original(), { ...input, [key]: number })).toThrow(/finite/);
  });
  it('rejects arithmetic overflow and a below-ground result', () => {
    const world = original(); world.aircraft[0]!.x_nm = Number.MAX_VALUE;
    expect(() => preview(world, { ...input, east_nm: Number.MAX_VALUE })).toThrow(/finite/);
    expect(() => preview(original(), { ...input, altitude_ft: -10124 })).toThrow(/zero or above/);
  });
  it('admits flight 60 and refuses flight 61', () => {
    const world = original();
    while (world.aircraft.length < 59) world.aircraft.push({ ...world.aircraft[0]!, aircraft_id: 'A' + world.aircraft.length, altitude_ft: 50000 });
    expect(preview(world).world.aircraft).toHaveLength(60);
    world.aircraft.push({ ...world.aircraft[0]!, aircraft_id: 'LAST' }); expect(() => preview(world)).toThrow(/60/);
  });
  it.each([Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER + 1, -1, 1.5])('refuses nonincrementable revision %s', version => {
    const world = original(); world.version = version; expect(() => preview(world)).toThrow(/version/);
  });
  it('refuses missing or ambiguous source selection', () => {
    const world = original(); expect(() => beginTrackCopy(world, 'ABSENT', DEFAULT_POLICY, 1002)).toThrow(/one existing/);
    world.aircraft.push({ ...world.aircraft[0]! }); expect(() => beginTrackCopy(world, 'LEAD', DEFAULT_POLICY, 1002)).toThrow(/one existing/);
  });
  it('binds preview and commit to the complete world, policy and clock', () => {
    const world = original(), session = beginTrackCopy(world, 'LEAD', DEFAULT_POLICY, 1002), reviewed = preview(world);
    const changes = [() => applyTrackCopy(session, reviewed, input, world, DEFAULT_POLICY, 1003),
      () => applyTrackCopy(session, reviewed, input, world, { ...DEFAULT_POLICY, max_state_age_sec: 11 }, 1002),
      () => applyTrackCopy(session, reviewed, input, { ...world, aircraft: [...world.aircraft].reverse() }, DEFAULT_POLICY, 1002)];
    for (const change of changes) expect(change).toThrow(/changed/);
    world.aircraft[1]!.vx_nm_min += 0.1; expect(() => applyTrackCopy(session, reviewed, input, world, DEFAULT_POLICY, 1002)).toThrow(/changed/);
  });
  it('rebuilds from the reviewed inputs and refuses changed fields or replay after commitment', () => {
    const world = original(), session = beginTrackCopy(world, 'LEAD', DEFAULT_POLICY, 1002), reviewed = preview(world);
    reviewed.world.aircraft.length = 0; reviewed.world.version = 123;
    const committed = applyTrackCopy(session, reviewed, input, world, DEFAULT_POLICY, 1002);
    expect(committed).toEqual(preview(world).world);
    expect(() => applyTrackCopy(session, reviewed, { ...input, north_nm: 3 }, world, DEFAULT_POLICY, 1002)).toThrow(/after preview/);
    expect(() => applyTrackCopy(session, reviewed, input, committed, DEFAULT_POLICY, 1002)).toThrow(/changed/);
  });
});
