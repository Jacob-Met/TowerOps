import { describe, expect, it } from 'vitest';
import { Aircraft, DEFAULT_POLICY, SafetyPolicy, WorldState, pairConflict } from '../src/core';
import { analyzeEncounter, separationAt } from '../src/encounter';

const flight = (aircraft_id: string, overrides: Partial<Aircraft> = {}): Aircraft => ({
  aircraft_id, x_nm: 0, y_nm: 0, altitude_ft: 10000,
  vx_nm_min: 1, vy_nm_min: 0, climb_ft_min: 0, ...overrides,
});
const policy: SafetyPolicy = { ...DEFAULT_POLICY, min_horizontal_nm: 2, horizon_min: 10 };
const world = (b: Partial<Aircraft> = {}, a: Partial<Aircraft> = {}): WorldState => ({
  version: 7, observed_at: 300, aircraft: [flight('ALPHA', a), flight('BRAVO', { x_nm: 10, vx_nm_min: -1, ...b })],
});

describe('read-only encounter exploration', () => {
  it('finds exact crossing windows and closest approach, including both horizon endpoints', () => {
    const state = world(), result = analyzeEncounter(state, 'ALPHA', 'BRAVO', policy);
    expect(result.horizontal_window).toEqual([4, 6]);
    expect(result.vertical_window).toEqual([0, 10]);
    expect(result.overlap).toEqual([4, 6]);
    expect(result.closest_horizontal_min).toBe(5);
    expect(result.samples).toHaveLength(81);
    expect(result.samples[0]).toMatchObject({ minutes: 0, horizontal_nm: 10, vertical_ft: 0, simultaneous: false });
    expect(result.samples.at(-1)).toMatchObject({ minutes: 10, horizontal_nm: 10, simultaneous: false });
  });
  it('uses strict threshold equality at entry and exit, with a distinct unsafe interior', () => {
    const state = world();
    for (const minutes of [4, 6]) expect(separationAt(state, 'ALPHA', 'BRAVO', policy, minutes)).toMatchObject({ horizontal_nm: 2, simultaneous: false });
    expect(separationAt(state, 'ALPHA', 'BRAVO', policy, 5)).toMatchObject({ horizontal_nm: 0, simultaneous: true });
  });
  it('does not conflate separately unsafe horizontal and vertical periods', () => {
    const state = world({ altitude_ft: 15000, climb_ft_min: -500 });
    const result = analyzeEncounter(state, 'ALPHA', 'BRAVO', policy);
    expect(result.horizontal_window).toEqual([4, 6]);
    expect(result.vertical_window).toEqual([8, 10]);
    expect(result.overlap).toBeNull();
    expect(separationAt(state, 'ALPHA', 'BRAVO', policy, 5)).toMatchObject({ horizontal_below: true, vertical_below: false, simultaneous: false });
    expect(separationAt(state, 'ALPHA', 'BRAVO', policy, 9)).toMatchObject({ horizontal_below: false, vertical_below: true, simultaneous: false });
  });
  it('retains a sub-sample overlap that the drawn points do not discover', () => {
    const narrow = { ...policy, min_horizontal_nm: 0.002 };
    const state = world({ x_nm: 10.06 });
    const result = analyzeEncounter(state, 'ALPHA', 'BRAVO', narrow);
    expect(result.overlap).not.toBeNull();
    expect(result.overlap![0]).toBeCloseTo(5.029, 8);
    expect(result.overlap![1]).toBeCloseTo(5.031, 8);
    expect(result.samples.some(sample => sample.simultaneous)).toBe(false);
    const mid = (result.overlap![0] + result.overlap![1]) / 2;
    expect(separationAt(state, 'ALPHA', 'BRAVO', narrow, mid).simultaneous).toBe(true);
  });
  it('treats a horizontal tangent as no intrusion', () => {
    const state = world({ y_nm: 2 });
    expect(analyzeEncounter(state, 'ALPHA', 'BRAVO', policy).overlap).toBeNull();
    expect(separationAt(state, 'ALPHA', 'BRAVO', policy, 5)).toMatchObject({ horizontal_nm: 2, simultaneous: false });
  });
  it('handles vertical crossing while horizontal separation is constant', () => {
    const state = world({ x_nm: 1, vx_nm_min: 1, altitude_ft: 12000, climb_ft_min: -1000 });
    const result = analyzeEncounter(state, 'ALPHA', 'BRAVO', policy);
    expect(result.horizontal_window).toEqual([0, 10]);
    expect(result.vertical_window).toEqual([1, 3]);
    expect(result.overlap).toEqual([1, 3]);
    expect(result.closest_horizontal_min).toBe(0);
    expect(separationAt(state, 'ALPHA', 'BRAVO', policy, 1).vertical_below).toBe(false);
    expect(separationAt(state, 'ALPHA', 'BRAVO', policy, 2).vertical_ft).toBe(0);
  });
  it('shows a complete unsafe interval for coincident stationary tracks', () => {
    const state = world({ x_nm: 0, vx_nm_min: 0 }, { vx_nm_min: 0 });
    const result = analyzeEncounter(state, 'ALPHA', 'BRAVO', policy);
    expect(result.overlap).toEqual([0, 10]);
    expect(result.closest_horizontal_min).toBe(0);
    expect(result.samples.every(sample => sample.simultaneous)).toBe(true);
  });
  it('bounds closest approach to the available future, including a receding pair', () => {
    expect(analyzeEncounter(world({ x_nm: -10 }), 'ALPHA', 'BRAVO', policy).closest_horizontal_min).toBe(0);
    expect(analyzeEncounter(world({ x_nm: 100 }), 'ALPHA', 'BRAVO', policy).closest_horizontal_min).toBe(10);
  });
  it('respects a changed look-ahead and envelope immediately', () => {
    const state = world();
    expect(analyzeEncounter(state, 'ALPHA', 'BRAVO', { ...policy, horizon_min: 3 }).overlap).toBeNull();
    expect(analyzeEncounter(state, 'ALPHA', 'BRAVO', { ...policy, min_horizontal_nm: 4 }).overlap).toEqual([3, 7]);
    expect(analyzeEncounter(state, 'ALPHA', 'BRAVO', { ...policy, min_vertical_ft: 500 }).vertical_window).toEqual([0, 10]);
  });
  it('uses only the chosen pair in multi-flight traffic', () => {
    const state = world();
    state.aircraft.push(flight('CHARLIE', { y_nm: 50 }));
    expect(analyzeEncounter(state, 'ALPHA', 'BRAVO', policy).overlap).toEqual([4, 6]);
    expect(analyzeEncounter(state, 'ALPHA', 'CHARLIE', policy).overlap).toBeNull();
  });
  it('is symmetric under pair order and does not depend on the input array order', () => {
    const state = world({ y_nm: 1, altitude_ft: 11000, climb_ft_min: -250 });
    const forward = analyzeEncounter(state, 'ALPHA', 'BRAVO', policy);
    const reverse = analyzeEncounter({ ...state, aircraft: [...state.aircraft].reverse() }, 'BRAVO', 'ALPHA', policy);
    for (const key of ['horizontal_window', 'vertical_window', 'overlap', 'closest_horizontal_min', 'samples'] as const) expect(reverse[key]).toEqual(forward[key]);
  });
  it('agrees with the existing continuous policy across distinct ordinary geometries', () => {
    for (const x of [-20, 0, 10, 40]) for (const y of [0, 2, 3]) for (const z of [0, 1000, 5000]) {
      const state = world({ x_nm: x, y_nm: y, altitude_ft: 10000 + z, climb_ft_min: -500 });
      expect(!!analyzeEncounter(state, 'ALPHA', 'BRAVO', policy).overlap).toBe(pairConflict(state.aircraft[0]!, state.aircraft[1]!, policy));
    }
  });
  it('does not mutate or alias world, aircraft, policy, version or observation time', () => {
    const state = world(), before = JSON.stringify(state), rules = Object.freeze({ ...policy });
    state.aircraft.forEach(Object.freeze); Object.freeze(state.aircraft); Object.freeze(state);
    const result = analyzeEncounter(state, 'ALPHA', 'BRAVO', rules);
    separationAt(state, 'ALPHA', 'BRAVO', rules, 7.25);
    result.samples[0]!.horizontal_nm = 900;
    expect(JSON.stringify(state)).toBe(before);
    expect(rules).toEqual(policy);
  });
  it.each([NaN, Infinity, -Infinity, -1, 10.0001])('rejects cursor %s without changing inputs', minutes => {
    const state = world(), before = JSON.stringify(state);
    expect(() => separationAt(state, 'ALPHA', 'BRAVO', policy, minutes)).toThrow();
    expect(JSON.stringify(state)).toBe(before);
  });
  it('rejects absent or duplicate selection rather than inventing an empty encounter', () => {
    expect(() => analyzeEncounter(world(), 'ALPHA', 'ALPHA', policy)).toThrow('different');
    expect(() => analyzeEncounter(world(), 'ALPHA', 'MISSING', policy)).toThrow('exist');
  });
  it.each([
    { name: 'horizontal', a: { x_nm: 1e16, vx_nm_min: 1e16 }, b: { x_nm: 1e16 + 4, vx_nm_min: 1e16 }, horizontal_nm: 4, vertical_ft: 0 },
    { name: 'vertical', a: { vx_nm_min: 0, altitude_ft: 1e19, climb_ft_min: 1e19 }, b: { x_nm: 0, vx_nm_min: 0, altitude_ft: 1e19 + 2048, climb_ft_min: 1e19 }, horizontal_nm: 0, vertical_ft: 2048 },
  ])('keeps a constant gap under shared $name motion', ({ a, b, horizontal_nm, vertical_ft }) => {
    const state = world(b, a), before = JSON.stringify(state);
    const rules = { ...policy, min_horizontal_nm: 3, horizon_min: 5 };
    const encounter = analyzeEncounter(state, 'ALPHA', 'BRAVO', rules);
    expect(encounter.overlap).toBeNull();
    expect(pairConflict(state.aircraft[0]!, state.aircraft[1]!, rules)).toBe(false);
    expect(separationAt(state, 'ALPHA', 'BRAVO', rules, 3)).toMatchObject({ horizontal_nm, vertical_ft, simultaneous: false });
    for (const point of encounter.samples) expect(point).toMatchObject({ horizontal_nm, vertical_ft, simultaneous: false });
    expect(JSON.stringify(state)).toBe(before);
  });
  it('keeps the exact vertical minimum safe under a large shared climb', () => {
    const state = world(
      { x_nm: 0, vx_nm_min: 0, altitude_ft: 1e16 + 500, climb_ft_min: 1e16 },
      { vx_nm_min: 0, altitude_ft: 1e16, climb_ft_min: 1e16 },
    );
    const rules = { ...policy, min_vertical_ft: 500, horizon_min: 5 };
    const encounter = analyzeEncounter(state, 'ALPHA', 'BRAVO', rules);
    expect(encounter.overlap).toBeNull();
    expect(separationAt(state, 'ALPHA', 'BRAVO', rules, 3)).toMatchObject({ vertical_ft: 500, vertical_below: false, simultaneous: false });
    for (const point of encounter.samples) expect(point).toMatchObject({ vertical_ft: 500, vertical_below: false, simultaneous: false });
  });
  it('refuses malformed or unrepresentable forecasting arithmetic', () => {
    expect(() => analyzeEncounter(world({ altitude_ft: NaN }), 'ALPHA', 'BRAVO', policy)).toThrow('finite');
    expect(() => analyzeEncounter(world({ x_nm: 1e200 }), 'ALPHA', 'BRAVO', policy)).toThrow('finite');
    expect(() => separationAt(world({ vx_nm_min: 1e308 }, { vx_nm_min: 1e308 }), 'ALPHA', 'BRAVO', policy, 3)).toThrow('finite');
    expect(() => analyzeEncounter(world(), 'ALPHA', 'BRAVO', { ...policy, horizon_min: 0 })).toThrow('positive');
    expect(() => analyzeEncounter(world(), 'ALPHA', 'BRAVO', { ...policy, min_horizontal_nm: Infinity })).toThrow('finite');
  });
});
