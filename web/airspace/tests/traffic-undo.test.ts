import { describe, expect, it } from 'vitest';
import { DEFAULT_POLICY, WorldState, canonicalJson } from '../src/core';
import { applyTrackEdit, beginTrackEdit, previewTrackEdit } from '../src/track-edit';
import { TrafficEditUndo, TrafficUndoContext } from '../src/traffic-undo';

const world = (): WorldState => ({
  version: 17, observed_at: 2400,
  aircraft: [
    { aircraft_id: 'UNDO101', x_nm: -7.25, y_nm: 1.125, altitude_ft: 10000, vx_nm_min: 1.375, vy_nm_min: -0, climb_ft_min: 0 },
    { aircraft_id: 'UNDO202', x_nm: 7.75, y_nm: 1.125, altitude_ft: 10000, vx_nm_min: -1.625, vy_nm_min: 0, climb_ft_min: 0 },
    { aircraft_id: 'UNDO303', x_nm: 9.875, y_nm: -8.625, altitude_ft: 24000, vx_nm_min: 0.125, vy_nm_min: 0.75, climb_ft_min: -125 },
  ],
});
const context = (): TrafficUndoContext => ({
  state: world(), policy: { ...DEFAULT_POLICY }, now: 2400, scenario: {},
});
function removeSecond(undo: TrafficEditUndo, before: TrafficUndoContext): TrafficUndoContext {
  const snapshot = undo.capture(before, 'UNDO202');
  const after = {
    ...before,
    state: { ...before.state, version: before.state.version + 1, aircraft: before.state.aircraft.filter(a => a.aircraft_id !== 'UNDO202') },
  };
  expect(undo.record('removal of UNDO202', snapshot, after)).toBe(true);
  return after;
}

