import { Interval, SafetyPolicy, WorldState } from './core';
import { Encounter, SeparationPoint, analyzeEncounter, separationAt } from './encounter';

const NS = 'http://www.w3.org/2000/svg';
type Metric = 'horizontal_nm' | 'vertical_ft';
function svgNode<K extends keyof SVGElementTagNameMap>(tag: K, attributes: Record<string, string | number>, text?: string): SVGElementTagNameMap[K] {
  const element = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  if (text !== undefined) element.textContent = text;
  return element;
}
function intervalText(interval: Interval | null): string {
  return interval ? `${(interval[0] * 60).toFixed(1)}–${(interval[1] * 60).toFixed(1)} sec` : 'None in this window';
}
function plot(svg: SVGSVGElement, encounter: Encounter, point: SeparationPoint, metric: Metric, minimum: number): void {
  const width = 320, left = 42, right = 10, top = 16, bottom = 132;
  const chartWidth = width - left - right, chartHeight = bottom - top;
  const maximum = Math.max(minimum * 1.35, ...encounter.samples.map(sample => sample[metric] * 1.1));
  if (!Number.isFinite(maximum)) throw new Error('Separation exceeds the chart range.');
  const x = (minutes: number) => left + minutes / encounter.horizon_min * chartWidth;
  const y = (value: number) => bottom - value / maximum * chartHeight;
  const unit = metric === 'horizontal_nm' ? 'NM' : 'FT';
  svg.replaceChildren();
  svg.append(svgNode('title', {}, `${encounter.aircraft_a} and ${encounter.aircraft_b}: ${metric === 'horizontal_nm' ? 'horizontal' : 'vertical'} separation over ${encounter.horizon_min} minutes. Numeric values and intervals follow the chart.`));
  if (encounter.overlap) {
    svg.append(svgNode('rect', { x: x(encounter.overlap[0]), y: top, width: x(encounter.overlap[1]) - x(encounter.overlap[0]), height: chartHeight, class: 'encounter-band' }));
  }
  for (const fraction of [0, 0.5, 1]) {
    const value = maximum * fraction, py = y(value);
    svg.append(svgNode('line', { x1: left, y1: py, x2: width - right, y2: py, class: 'encounter-grid' }));
    svg.append(svgNode('text', { x: left - 6, y: py + 4, 'text-anchor': 'end', class: 'encounter-axis' }, value === 0 ? '0' : value >= 10000 || value < 0.01 ? value.toExponential(1) : String(Number(value.toPrecision(3)))));
    const minutes = encounter.horizon_min * fraction;
    svg.append(svgNode('text', { x: x(minutes), y: bottom + 19, 'text-anchor': fraction === 1 ? 'end' : 'middle', class: 'encounter-axis' }, minutes.toFixed(1)));
  }
  svg.append(svgNode('line', { x1: left, y1: y(minimum), x2: width - right, y2: y(minimum), class: 'encounter-minimum' }));
  svg.append(svgNode('text', { x: width - right - 3, y: y(minimum) - 5, 'text-anchor': 'end', class: 'encounter-threshold-label' }, `MIN ${minimum} ${unit}`));
  svg.append(svgNode('polyline', { points: encounter.samples.map(sample => `${x(sample.minutes)},${y(sample[metric])}`).join(' '), class: 'encounter-curve' }));
  svg.append(svgNode('line', { x1: x(point.minutes), y1: top, x2: x(point.minutes), y2: bottom, class: 'encounter-cursor' }));
  svg.append(svgNode('circle', { cx: x(point.minutes), cy: y(point[metric]), r: 4, class: 'encounter-point' }));
}

