import { DEFAULT_POLICY, SafetyPolicy, WorldState } from './core';
import { parseWorldState } from './world-tools';

export const SCENARIO_FORMAT = 'towerops.airspace-scenario';
export const MAX_SCENARIO_BYTES = 256 * 1024;

export interface ScenarioSnapshot {
  world: WorldState;
  policy: SafetyPolicy;
  now: number;
  time_scale: number;
  selected_aircraft_id: string;
}
export interface ScenarioFile extends ScenarioSnapshot {
  format: typeof SCENARIO_FORMAT;
  version: 1;
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be an object.`);
  }
  return value as Record<string, unknown>;
}
function exactKeys(value: Record<string, unknown>, keys: readonly string[], label: string): void {
  const actual = Object.keys(value);
  if (actual.length !== keys.length || actual.some(key => !keys.includes(key))) {
    throw new Error(`${label} needs exactly these fields: ${keys.join(', ')}.`);
  }
}
function finite(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`${label} must be a finite number.`);
  return value;
}
function controlValue(value: unknown, min: number, max: number, step: number, label: string): number {
  const number = finite(value, label);
  if (number < min || number > max || !Number.isInteger((number - min) / step)) {
    throw new Error(`${label} must be between ${min} and ${max}, in steps of ${step}.`);
  }
  return number;
}
function checkedWorld(value: unknown): WorldState {
  const world = record(value, 'world');
  exactKeys(world, ['version', 'observed_at', 'aircraft'], 'world');
  if (!Number.isSafeInteger(world.version) || (world.version as number) < 0) {
    throw new Error('world.version must be a non-negative safe integer.');
  }
  if (Array.isArray(world.aircraft)) {
    for (const [index, value] of world.aircraft.entries()) {
      exactKeys(record(value, `Aircraft ${index + 1}`),
        ['aircraft_id', 'x_nm', 'y_nm', 'altitude_ft', 'vx_nm_min', 'vy_nm_min', 'climb_ft_min'],
        `Aircraft ${index + 1}`);
    }
  }
  const parsed = parseWorldState(world);
  for (const [index, aircraft] of parsed.aircraft.entries()) {
    if (aircraft.aircraft_id !== (world.aircraft as Record<string, unknown>[])[index]!.aircraft_id) {
      throw new Error('Scenario callsigns must use uppercase letters, digits, _ or -.');
    }
  }
  return parsed;
}
function checkedPolicy(value: unknown): SafetyPolicy {
  const input = record(value, 'policy');
  exactKeys(input, Object.keys(DEFAULT_POLICY), 'policy');
  const policy: SafetyPolicy = {
    min_horizontal_nm: controlValue(input.min_horizontal_nm, 3, 10, 0.5, 'Horizontal separation (NM)'),
    min_vertical_ft: controlValue(input.min_vertical_ft, 500, 2500, 100, 'Vertical separation (FT)'),
    horizon_min: controlValue(input.horizon_min, 2, 10, 0.5, 'Look-ahead (MIN)'),
    sample_step_min: finite(input.sample_step_min, 'sample_step_min'),
    max_state_age_sec: finite(input.max_state_age_sec, 'max_state_age_sec'),
    max_speed_nm_min: finite(input.max_speed_nm_min, 'max_speed_nm_min'),
    max_climb_ft_min: finite(input.max_climb_ft_min, 'max_climb_ft_min'),
  };
  // These four parameters have no editor in this lab. Do not silently import
  // an invisible policy change which the current controls cannot reproduce.
  for (const key of ['sample_step_min', 'max_state_age_sec', 'max_speed_nm_min', 'max_climb_ft_min'] as const) {
    if (policy[key] !== DEFAULT_POLICY[key]) throw new Error(`${key} is not configurable in scenario format v1; expected ${DEFAULT_POLICY[key]}.`);
  }
  return policy;
}
export function createScenario(snapshot: ScenarioSnapshot): ScenarioFile {
  const world = checkedWorld(snapshot.world);
  const policy = checkedPolicy(snapshot.policy);
  const now = finite(snapshot.now, 'now');
  const time_scale = controlValue(snapshot.time_scale, 0.5, 3, 0.5, 'Time scale');
  const selected_aircraft_id = snapshot.selected_aircraft_id;
  if (typeof selected_aircraft_id !== 'string' || !world.aircraft.some(a => a.aircraft_id === selected_aircraft_id)) {
    throw new Error('selected_aircraft_id must identify an aircraft in this world.');
  }
  return { format: SCENARIO_FORMAT, version: 1, world, policy, now, time_scale, selected_aircraft_id };
}
export function parseScenario(text: string): ScenarioFile {
  if (new TextEncoder().encode(text).byteLength > MAX_SCENARIO_BYTES) throw new Error('Scenario files must be at most 256 KiB.');
  let parsed: unknown;
  try { parsed = JSON.parse(text); } catch { throw new Error('The selected file is not valid JSON.'); }
  const value = record(parsed, 'Scenario');
  if (value.format !== SCENARIO_FORMAT || value.version !== 1) throw new Error('Choose a TowerOps Airspace scenario file with format version 1. Raw WorldState JSON uses the existing workbench below.');
  exactKeys(value, ['format', 'version', 'world', 'policy', 'now', 'time_scale', 'selected_aircraft_id'], 'Scenario');
  return createScenario(value as unknown as ScenarioSnapshot);
}

// JSON.stringify changes -0 into 0; TowerOps world hashes distinguish them.
// Format the validated data only, keeping ordinary JSON number syntax even for
// large or subnormal finite values. JSON.parse restores the signed zero.
function dataJson(value: unknown, depth = 0): string {
  if (typeof value === 'number') return Object.is(value, -0) ? '-0' : JSON.stringify(value);
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  const indent = '  '.repeat(depth), child = indent + '  ';
  if (Array.isArray(value)) return value.length ? '[\n' + value.map(item => child + dataJson(item, depth + 1)).join(',\n') + '\n' + indent + ']' : '[]';
  return '{\n' + Object.entries(value).map(([key, item]) => child + JSON.stringify(key) + ': ' + dataJson(item, depth + 1)).join(',\n') + '\n' + indent + '}';
}
export function serializeScenario(snapshot: ScenarioSnapshot): { text: string; filename: string; mime: string } {
  const scenario = createScenario(snapshot);
  const text = dataJson(scenario) + '\n';
  if (new TextEncoder().encode(text).byteLength > MAX_SCENARIO_BYTES) throw new Error('The scenario is larger than the 256 KiB file limit.');
  return { text, filename: `towerops-scenario-v${scenario.world.version}.json`, mime: 'application/json;charset=utf-8' };
}
