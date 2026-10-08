// Exact TypeScript modules; controlled DOM/events/RAF, not a browser or Pyodide run.
// Node 24: node --experimental-vm-modules playback-baseline.mjs [airspace-root]
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash, webcrypto } from 'node:crypto';
import { stripTypeScriptTypes } from 'node:module';
import vm from 'node:vm';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(process.argv[2] || resolve(here, '../../../web/airspace'));
const output = process.argv[3] || resolve(process.cwd(), 'playback-result.json');
const copy = value => JSON.parse(JSON.stringify(value));
const sha256 = value => createHash('sha256').update(value).digest('hex');
const files = ['src/main.ts', 'src/core.ts', 'src/world-tools.ts', 'src/audit.ts', 'tests/python-reference.json', 'index.html'];
const before = Object.fromEntries(files.map(path => [path, sha256(readFileSync(resolve(root, path)))]));
const reference = JSON.parse(readFileSync(resolve(root, 'tests/python-reference.json'), 'utf8'));

class Element {
  constructor(tag = 'div', attributes = '') {
    this.tagName = tag.toUpperCase(); this.children = []; this.listeners = new Map();
    this.textContent = ''; this.className = ''; this.disabled = false; this.hidden = false;
    this.readOnly = false; this.value = ''; this.attributes = new Map();
    for (const match of attributes.matchAll(/([\w-]+)(?:="([^"]*)")?/g)) this.attributes.set(match[1], match[2] ?? '');
    this.id = this.attributes.get('id') || '';
    this.value = this.attributes.get('value') || '';
    this.disabled = this.attributes.has('disabled'); this.hidden = this.attributes.has('hidden');
  }
  get valueAsNumber() { return this.value.trim() === '' ? NaN : Number(this.value); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = [...nodes]; }
  querySelector(selector) { return selector === 'i' ? (this.icon ||= new Element('i')) : null; }
  toggleAttribute(name, force) { const value = force ?? !this.attributes.has(name); if (value) this.attributes.set(name, ''); else this.attributes.delete(name); if (name === 'disabled') this.disabled = value; return value; }
  addEventListener(kind, handler) { this.listeners.set(kind, [...(this.listeners.get(kind) || []), handler]); }
  focus() { this.document.activeElement = this; }
}

async function makePage() {
  const html = readFileSync(resolve(root, 'index.html'), 'utf8');
  const elements = new Map();
  const document = { activeElement: null, getElementById(id) { if (!elements.has(id)) throw new Error(`Unknown native element ${id}`); return elements.get(id); }, createElement(tag) { const node = new Element(tag); node.document = document; return node; } };
  for (const match of html.matchAll(/<([a-z][\w-]*)\b([^>]*\bid="[^"]+"[^>]*)>([^<]*)/gi)) {
    const node = new Element(match[1], match[2]); node.document = document; node.textContent = match[3]; elements.set(node.id, node);
  }
  const frames = []; const draws = []; const pythonCalls = []; const unexpected = [];
  const context = vm.createContext({ document, window: { addEventListener() {} }, requestAnimationFrame(callback) { frames.push(callback); return frames.length; }, console, crypto: webcrypto, TextEncoder });
  const moduleCache = new Map();
  function synthetic(name, values) {
    return new vm.SyntheticModule(Object.keys(values), function () { for (const [key, value] of Object.entries(values)) this.setExport(key, value); }, { context, identifier: name });
  }
  const typeExports = { './core': ['Aircraft', 'WorldState', 'SafetyPolicy'], './audit': ['AuditEvent'] };
  async function sourceModule(specifier) {
    if (moduleCache.has(specifier)) return moduleCache.get(specifier);
    const pending = (async () => {
    const source = readFileSync(resolve(root, `src/${specifier.slice(2)}.ts`), 'utf8');
    // Node erases types but preserves imports. Facades below supply undefined only
    // for erased interfaces; every runtime export comes from the exact module.
    const native = new vm.SourceTextModule(stripTypeScriptTypes(source, { mode: 'strip' }), { context, identifier: `${specifier}.ts` });
    await native.link(linker); await native.evaluate();
    if (!typeExports[specifier]) return native;
    const values = Object.fromEntries(Object.getOwnPropertyNames(native.namespace).map(key => [key, native.namespace[key]]));
    for (const name of typeExports[specifier]) values[name] = undefined;
    const facade = synthetic(`${specifier}:erased-type-import-facade`, values); await facade.link(linker); await facade.evaluate();
    return facade;
    })();
    moduleCache.set(specifier, pending); return pending;
  }
  function unused(name) { return () => { unexpected.push(name); throw new Error(`Unexercised boundary called: ${name}`); }; }
  async function linker(specifier) {
    if (['./core', './world-tools', './audit'].includes(specifier)) return sourceModule(specifier);
    if (moduleCache.has(specifier)) return moduleCache.get(specifier);
    let values;
    if (specifier === '../style.css') values = {};
    else if (specifier === '../tests/python-reference.json') values = { default: copy(reference) };
    else if (specifier === './track-edit') values = { TrackEditInput: undefined, TrackEditPreview: undefined, TrackEditSession: undefined, applyTrackEdit: unused('applyTrackEdit'), beginTrackEdit: unused('beginTrackEdit'), previewTrackEdit: unused('previewTrackEdit') };
    else if (specifier === './planner') values = { Advisory: undefined };
    else if (specifier === './python') values = { towerPython: async request => { pythonCalls.push(copy(request)); throw new Error('Controlled Python unavailable response'); } };
    else if (specifier === './gate') values = { Ack: undefined, Approval: undefined, GateRejected: class GateRejected extends Error {} };
    else if (specifier === './draw') values = { drawAirspace(_canvas, state, selected, policy) { draws.push(copy({ state, selected, policy })); }, viewRange: () => 12 };
    else throw new Error(`Unexpected import ${specifier}`);
    const result = synthetic(specifier, values); moduleCache.set(specifier, result); return result;
  }
  const main = new vm.SourceTextModule(stripTypeScriptTypes(readFileSync(resolve(root, 'src/main.ts'), 'utf8'), { mode: 'strip' }), { context, identifier: 'exact-main.ts' });
  await main.link(linker); await main.evaluate();
  const settle = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
  await settle();
  const node = id => document.getElementById(id);
  const dispatch = async (id, kind = 'click') => {
    const target = node(id);
    if (target.disabled) throw new Error(`Native disabled control ${id}`);
    for (const handler of target.listeners.get(kind) || []) await handler({ currentTarget: target, target });
    await settle();
  };
  const tick = async time => { assert.equal(frames.length, 1, 'one native RAF chain'); frames.shift()(time); await settle(); };
  const snapshot = () => ({ state: copy(draws.at(-1).state), rateLabel: node('speed-value').textContent, slider: node('speed-range').value, runLabel: node('toggle-run').textContent, clock: node('sim-clock').textContent });
  return { node, dispatch, tick, snapshot, pythonCalls, unexpected, async rate(value) { node('speed-range').value = String(value); await dispatch('speed-range', 'input'); }, async advance(start = 1000) { await tick(start); await tick(start + 80); } };
}

const cases = [];
async function check(name, fn) {
  let observation;
  try { observation = await fn(); cases.push({ name, pass: true, observation }); }
  catch (error) { cases.push({ name, pass: false, error: String(error), observation: error.observation }); }
}
function verify(condition, message, observation) { if (!condition) { const error = new Error(message); error.observation = observation; throw error; } }
const near = (left, right) => Math.abs(left - right) < 1e-9;

await check('fresh_run_advances_at_native_default_rate', async () => {
  const page = await makePage(); const initial = page.snapshot();
  await page.dispatch('toggle-run'); await page.advance(); const after = page.snapshot();
  const deltaSeconds = after.state.observed_at - reference.scenarios[0].now;
  const deltaNm = after.state.aircraft[0].x_nm - initial.state.aircraft[0].x_nm;
  const observation = { initial, after, deltaSeconds, deltaNm };
  verify(near(deltaSeconds, 4.8) && near(deltaNm, 0.08) && after.runLabel === 'Pause traffic', 'native 80ms frame must advance at default rate', observation);
  return observation;
});
await check('reset_restores_slider_label_and_actual_default_rate', async () => {
  const page = await makePage(); await page.rate(3); await page.dispatch('toggle-run'); await page.advance(); const beforeReset = page.snapshot();
  await page.dispatch('reset-world'); const reset = page.snapshot(); await page.dispatch('toggle-run'); await page.advance(2000); const after = page.snapshot();
  const deltaSeconds = after.state.observed_at - reference.scenarios[0].now;
  const deltaNm = after.state.aircraft[0].x_nm - reference.scenarios[0].state.aircraft[0].x_nm;
  const observation = { beforeReset, reset, after, deltaSeconds, deltaNm };
  verify(reset.slider === '1' && reset.rateLabel === '1.0x' && reset.runLabel === 'Run traffic' && near(deltaSeconds, 4.8) && near(deltaNm, 0.08), 'reset must restore engine rate, label and slider together', observation);
  return observation;
});
for (const id of ['add-traffic', 'perturb-track', 'policy-horizontal', 'add-custom-flight', 'remove-selected', 'load-world']) {
  await check(`automatic_pause_${id}`, async () => {
    const page = await makePage(); await page.rate(2); await page.dispatch('toggle-run'); await page.advance();
    if (id === 'policy-horizontal') page.node(id).value = '6';
    if (id === 'load-world') page.node('world-json').value = JSON.stringify(reference.scenarios[0].state);
    await page.dispatch(id, id.startsWith('policy-') ? 'input' : 'click'); const paused = page.snapshot();
    await page.tick(1160); await page.tick(1240); const held = page.snapshot();
    const observation = { paused, held, unexpected: page.unexpected };
    verify(paused.runLabel === 'Run traffic' && JSON.stringify(paused.state) === JSON.stringify(held.state) && paused.rateLabel === '2.0x' && page.unexpected.length === 0, 'automatic pause must expose Run traffic and hold the world', observation);
    return observation;
  });
}
await check('failed_flight_validation_still_displays_actual_paused_state', async () => {
  const page = await makePage(); await page.dispatch('toggle-run'); await page.advance(); page.node('flight-speed').value = '';
  await page.dispatch('add-custom-flight'); const paused = page.snapshot(); await page.tick(1160); const held = page.snapshot();
  const observation = { paused, held, feedback: page.node('builder-feedback').textContent };
  verify(paused.runLabel === 'Run traffic' && JSON.stringify(paused.state) === JSON.stringify(held.state) && observation.feedback.startsWith('NOT ADDED:'), 'validation refusal must not leave a stale Pause traffic button', observation);
  return observation;
});
await check('manual_pause_resume_preserves_selected_rate_and_ignores_paused_gap', async () => {
  const page = await makePage(); await page.rate(0.5); await page.dispatch('toggle-run'); await page.advance();
  await page.dispatch('toggle-run'); const paused = page.snapshot(); await page.tick(10000); const held = page.snapshot();
  await page.dispatch('toggle-run'); await page.advance(20000); const resumed = page.snapshot();
  const deltaSeconds = resumed.state.observed_at - held.state.observed_at;
  const observation = { paused, held, resumed, deltaSeconds };
  verify(paused.runLabel === 'Run traffic' && JSON.stringify(paused.state) === JSON.stringify(held.state) && near(deltaSeconds, 2.4) && resumed.rateLabel === '0.5x' && resumed.runLabel === 'Pause traffic', 'manual pause/resume must preserve rate without consuming paused time', observation);
  return observation;
});
const after = Object.fromEntries(files.map(path => [path, sha256(readFileSync(resolve(root, path)))]));
assert.deepEqual(after, before, 'source bytes stay unchanged during replay');
const result = { schema: 'towerops.playback.controlled-replay.v1', nativeRoot: root, runtime: process.version, command: 'node --experimental-vm-modules playback-baseline.mjs [airspace-root] [result-json]', qualification: 'Exact main/core/world-tools/audit and reference JSON, Node type erasure, controlled DOM/events/RAF. No real browser, Canvas rendering, Pyodide, build or deployment.', sourceBefore: before, sourceAfter: after, passed: cases.filter(item => item.pass).length, failed: cases.filter(item => !item.pass).length, cases };
writeFileSync(output, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ result: output, passed: result.passed, failed: result.failed, cases: cases.map(({ name, pass, error }) => ({ name, pass, error })) }, null, 2));
process.exitCode = result.failed ? 1 : 0;
