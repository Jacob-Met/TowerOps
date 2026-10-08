import html from '../index.html?raw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { WorldState } from '../src/core';
import reference from './python-reference.json';

// Exercise the page's actual event handlers and RAF integration. Only drawing
// and the asynchronous Python boundary are mocked; no browser DOM is required.
const { draw, python } = vi.hoisted(() => ({ draw: vi.fn(), python: vi.fn() }));
vi.mock('../src/draw', async (importOriginal) => ({
  ...await importOriginal<typeof import('../src/draw')>(),
  drawAirspace: draw,
}));
vi.mock('../src/python', () => ({ towerPython: python }));
// The retained fixture deliberately has no native DOM. Keep register drawing
// outside these playback/worker assertions; its real DOM is received in Chromium.
vi.mock('../src/flight-register', () => ({ createFlightRegister: () => ({ update: vi.fn() }) }));

type Listener = (event: { currentTarget: ElementStub; target: ElementStub }) => unknown;
class ElementStub {
  id = ''; value = ''; textContent = ''; className = '';
  disabled = false; hidden = false; readOnly = false;
  children: unknown[] = [];
  attributes = new Map<string, string>();
  get options() { return this.children as ElementStub[]; }
  setAttribute(name: string, value: string) { this.attributes.set(name, value); }
  listeners = new Map<string, Listener[]>();
  icon: ElementStub | null = null;
  get valueAsNumber() { return this.value.trim() === '' ? NaN : Number(this.value); }
  append(...nodes: unknown[]) { this.children.push(...nodes); }
  replaceChildren(...nodes: unknown[]) { this.children = nodes; }
  querySelector(selector: string) { return selector === 'i' ? (this.icon ??= new ElementStub()) : selector.startsWith('#') ? node(selector.slice(1)) : null; }
  toggleAttribute(name: string, value: boolean) { if (name === 'disabled') this.disabled = value; return value; }
  addEventListener(kind: string, listener: Listener) { this.listeners.set(kind, [...(this.listeners.get(kind) ?? []), listener]); }
}

const fixture = reference.scenarios[0]!;
function drainTasks(): Promise<void> {
  return new Promise<void>(resolve => globalThis.setTimeout(resolve, 0));
}
let elements: Map<string, ElementStub>;
let frames: FrameRequestCallback[];
const node = (id: string) => {
  const value = elements.get(id);
  if (!value) throw new Error(`Missing native page control: ${id}`);
  return value;
};
async function dispatch(id: string, kind = 'click') {
  const element = node(id);
  expect(element.disabled, `${id} must be an enabled native control`).toBe(false);
  for (const listener of element.listeners.get(kind) ?? []) await listener({ currentTarget: element, target: element });
  await drainTasks();
}
async function tick(time: number) {
  expect(frames).toHaveLength(1);
  frames.shift()!(time);
  await drainTasks();
}
async function advance(start = 1000) { await tick(start); await tick(start + 80); }
async function setRate(value: number) { node('speed-range').value = String(value); await dispatch('speed-range', 'input'); }
function world(): WorldState {
  const last = draw.mock.calls.at(-1);
  if (!last) throw new Error('Page did not draw a world');
  return JSON.parse(JSON.stringify(last[1])) as WorldState;
}

