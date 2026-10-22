import { Aircraft, SafetyPolicy, WorldState, projected } from './core';
import { RadarFrame, RadarViewport, fitRadar, radarNumber, radarPoint, radarViewport } from './radar-geometry';

export type RadarMove = 'zoom-in' | 'zoom-out' | 'pan-north' | 'pan-south' | 'pan-east' | 'pan-west' | 'focus';
type RadarAction = RadarMove | 'fit';
export const MIN_RADAR_HALF_RANGE_NM = 1;
const sameFrame = (a: RadarFrame, b: RadarFrame) =>
  a.center_x_nm === b.center_x_nm && a.center_y_nm === b.center_y_nm && a.half_range_nm === b.half_range_nm;

/** A camera change produces a new frame; it never receives mutable operational state. */
export function moveRadarFrame(
  current: RadarFrame, action: RadarMove, selected: Pick<Aircraft, 'x_nm' | 'y_nm'> | undefined,
  width: number, height: number,
): RadarFrame | null {
  if (!Object.values(current).every(Number.isFinite) || current.half_range_nm < MIN_RADAR_HALF_RANGE_NM ||
      !radarViewport(current, width, height)) return null;
  const next = { ...current }, step = current.half_range_nm / 2;
  switch (action) {
    case 'zoom-in': next.half_range_nm = Math.max(MIN_RADAR_HALF_RANGE_NM, current.half_range_nm / 2); break;
    case 'zoom-out': next.half_range_nm = current.half_range_nm * 2; break;
    case 'pan-north': next.center_y_nm += step; break;
    case 'pan-south': next.center_y_nm -= step; break;
    case 'pan-east': next.center_x_nm += step; break;
    case 'pan-west': next.center_x_nm -= step; break;
    case 'focus':
      if (!selected) return null;
      next.center_x_nm = selected.x_nm; next.center_y_nm = selected.y_nm;
      next.half_range_nm = Math.min(current.half_range_nm, 15);
      break;
  }
  if (!Object.values(next).every(Number.isFinite) || next.half_range_nm < MIN_RADAR_HALF_RANGE_NM ||
      !radarViewport(next, width, height) || sameFrame(current, next)) return null;
  return next;
}

/** Refuse a magnification where even the projected screen coordinates overflow. */
export function radarViewCanProject(view: RadarViewport, state: WorldState, policy: SafetyPolicy): boolean {
  return state.aircraft.every(a => [a, projected(a, policy.horizon_min)].every(p =>
    radarPoint(view, p.x_nm, p.y_nm).every(Number.isFinite)));
}

export interface RadarClip { left: number; top: number; right: number; bottom: number }
type Point = readonly [number, number];
export function insideRadarClip([x, y]: Point, box: RadarClip): boolean {
  return x >= box.left && x <= box.right && y >= box.top && y <= box.bottom;
}

/** Clip before giving Canvas a trajectory, including one with both ends outside. */
export function clipRadarSegment(first: Point, last: Point, box: RadarClip): readonly [Point, Point] | null {
  if (![...first, ...last, ...Object.values(box)].every(Number.isFinite) ||
      box.left >= box.right || box.top >= box.bottom) return null;
  const code = ([x, y]: Point) => (x < box.left ? 1 : x > box.right ? 2 : 0) |
    (y < box.top ? 4 : y > box.bottom ? 8 : 0);
  let a: Point = first, b: Point = last;
  for (let count = 0; count < 8; count++) {
    const ca = code(a), cb = code(b);
    if (!(ca | cb)) return [a, b];
    if (ca & cb) return null;
    const out = ca || cb;
    let point: Point;
    if (out & 12) {
      const y = out & 4 ? box.top : box.bottom;
      const t = (y / 2 - a[1] / 2) / (b[1] / 2 - a[1] / 2);
      point = [a[0] * (1 - t) + b[0] * t, y];
    } else {
      const x = out & 1 ? box.left : box.right;
      const t = (x / 2 - a[0] / 2) / (b[0] / 2 - a[0] / 2);
      point = [x, a[1] * (1 - t) + b[1] * t];
    }
    if (!point.every(Number.isFinite)) return null;
    if (out === ca) a = point; else b = point;
  }
  return null;
}

export function radarViewSummary(view: RadarViewport, state: WorldState, policy: SafetyPolicy, selected: string): string {
  const contains = (a: Pick<Aircraft, 'x_nm' | 'y_nm'>) =>
    a.x_nm >= view.min_x_nm && a.x_nm <= view.max_x_nm && a.y_nm >= view.min_y_nm && a.y_nm <= view.max_y_nm;
  const outside = state.aircraft.filter(a => !contains(a));
  const endpointsOutside = state.aircraft.filter(a => !contains(projected(a, policy.horizon_min))).length;
  return (state.aircraft.length - outside.length) + ' of ' + state.aircraft.length + ' aircraft positions in view. ' +
    outside.length + ' outside; ' + endpointsOutside + ' projection ends outside.' +
    (outside.some(a => a.aircraft_id === selected) ? ' Selected ' + selected + ' is outside this view.' : '');
}