/** Read-only view: event handlers update only this panel's pair and forecast cursor. */
export function createEncounterExplorer(root: HTMLElement) {
  const get = <T extends Element>(selector: string) => root.querySelector<T>(selector)!;
  const first = get<HTMLSelectElement>('#encounter-first'), second = get<HTMLSelectElement>('#encounter-second');
  const cursor = get<HTMLInputElement>('#encounter-time');
  const midpoint = get<HTMLButtonElement>('#encounter-midpoint'), closest = get<HTMLButtonElement>('#encounter-closest');
  const zero = get<HTMLButtonElement>('#encounter-now');
  const contents = get<HTMLElement>('#encounter-content'), message = get<HTMLElement>('#encounter-message');
  let latest: { state: WorldState; policy: SafetyPolicy; running: boolean } | null = null;
  let minutes = 0;
  let current: Encounter | null = null;
  function options(select: HTMLSelectElement, ids: string[], preferred: string) {
    if (Array.from(select.options).map(option => option.value).join('\0') !== ids.join('\0')) {
      select.replaceChildren(...ids.map(id => {
        const option = document.createElement('option'); option.value = id; option.textContent = id; return option;
      }));
    }
    select.value = ids.includes(preferred) ? preferred : ids[0] ?? '';
  }
  function refreshPair() {
    if (!latest) return;
    const ids = latest.state.aircraft.map(a => a.aircraft_id);
    options(first, ids, first.value);
    options(second, ids.filter(id => id !== first.value), second.value);
  }
  function setDisabled(disabled: boolean) {
    for (const control of [first, second, cursor, midpoint, closest, zero]) control.disabled = disabled;
  }
  function render() {
    current = null;
    if (!latest) return;
    const { state, policy, running } = latest;
    setDisabled(false);
    if (running || state.aircraft.length < 2) {
      setDisabled(true); contents.hidden = true;
      message.textContent = running ? 'Pause traffic to explore a stable forecast.' : 'Add a second flight to compare an encounter.';
      return;
    }
    try {
      current = analyzeEncounter(state, first.value, second.value, policy);
      minutes = Math.max(0, Math.min(minutes, policy.horizon_min));
      const point = separationAt(state, first.value, second.value, policy, minutes);
      cursor.max = String(policy.horizon_min * 60); cursor.value = String(minutes * 60);
      cursor.setAttribute('aria-valuetext', `${(minutes * 60).toFixed(1)} seconds ahead`);
      get<HTMLOutputElement>('#encounter-time-value').textContent = `+${(minutes * 60).toFixed(1)} SEC`;
      get<HTMLElement>('#encounter-source').textContent = `WORLD ${state.version} · CURRENT PAUSED TRAFFIC`;
      get<HTMLElement>('#encounter-horizontal-value').textContent = `${point.horizontal_nm.toFixed(2)} NM`;
      get<HTMLElement>('#encounter-vertical-value').textContent = `${point.vertical_ft.toFixed(1)} FT`;
      const verdict = get<HTMLElement>('#encounter-verdict');
      verdict.textContent = point.simultaneous ? 'Below both minimum separations at this time.' : 'At least one separation is at or above its minimum.';
      verdict.className = `encounter-verdict ${point.simultaneous ? 'intrusion' : 'clear'}`;
      get<HTMLElement>('#encounter-horizontal-window').textContent = intervalText(current.horizontal_window);
      get<HTMLElement>('#encounter-vertical-window').textContent = intervalText(current.vertical_window);
      get<HTMLElement>('#encounter-overlap-window').textContent = intervalText(current.overlap);
      midpoint.disabled = !current.overlap;
      plot(get<SVGSVGElement>('#encounter-horizontal-chart'), current, point, 'horizontal_nm', policy.min_horizontal_nm);
      plot(get<SVGSVGElement>('#encounter-vertical-chart'), current, point, 'vertical_ft', policy.min_vertical_ft);
      contents.hidden = false;
      message.textContent = `Forecasts hold both flights' current velocity and climb constant for ${policy.horizon_min.toFixed(1)} minutes. The live world, proposal and trace stay unchanged.`;
    } catch (error) {
      setDisabled(true); first.disabled = false; second.disabled = false; contents.hidden = true;
      message.textContent = `Forecast unavailable: ${error instanceof Error ? error.message : String(error)}`;
    }
  }
  function seek(next: number) { minutes = next; render(); }
  first.addEventListener('change', () => { refreshPair(); render(); });
  second.addEventListener('change', render);
  cursor.addEventListener('input', () => seek(cursor.valueAsNumber / 60));
  midpoint.addEventListener('click', () => { if (current?.overlap) seek((current.overlap[0] + current.overlap[1]) / 2); });
  closest.addEventListener('click', () => { if (current) seek(current.closest_horizontal_min); });
  zero.addEventListener('click', () => seek(0));
  return {
    update(state: WorldState, policy: SafetyPolicy, running: boolean): void {
      latest = { state, policy, running }; refreshPair(); render();
    },
  };
}