describe('one-step authored traffic Undo', () => {
  it('recovers an accidentally removed aircraft, exact vectors/order and the previous selection in a new revision', () => {
    const undo = new TrafficEditUndo(), before = context(), after = removeSecond(undo, before);
    const unchanged = canonicalJson(after.state);
    const result = undo.take(after);
    expect(result.state.aircraft).toEqual(before.state.aircraft);
    expect(Object.is(result.state.aircraft[0]!.vy_nm_min, -0)).toBe(true);
    expect(result.selected).toBe('UNDO202');
    expect(result.state.version).toBe(after.state.version + 1);
    expect(result.state.observed_at).toBe(after.now);
    expect(canonicalJson(after.state)).toBe(unchanged);
    expect(undo.label(after)).toBeNull();
    expect(() => undo.take(after)).toThrow('No traffic edit');
  });

  it('receives a real selected-flight preview/apply without adding vector round-trip drift', () => {
    const undo = new TrafficEditUndo(), before = context();
    const captured = undo.capture(before, 'UNDO303');
    const session = beginTrackEdit(before.state, 'UNDO303', before.policy, before.now);
    const input = { ...session.input, x_nm: 3.625, flight_level: 245 };
    const preview = previewTrackEdit(session, input, before.state, before.policy, before.now);
    const after = { ...before, state: applyTrackEdit(session, preview, input, before.state, before.policy, before.now) };
    expect(undo.record('edit to UNDO303', captured, after)).toBe(true);
    const recovered = undo.take(after);
    expect(canonicalJson(recovered.state.aircraft)).toBe(canonicalJson(before.state.aircraft));
    expect(recovered.selected).toBe('UNDO303');
  });

  it('keeps only the most recent edit and restores that edit’s selection', () => {
    const undo = new TrafficEditUndo(), original = context(), first = removeSecond(undo, original);
    const captured = undo.capture(first, 'UNDO303');
    const second = { ...first, state: {
      ...first.state, version: first.state.version + 1,
      aircraft: first.state.aircraft.map(a => a.aircraft_id === 'UNDO303' ? { ...a, vx_nm_min: a.vx_nm_min + 0.4 } : a),
    } };
    expect(undo.record('vector change to UNDO303', captured, second)).toBe(true);
    const restored = undo.take(second);
    expect(restored.state.aircraft).toEqual(first.state.aircraft);
    expect(restored.selected).toBe('UNDO303');
    expect(restored.state.aircraft.some(a => a.aircraft_id === 'UNDO202')).toBe(false);
    expect(undo.label({ ...second, state: restored.state })).toBeNull();
  });

  it('preserves an applicable entry after a refused or unchanged edit', () => {
    const undo = new TrafficEditUndo(), after = removeSecond(undo, context());
    const captured = undo.capture(after, 'UNDO101');
    expect(undo.record('refused duplicate callsign', captured, after)).toBe(false);
    expect(undo.label(after)).toBe('removal of UNDO202');
    expect(undo.take(after).selected).toBe('UNDO202');
  });

  it('does not create an entry from a revision-only change', () => {
    const undo = new TrafficEditUndo(), before = context();
    const captured = undo.capture(before, 'UNDO101');
    expect(undo.record('no aircraft change', captured, {
      ...before, state: { ...before.state, version: before.state.version + 1 },
    })).toBe(false);
    expect(undo.label(before)).toBeNull();
  });

  const changedContexts: Array<[string, (value: TrafficUndoContext) => TrafficUndoContext]> = [
    ['world revision', c => ({ ...c, state: { ...c.state, version: c.state.version + 1 } })],
    ['observation time', c => ({ ...c, state: { ...c.state, observed_at: c.state.observed_at + 0.5 } })],
    ['aircraft state', c => ({ ...c, state: { ...c.state, aircraft: c.state.aircraft.map((a, i) => i ? a : { ...a, x_nm: a.x_nm + 0.125 }) } })],
    ['policy', c => ({ ...c, policy: { ...c.policy, min_horizontal_nm: c.policy.min_horizontal_nm + 0.5 } })],
    ['clock', c => ({ ...c, now: c.now + 0.5 })],
    ['same-valued new scenario', c => ({ ...c, state: { ...c.state, aircraft: c.state.aircraft.map(a => ({ ...a })) }, scenario: {} })],
  ];
  it.each(changedContexts)('permanently refuses stale restoration after a changed %s', (_name, change) => {
    const undo = new TrafficEditUndo(), after = removeSecond(undo, context()), changed = change(after);
    const unchanged = canonicalJson(changed.state);
    expect(undo.label(changed)).toBeNull();
    expect(() => undo.take(changed)).toThrow('No traffic edit');
    expect(canonicalJson(changed.state)).toBe(unchanged);
    expect(undo.label(after)).toBeNull();
    expect(() => undo.take(after)).toThrow('No traffic edit');
  });

  it('checks the context again at the actual Undo, without requiring a prior UI refresh', () => {
    const undo = new TrafficEditUndo(), after = removeSecond(undo, context());
    expect(undo.label(after)).not.toBeNull();
    const moved = { ...after, now: after.now + 1 };
    expect(() => undo.take(moved)).toThrow('No traffic edit');
    expect(undo.label(after)).toBeNull();
  });

  it('refuses an operation that crosses a scenario or policy boundary while recording', () => {
    const undo = new TrafficEditUndo(), before = context(), captured = undo.capture(before, 'UNDO202');
    const changed = { ...before, scenario: {}, state: { ...before.state, version: 18, aircraft: before.state.aircraft.slice(0, 1) } };
    expect(undo.record('scenario replacement', captured, changed)).toBe(false);
    expect(undo.label(changed)).toBeNull();
  });

  it('detaches and freezes the captured values before the caller can change them', () => {
    const undo = new TrafficEditUndo(), before = context(), captured = undo.capture(before, 'UNDO202')!;
    const expected = canonicalJson(before.state.aircraft);
    before.state.aircraft[0]!.x_nm = 100;
    expect(() => { captured.state.aircraft[0]!.x_nm = 999; }).toThrow();
    const after = { ...before, state: { ...before.state, version: 18, aircraft: before.state.aircraft.slice(0, 1) } };
    expect(undo.record('authored edit', captured, after)).toBe(true);
    expect(canonicalJson(undo.take(after).state.aircraft)).toBe(expected);
  });

  it('allows the final exact new revision but never offers an overflowing Undo', () => {
    const undo = new TrafficEditUndo(), before = context();
    before.state.version = Number.MAX_SAFE_INTEGER - 2;
    const after = removeSecond(undo, before);
    expect(undo.take(after).state.version).toBe(Number.MAX_SAFE_INTEGER);
    const last = context(); last.state.version = Number.MAX_SAFE_INTEGER - 1;
    const captured = undo.capture(last, 'UNDO202');
    const changed = { ...last, state: { ...last.state, version: Number.MAX_SAFE_INTEGER, aircraft: last.state.aircraft.slice(0, 1) } };
    expect(undo.record('last safe edit', captured, changed)).toBe(false);
    expect(undo.label(changed)).toBeNull();
  });

  it.each([NaN, Infinity, -1, 1.5, Number.MAX_SAFE_INTEGER + 1])('refuses an invalid version %s without changing the caller world', version => {
    const undo = new TrafficEditUndo(), before = context();
    before.state.version = version;
    expect(undo.capture(before, 'UNDO202')).toBeNull();
    expect(Object.is(before.state.version, version)).toBe(true);
  });

  it('invalidates on non-finite context or an explicit playback start and cannot revive a cleared entry', () => {
    const undo = new TrafficEditUndo(), after = removeSecond(undo, context());
    expect(undo.label({ ...after, now: NaN })).toBeNull();
    expect(undo.label(after)).toBeNull();
    const another = removeSecond(undo, context());
    undo.clear();
    expect(() => undo.take(another)).toThrow('No traffic edit');
  });
});
