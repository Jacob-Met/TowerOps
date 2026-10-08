import { describe, expect, it } from 'vitest';
import { Aircraft, DEFAULT_POLICY, WorldState, projected } from '../src/core';
import { RadarFrame, fitRadar, radarPoint, radarViewport } from '../src/radar-geometry';
import {
  MIN_RADAR_HALF_RANGE_NM, RadarMove, RadarViewControls, clipRadarSegment,
  insideRadarClip, moveRadarFrame, radarViewCanProject, radarViewSummary,
} from '../src/radar-view';

const plane = (id: string, x: number, y: number, vx = 0, vy = 0): Aircraft => ({
  aircraft_id: id, x_nm: x, y_nm: y, altitude_ft: 10000,
  vx_nm_min: vx, vy_nm_min: vy, climb_ft_min: 0,
});
const world = (...aircraft: Aircraft[]): WorldState => ({ version: 17, observed_at: 1000, aircraft });
const policy = Object.freeze({ ...DEFAULT_POLICY });
const origin = Object.freeze({ center_x_nm: 0, center_y_nm: 0, half_range_nm: 15 });
const broad = world(plane('LOCAL_A', 0, 0), plane('LOCAL_B', 1, 0), plane('DISTANT', 10000, 10000));

describe('manual radar framing', () => {
  it('makes a local one-NM pair readable in a wide world without redefining automatic fit', () => {
    const original = JSON.stringify(broad), automatic = fitRadar(broad, policy)!;
    for (const [width, height] of [[650, 456], [176, 256]]) {
      const before = radarViewport(automatic, width!, height!)!;
      const focused = moveRadarFrame(automatic, 'focus', broad.aircraft[0], width!, height!)!;
      const close = moveRadarFrame(focused, 'zoom-in', undefined, width!, height!)!;
      const after = radarViewport(close, width!, height!)!;
      expect(radarPoint(before, 1, 0)[0] - radarPoint(before, 0, 0)[0]).toBeLessThan(1);
      expect(radarPoint(after, 1, 0)[0] - radarPoint(after, 0, 0)[0]).toBeGreaterThan(10);
      expect(radarPoint(after, 0, 0)).toEqual([width! / 2, height! / 2]);
      expect(radarPoint(after, 0, 1)[1] - radarPoint(after, 0, 0)[1])
        .toBeCloseTo(-(radarPoint(after, 1, 0)[0] - radarPoint(after, 0, 0)[0]), 10);
    }
    expect(fitRadar(broad, policy)).toEqual(automatic);
    expect(JSON.stringify(broad)).toBe(original);
  });

  it('pans the center in world directions and reverses a pan without moving the track', () => {
    const before = radarViewport(origin, 600, 300)!;
    const deltas: Array<[RadarMove, RadarMove, number, number]> = [
      ['pan-east', 'pan-west', -75, 0], ['pan-west', 'pan-east', 75, 0],
      ['pan-north', 'pan-south', 0, 75], ['pan-south', 'pan-north', 0, -75],
    ];
    for (const [action, reverse, dx, dy] of deltas) {
      const moved = moveRadarFrame(origin, action, undefined, 600, 300)!;
      const point = radarPoint(radarViewport(moved, 600, 300)!, 0, 0);
      expect(point).toEqual([radarPoint(before, 0, 0)[0] + dx, radarPoint(before, 0, 0)[1] + dy]);
      expect(moveRadarFrame(moved, reverse, undefined, 600, 300)).toEqual(origin);
    }
  });

  it('bounds zoom at one NM, preserves close focus and returns defensive new frames', () => {
    let frame: RadarFrame = origin;
    for (let i = 0; i < 5; i++) frame = moveRadarFrame(frame, 'zoom-in', undefined, 500, 300) ?? frame;
    expect(frame.half_range_nm).toBe(MIN_RADAR_HALF_RANGE_NM);
    expect(moveRadarFrame(frame, 'zoom-in', undefined, 500, 300)).toBeNull();
    expect(moveRadarFrame(frame, 'zoom-out', undefined, 500, 300)?.half_range_nm).toBe(2);
    const target = Object.freeze({ x_nm: 30, y_nm: -20 });
    expect(moveRadarFrame(frame, 'focus', target, 500, 300)).toEqual({
      center_x_nm: 30, center_y_nm: -20, half_range_nm: 1 });
  });

  it('refuses missing selection, nonfinite, overflowing and numerically unchanged frames', () => {
    expect(moveRadarFrame(origin, 'focus', undefined, 500, 300)).toBeNull();
    expect(moveRadarFrame(origin, 'focus', { x_nm: Infinity, y_nm: 0 }, 500, 300)).toBeNull();
    expect(moveRadarFrame(origin, 'focus', { x_nm: 1e308, y_nm: 0 }, 500, 300)).toBeNull();
    expect(moveRadarFrame(origin, 'pan-east', undefined, 0, 300)).toBeNull();
    expect(moveRadarFrame({ center_x_nm: 0, center_y_nm: 0, half_range_nm: 1e308 },
      'zoom-out', undefined, 300, 300)).toBeNull();
    const tooWide = world(plane('LEFT', -1e308, 0), plane('RIGHT', 1e308, 0));
    expect(radarViewCanProject(radarViewport(origin, 300, 300)!, tooWide, policy)).toBe(false);
    for (const a of broad.aircraft) Object.freeze(a);
    Object.freeze(broad.aircraft); Object.freeze(broad);
    expect(() => moveRadarFrame(Object.freeze(fitRadar(broad, policy)!), 'focus',
      broad.aircraft[0], 500, 300)).not.toThrow();
    expect(origin).toEqual({ center_x_nm: 0, center_y_nm: 0, half_range_nm: 15 });
  });

  it('counts position and projection ends against the actual rectangular plot', () => {
    const state = world(plane('CENTER', 0, 0, 10, 0), plane('SIDE', 20, 0), plane('OUT', 40, 0));
    const wide = radarViewport(origin, 600, 300)!;
    expect(radarViewSummary(wide, state, policy, 'OUT'))
      .toBe('2 of 3 aircraft positions in view. 1 outside; 2 projection ends outside. Selected OUT is outside this view.');
    const narrow = radarViewport(origin, 300, 600)!;
    expect(radarViewSummary(narrow, state, policy, 'CENTER'))
      .toBe('1 of 3 aircraft positions in view. 2 outside; 3 projection ends outside.');
    expect(radarViewSummary(wide, world(), policy, '')).toBe('0 of 0 aircraft positions in view. 0 outside; 0 projection ends outside.');
  });
});