beforeEach(async () => {
  vi.resetModules(); draw.mockReset(); python.mockReset();
  elements = new Map(); frames = [];
  for (const match of html.matchAll(/<[a-z][\w-]*\b([^>]*\bid="[^"]+"[^>]*)>([^<]*)/gi)) {
    const attributes = new Map([...match[1]!.matchAll(/([\w-]+)(?:="([^"]*)")?/g)].map(item => [item[1]!, item[2] ?? '']));
    const element = new ElementStub();
    element.id = attributes.get('id')!; element.value = attributes.get('value') ?? '';
    element.textContent = match[2]!; element.disabled = attributes.has('disabled');
    elements.set(element.id, element);
  }
  vi.stubGlobal('document', { activeElement: null, getElementById: node, createElement: () => new ElementStub(), createElementNS: () => new ElementStub() });
  vi.stubGlobal('window', { addEventListener: vi.fn() });
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => frames.push(callback));
  await import('../src/main');
  await drainTasks();
});
afterEach(() => { vi.unstubAllGlobals(); });

describe('traffic playback controls', () => {
  it('starts at the displayed default rate', async () => {
    await dispatch('toggle-run'); await advance();
    expect(node('toggle-run').textContent).toBe('Pause traffic');
    expect(world().observed_at - fixture.now).toBeCloseTo(4.8, 9);
    expect(world().aircraft[0]!.x_nm - fixture.state.aircraft[0]!.x_nm).toBeCloseTo(0.08, 9);
  });

  it.each([0.5, 3])('Reset restores the default engine rate after %sx playback', async rate => {
    await setRate(rate); await dispatch('toggle-run'); await advance();
    await dispatch('reset-world');
    expect(world()).toEqual(fixture.state);
    expect(node('speed-range').value).toBe('1');
    expect(node('speed-value').textContent).toBe('1.0x');
    expect(node('toggle-run').textContent).toBe('Run traffic');
    await tick(1160); expect(world()).toEqual(fixture.state);
    await dispatch('toggle-run'); await advance(2000);
    expect(world().observed_at - fixture.now).toBeCloseTo(4.8, 9);
    expect(world().aircraft[0]!.x_nm - fixture.state.aircraft[0]!.x_nm).toBeCloseTo(0.08, 9);
  });

  it.each(['add-traffic', 'perturb-track', 'policy-horizontal', 'add-custom-flight', 'remove-selected', 'load-world'])(
    '%s pauses playback and displays the action that resumes it', async id => {
      await setRate(2); await dispatch('toggle-run'); await advance();
      if (id === 'policy-horizontal') node(id).value = '6';
      if (id === 'load-world') node('world-json').value = JSON.stringify(fixture.state);
      await dispatch(id, id.startsWith('policy-') ? 'input' : 'click');
      const paused = world();
      expect(node('toggle-run').textContent).toBe('Run traffic');
      expect(node('speed-value').textContent).toBe('2.0x');
      await tick(1160); await tick(1240); expect(world()).toEqual(paused);
      await dispatch('toggle-run'); await advance(2000);
      // A loaded fixture's recorded timestamp precedes its displayed clock by
      // two seconds. Measure from the clock selected by the existing load path.
      expect(world().observed_at - paused.observed_at).toBeCloseTo(9.6, 9);
      expect(node('toggle-run').textContent).toBe('Pause traffic');
    },
  );

  it('displays the existing pause when custom-flight validation returns early', async () => {
    await dispatch('toggle-run'); await advance(); node('flight-speed').value = '';
    const before = world(); await dispatch('add-custom-flight');
    expect(node('builder-feedback').textContent).toMatch(/^NOT ADDED:/);
    expect(node('toggle-run').textContent).toBe('Run traffic');
    expect(node('encounter-first').disabled).toBe(false);
    expect(node('encounter-content').hidden).toBe(false);
    await tick(1160); expect(world()).toEqual(before);
  });

  it('displays the existing pause when removal must retain the last aircraft', async () => {
    await dispatch('remove-selected');
    await dispatch('toggle-run'); await advance(); const before = world();
    await dispatch('remove-selected');
    expect(node('builder-feedback').textContent).toBe('Keep at least one aircraft in the world.');
    expect(node('toggle-run').textContent).toBe('Run traffic');
    expect(node('encounter-message').textContent).toBe('Add a second flight to compare an encounter.');
    await tick(1160); expect(world()).toEqual(before);
  });

  it('keeps playback running when WorldState validation fails before the pause point', async () => {
    await dispatch('toggle-run'); await advance(); const before = world();
    node('world-json').value = '{'; await dispatch('load-world');
    expect(node('world-json-feedback').textContent).toMatch(/^NOT LOADED:/);
    expect(node('toggle-run').textContent).toBe('Pause traffic');
    await tick(1160);
    expect(world().observed_at - before.observed_at).toBeCloseTo(4.8, 9);
  });

  it('updates the pause label before the planner promise settles', async () => {
    let rejectPlan!: (error: Error) => void;
    python.mockImplementation(() => new Promise((_resolve, reject) => { rejectPlan = reject; }));
    await dispatch('toggle-run'); await advance(); const before = world();
    await dispatch('run-planner');
    expect(python).toHaveBeenCalledOnce();
    expect(node('toggle-run').disabled).toBe(true);
    expect(node('toggle-run').textContent).toBe('Run traffic');
    await tick(1160); expect(world()).toEqual(before);
    rejectPlan(new Error('Controlled unavailable planner')); await drainTasks();
    expect(node('toggle-run').disabled).toBe(false);
    expect(node('toggle-run').textContent).toBe('Run traffic');
    expect(world()).toEqual(before);
  });

  it('retains the chosen rate through manual pause and resume', async () => {
    await setRate(0.5); await dispatch('toggle-run'); await advance();
    await dispatch('toggle-run'); const before = world();
    expect(node('toggle-run').textContent).toBe('Run traffic');
    await tick(10000); expect(world()).toEqual(before);
    await dispatch('toggle-run'); await advance(20000);
    expect(world().observed_at - before.observed_at).toBeCloseTo(2.4, 9);
    expect(node('speed-value').textContent).toBe('0.5x');
  });
});