interface RadarInput { state: WorldState; policy: SafetyPolicy; selected: string }
const moves: RadarMove[] = ['zoom-in', 'zoom-out', 'pan-north', 'pan-south', 'pan-east', 'pan-west', 'focus'];
const keyActions: Record<string, RadarAction> = {
  '+': 'zoom-in', '=': 'zoom-in', '-': 'zoom-out', '_': 'zoom-out',
  ArrowUp: 'pan-north', ArrowDown: 'pan-south', ArrowRight: 'pan-east', ArrowLeft: 'pan-west',
  Home: 'fit', f: 'focus', F: 'focus',
};

/** Session-local viewing state. The only callback redraws the radar and its controls. */
export class RadarViewControls {
  private manual: RadarFrame | null = null;
  private view: RadarViewport | null = null;
  private nodes: Record<string, HTMLElement>;
  constructor(
    element: (id: string) => HTMLElement,
    private readonly input: () => RadarInput,
    private readonly redraw: () => void,
  ) {
    const ids = [...moves.map(move => 'radar-' + move), 'radar-fit', 'range-label',
      'radar-center-label', 'radar-view-summary', 'radar-view-status'];
    this.nodes = Object.fromEntries(ids.map(id => [id, element(id)]));
    for (const action of [...moves, 'fit'] as RadarAction[])
      this.nodes['radar-' + action]!.addEventListener('click', () => this.change(action));
    element('airspace').addEventListener('keydown', event => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const action = Object.hasOwn(keyActions, event.key) ? keyActions[event.key] : undefined;
      if (!action) return;
      event.preventDefault(); this.change(action);
    });
  }

  get frame(): RadarFrame | undefined { return this.manual ? { ...this.manual } : undefined; }

  private text(id: string, value: string): void {
    const node = this.nodes[id]!;
    if (node.textContent !== value) node.textContent = value;
  }

  private candidate(action: RadarMove, input: RadarInput): RadarFrame | null {
    if (!this.view) return null;
    const automatic = fitRadar(input.state, input.policy);
    if (!automatic) return null;
    const next = moveRadarFrame(this.manual ?? automatic, action,
      input.state.aircraft.find(a => a.aircraft_id === input.selected), this.view.width, this.view.height);
    if (!next) return null;
    const view = radarViewport(next, this.view.width, this.view.height)!;
    return radarViewCanProject(view, input.state, input.policy) ? next : null;
  }

  update(view: RadarViewport | null): void {
    this.view = view;
    const input = this.input(), automatic = fitRadar(input.state, input.policy);
    const frame = this.manual ?? automatic;
    this.text('range-label', frame && (!this.manual || view)
      ? (this.manual ? 'MANUAL' : 'AUTO FIT') + ' +/- ' + radarNumber(frame.half_range_nm) + ' NM' : 'RADAR VIEW UNAVAILABLE');
    this.text('radar-center-label', frame
      ? 'CENTER EAST ' + radarNumber(frame.center_x_nm) + ' / NORTH ' + radarNumber(frame.center_y_nm) + ' NM' : 'CENTER UNAVAILABLE');
    this.text('radar-view-summary', view
      ? radarViewSummary(view, input.state, input.policy, input.selected)
      : 'Traffic cannot be shown at this size or coordinate scale. World check still includes all aircraft.');
    for (const action of moves)
      this.nodes['radar-' + action]!.toggleAttribute('disabled', !this.candidate(action, input));
    this.text('radar-focus', 'Focus ' + (input.selected || 'selected flight'));
    this.nodes['radar-fit']!.setAttribute('aria-pressed', String(!this.manual));
  }

  private change(action: RadarAction): void {
    if (action === 'fit') {
      this.manual = null; this.redraw();
      this.text('radar-view-status', 'Automatic fit restored. ' + this.nodes['radar-view-summary']!.textContent);
      return;
    }
    const next = this.candidate(action, this.input());
    if (!next) {
      this.text('radar-view-status', 'The view is unchanged: this control has reached its available position or range.');
      return;
    }
    this.manual = next; this.redraw();
    this.text('radar-view-status', this.nodes['range-label']!.textContent + '. ' +
      this.nodes['radar-center-label']!.textContent + '. ' + this.nodes['radar-view-summary']!.textContent);
  }
}