describe('manual plot clipping', () => {
  const box = Object.freeze({ left: 0, top: 0, right: 100, bottom: 80 });
  it('retains trajectories that cross the view with both endpoints outside', () => {
    expect(clipRadarSegment([-500, 40], [500, 40], box)).toEqual([[0, 40], [100, 40]]);
    expect(clipRadarSegment([40, -500], [40, 500], box)).toEqual([[40, 0], [40, 80]]);
    const diagonal = clipRadarSegment([-100, -100], [100, 100], box)!;
    expect(diagonal[0][0]).toBeCloseTo(0, 10); expect(diagonal[0][1]).toBeCloseTo(0, 10);
    expect(diagonal[1][0]).toBeCloseTo(80, 10); expect(diagonal[1][1]).toBeCloseTo(80, 10);
    expect(clipRadarSegment([10, 20], [30, 40], box)).toEqual([[10, 20], [30, 40]]);
  });

  it('rejects absent and invalid paths and keeps returned endpoints inside finite bounds', () => {
    expect(clipRadarSegment([-10, 20], [-30, 40], box)).toBeNull();
    expect(clipRadarSegment([0, Infinity], [20, 30], box)).toBeNull();
    expect(clipRadarSegment([0, 0], [20, 30], { ...box, right: NaN })).toBeNull();
    for (const [a, b] of [
      [[-1e308, 40], [1e308, 40]], [[40, -1e308], [40, 1e308]],
      [[-10, 40], [110, 40]], [[110, 40], [-10, 40]],
    ] as const) {
      const line = clipRadarSegment(a, b, box)!;
      expect(line).not.toBeNull();
      expect(line.every(point => point.every(Number.isFinite) && insideRadarClip(point, box))).toBe(true);
    }
  });
});

