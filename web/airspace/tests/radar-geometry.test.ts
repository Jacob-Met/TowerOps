import { describe, expect, it } from 'vitest';
import reference from './python-reference.json';
import { Aircraft, DEFAULT_POLICY, WorldState, projected } from '../src/core';
import { parseWorldState } from '../src/world-tools';
import { fitRadar, radarPoint, radarRangeLabel, radarTicks, radarViewport } from '../src/radar-geometry';

const plane = (id: string, x: number, y: number, vx = 0, vy = 0): Aircraft => ({
  aircraft_id: id, x_nm: x, y_nm: y, altitude_ft: 10000,
  vx_nm_min: vx, vy_nm_min: vy, climb_ft_min: 0,
});
const world = (...aircraft: Aircraft[]): WorldState => ({ version: 1, observed_at: 1000, aircraft });
const policy = { ...DEFAULT_POLICY };
const translate = (state: WorldState, dx: number, dy: number): WorldState => ({
  ...state, aircraft: state.aircraft.map(a => ({ ...a, x_nm: a.x_nm + dx, y_nm: a.y_nm + dy })),
});

describe('traffic radar framing', () => {
  it('preserves relative screen geometry under a valid common translation', () => {
    const near = world(plane('WEST', -2, 0), plane('EAST', 2, 0));
    const far = parseWorldState(translate(near, 1000, -1500));
    const nearFrame = fitRadar(near, policy)!, farFrame = fitRadar(far, policy)!;
    expect(farFrame.half_range_nm).toBe(nearFrame.half_range_nm);
    for (const [width, height] of [[708, 536], [268, 436], [908, 236]]) {
      const a = radarViewport(nearFrame, width!, height!)!, b = radarViewport(farFrame, width!, height!)!;
      near.aircraft.forEach((flight, i) => {
        const p = radarPoint(a, flight.x_nm, flight.y_nm), moved = far.aircraft[i]!;
        const q = radarPoint(b, moved.x_nm, moved.y_nm);
        expect(q[0]).toBeCloseTo(p[0], 10); expect(q[1]).toBeCloseTo(p[1], 10);
      });
    }
  });

  it('frames both current traffic and the existing look-ahead endpoints with margin', () => {
    const state = world(plane('FAST', 1000, -500, 6, -4), plane('STILL', 994, -494));
    const frame = fitRadar(state, policy)!;
    expect(frame.center_x_nm).toBe(1012);
    expect(frame.center_y_nm).toBe(-507);
    for (const a of state.aircraft) for (const p of [a, projected(a, policy.horizon_min)]) {
      expect(frame.half_range_nm - Math.abs(p.x_nm - frame.center_x_nm)).toBeGreaterThanOrEqual(2);
      expect(frame.half_range_nm - Math.abs(p.y_nm - frame.center_y_nm)).toBeGreaterThanOrEqual(2);
    }
  });

  it('uses an isotropic scale and positive east/right and north/up directions', () => {
    const view = radarViewport(fitRadar(world(plane('A', 1000, 1000)), policy)!, 600, 300)!;
    const [x, y] = radarPoint(view, 1000, 1000);
    expect([x, y]).toEqual([300, 150]);
    expect(radarPoint(view, 1001, 1000)).toEqual([310, 150]);
    expect(radarPoint(view, 1000, 1001)).toEqual([300, 140]);
    expect(radarPoint(view, 999, 999)).toEqual([290, 160]);
  });

  it('gives empty, single and coincident traffic a stable nonzero range', () => {
    expect(fitRadar(world(), policy)).toEqual({ center_x_nm: 0, center_y_nm: 0, half_range_nm: 15 });
    for (const state of [world(plane('ONE', 42, -70)), world(plane('ONE', 42, -70), plane('TWO', 42, -70))]) {
      expect(fitRadar(state, policy)).toEqual({ center_x_nm: 42, center_y_nm: -70, half_range_nm: 15 });
    }
    // Empty traffic is a defensive drawing boundary, not a relaxed import contract.
    expect(() => parseWorldState(world())).toThrow('Supply between 1 and 60 aircraft.');
  });

  it('keeps every canonical fixture current/end point inside landscape and narrow plots', () => {
    for (const fixture of reference.scenarios) for (const [width, height] of [[708, 536], [268, 436]]) {
      const state = fixture.state as WorldState;
      const view = radarViewport(fitRadar(state, policy)!, width!, height!)!;
      for (const a of state.aircraft) for (const p of [a, projected(a, policy.horizon_min)]) {
        const [x, y] = radarPoint(view, p.x_nm, p.y_nm);
        expect(x).toBeGreaterThan(0); expect(x).toBeLessThan(width!);
        expect(y).toBeGreaterThan(0); expect(y).toBeLessThan(height!);
      }
    }
  });

  it('labels absolute signed ticks rather than recentering coordinate values to zero', () => {
    expect(radarTicks(985, 1015, 6)).toEqual([985, 990, 995, 1000, 1005, 1010, 1015]);
    expect(radarTicks(-15, 15, 6)).toEqual([-15, -10, -5, 0, 5, 10, 15]);
    expect(radarTicks(-15, 15, 6).some(n => Object.is(n, -0))).toBe(false);
  });

  it('bounds grid work for extreme finite intervals and rejects nonfinite intervals', () => {
    for (const [min, max] of [[-1e308, 1e308], [1e20, 1e20 + 65536], [-1e-200, 1e-200]]) {
      const ticks = radarTicks(min!, max!, 1e6);
      expect(ticks.length).toBeLessThanOrEqual(64);
      expect(ticks.every(Number.isFinite)).toBe(true);
      expect(ticks.every((v, i) => i === 0 || v > ticks[i - 1]!)).toBe(true);
    }
    expect(radarTicks(-Infinity, Infinity, 6)).toEqual([]);
    expect(radarTicks(0, 1, NaN)).toEqual([]);
  });

  it('explicitly marks admitted finite overflow or unrepresentable view bounds unavailable', () => {
    for (const state of [
      world(plane('OVERFLOW', 1, 0, Number.MAX_VALUE, 0)),
      world(plane('UNRESOLVED', 1e308, 1e308)),
    ]) {
      const admitted = parseWorldState(state);
      expect(fitRadar(admitted, policy)).toBeNull();
      expect(radarRangeLabel(admitted, policy)).toBe('RADAR VIEW UNAVAILABLE');
      expect(admitted).toEqual(state);
    }
  });

  it('keeps the existing parser rejection of nonfinite inputs', () => {
    for (const value of [Infinity, -Infinity, NaN]) {
      const state = world(plane('BAD', value, 0));
      expect(() => parseWorldState(state)).toThrow('must be a finite number');
      expect(fitRadar(state, policy)).toBeNull();
    }
  });

  it('rejects invalid projection horizons and unusable canvas dimensions without a scale', () => {
    for (const horizon_min of [Infinity, NaN, -1]) expect(fitRadar(world(plane('A', 0, 0)), { ...policy, horizon_min })).toBeNull();
    const frame = fitRadar(world(plane('A', 0, 0)), policy)!;
    for (const [width, height] of [[0, 300], [-1, 300], [300, 0], [Infinity, 300]]) {
      expect(radarViewport(frame, width!, height!)).toBeNull();
    }
  });

  it('does not mutate frozen world or policy while fitting, projecting and generating ticks', () => {
    const state = world(plane('A', -2, 1, 2, -1), plane('B', 3, -2, -1, 2));
    state.aircraft.forEach(Object.freeze); Object.freeze(state.aircraft); Object.freeze(state);
    const frozenPolicy = Object.freeze({ ...policy }), before = JSON.stringify({ state, policy: frozenPolicy });
    const view = radarViewport(fitRadar(state, frozenPolicy)!, 708, 536)!;
    radarPoint(view, -2, 1); radarTicks(view.min_x_nm, view.max_x_nm, 10);
    expect(JSON.stringify({ state, policy: frozenPolicy })).toBe(before);
    expect(radarRangeLabel(state, frozenPolicy)).toBe('AUTO FIT +/- 15 NM');
  });
});