class Element {
  textContent = ''; disabled = false;
  attributes = new Map<string, string>();
  listeners = new Map<string, Array<(event: any) => void>>();
  addEventListener(type: string, fn: (event: any) => void) {
    this.listeners.set(type, [...this.listeners.get(type) ?? [], fn]);
  }
  setAttribute(key: string, value: string) { this.attributes.set(key, value); }
  toggleAttribute(key: string, value: boolean) { if (key === 'disabled') this.disabled = value; return value; }
  dispatch(type: string, event: any = {}) { for (const fn of this.listeners.get(type) ?? []) fn(event); }
}
function controls() {
  const elements = new Map<string, Element>();
  const element = (id: string): Element => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id)!;
  };
  const input = { state: JSON.parse(JSON.stringify(broad)) as WorldState, policy: { ...policy }, selected: 'LOCAL_A' };
  let renders = 0;
  let camera: RadarViewControls;
  const redraw = () => {
    renders++;
    const automatic = fitRadar(input.state, input.policy);
    const view = automatic && radarViewport(camera.frame ?? automatic, 600, 300);
    camera.update(view && radarViewCanProject(view, input.state, input.policy) ? view : null);
  };
  camera = new RadarViewControls(id => element(id) as unknown as HTMLElement, () => input, redraw);
  redraw();
  return { input, element, camera, redraw, count: () => renders };
}

describe('radar control boundary', () => {
  it('starts automatic, changes only the redraw target, and restores current automatic fitting', () => {
    const h = controls(), input = JSON.stringify(h.input);
    expect(h.camera.frame).toBeUndefined();
    expect(h.element('range-label').textContent).toBe('AUTO FIT +/- 5500 NM');
    h.element('radar-focus').dispatch('click');
    expect(h.camera.frame).toEqual(origin);
    expect(h.element('radar-fit').attributes.get('aria-pressed')).toBe('false');
    const exposed = h.camera.frame!; exposed.center_x_nm = 999;
    expect(h.camera.frame!.center_x_nm).toBe(0);
    for (const id of ['zoom-in', 'zoom-out', 'pan-east', 'pan-west', 'pan-north', 'pan-south'])
      h.element('radar-' + id).dispatch('click');
    expect(JSON.stringify(h.input)).toBe(input);
    expect(h.count()).toBe(8);
    h.input.state = world(plane('NEW', 100, -100)); h.input.selected = 'NEW'; h.redraw();
    expect(h.camera.frame).toEqual(origin);
    expect(h.element('radar-view-summary').textContent).toContain('Selected NEW is outside');
    h.element('radar-fit').dispatch('click');
    expect(h.camera.frame).toBeUndefined();
    expect(h.element('radar-center-label').textContent).toBe('CENTER EAST 100 / NORTH -100 NM');
    expect(h.element('radar-fit').attributes.get('aria-pressed')).toBe('true');
  });

  it('routes scoped keys through the same controls and leaves modified keys alone', () => {
    const h = controls();
    let prevented = 0;
    h.element('airspace').dispatch('keydown', { key: 'f', preventDefault: () => prevented++ });
    expect(h.camera.frame).toEqual(origin);
    h.element('airspace').dispatch('keydown', { key: 'ArrowRight', preventDefault: () => prevented++ });
    expect(h.camera.frame!.center_x_nm).toBe(7.5);
    h.element('airspace').dispatch('keydown', { key: '+', ctrlKey: true, preventDefault: () => prevented++ });
    expect(h.camera.frame!.half_range_nm).toBe(15);
    expect(prevented).toBe(2);
    expect(h.element('world-json').listeners.size).toBe(0);
    h.element('airspace').dispatch('keydown', { key: 'Home', preventDefault: () => prevented++ });
    expect(h.camera.frame).toBeUndefined();
    expect(h.element('radar-view-status').textContent).toMatch(/^Automatic fit restored/);
  });

  it('disables exhausted or unrepresentable changes without losing the route back to automatic', () => {
    const h = controls();
    h.element('radar-focus').dispatch('click');
    for (let i = 0; i < 8; i++) h.element('radar-zoom-in').dispatch('click');
    expect(h.camera.frame!.half_range_nm).toBe(1);
    expect(h.element('radar-zoom-in').disabled).toBe(true);
    h.input.state = world(plane('BAD_PROJECTION', 0, 0, Number.MAX_VALUE)); h.redraw();
    expect(h.element('range-label').textContent).toBe('RADAR VIEW UNAVAILABLE');
    expect(h.element('radar-pan-east').disabled).toBe(true);
    expect(h.element('radar-fit').disabled).toBe(false);
    h.element('radar-fit').dispatch('click');
    expect(h.camera.frame).toBeUndefined();
    expect(h.element('range-label').textContent).toBe('RADAR VIEW UNAVAILABLE');
    expect(projected(h.input.state.aircraft[0]!, policy.horizon_min).x_nm).toBe(Infinity);
  });
});
