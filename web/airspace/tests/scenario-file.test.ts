import { describe, expect, it } from 'vitest';
import { DEFAULT_POLICY, conflictPairs, worldHash } from '../src/core';
import { MAX_SCENARIO_BYTES, SCENARIO_FORMAT, ScenarioSnapshot, createScenario, parseScenario, serializeScenario } from '../src/scenario-file';

function snapshot(): ScenarioSnapshot {
  return {
    world: { version: 7, observed_at: 1000, aircraft: [
      { aircraft_id: 'TWR101', x_nm: 0, y_nm: 0, altitude_ft: 10000, vx_nm_min: 0, vy_nm_min: 0, climb_ft_min: 0 },
      { aircraft_id: 'TWR202', x_nm: 7, y_nm: 0, altitude_ft: 10000, vx_nm_min: 0, vy_nm_min: 0, climb_ft_min: 0 },
    ] },
    policy: { ...DEFAULT_POLICY, min_horizontal_nm: 9, min_vertical_ft: 1500, horizon_min: 8 },
    now: 1002.5, time_scale: 2.5, selected_aircraft_id: 'TWR202',
  };
}
const read = (value: unknown) => parseScenario(JSON.stringify(value));

describe('portable synthetic scenarios', () => {
  it('restores the policy that determines the saved conflict, plus clock and selection', async () => {
    const before = snapshot();
    const file = serializeScenario(before), after = parseScenario(file.text);
    expect(conflictPairs(before.world, before.policy)).toEqual([['TWR101', 'TWR202']]);
    expect(conflictPairs(before.world, { ...DEFAULT_POLICY, min_horizontal_nm: 3 })).toEqual([]);
    expect(conflictPairs(after.world, after.policy)).toEqual(conflictPairs(before.world, before.policy));
    expect(await worldHash(after.world)).toBe(await worldHash(before.world));
    expect(after).toEqual({ format: SCENARIO_FORMAT, version: 1, ...before });
    expect(file.filename).toBe('towerops-scenario-v7.json');
    expect(file.mime).toBe('application/json;charset=utf-8');
  });
  it('makes independent data copies and emits only scenario data', () => {
    const before = snapshot(), saved = createScenario(before);
    const original = serializeScenario(before).text;
    before.world.aircraft[0]!.x_nm = 44; before.policy.min_horizontal_nm = 3;
    expect(saved.world.aircraft[0]!.x_nm).toBe(0); expect(saved.policy.min_horizontal_nm).toBe(9);
    expect(serializeScenario(saved).text).toBe(original);
    expect(Object.keys(saved).sort()).toEqual(['format','now','policy','selected_aircraft_id','time_scale','version','world']);
  });
  it.each([-0, Number.MIN_VALUE, Number.MAX_VALUE, 1e21, 1e-20, Math.PI, -123.456])('round-trips finite numeric value %s without changing its identity', value => {
    const before = snapshot(); before.world.aircraft[0]!.x_nm = value; before.now = value;
    const result = parseScenario(serializeScenario(before).text);
    expect(Object.is(result.world.aircraft[0]!.x_nm, value)).toBe(true);
    expect(Object.is(result.now, value)).toBe(true);
  });
  it('keeps the signed-zero world hash stable through actual JSON text', async () => {
    const before = snapshot(); before.world.aircraft[0]!.vx_nm_min = -0;
    const after = parseScenario(serializeScenario(before).text);
    expect(await worldHash(after.world)).toBe(await worldHash(before.world));
    expect(Object.is(after.world.aircraft[0]!.vx_nm_min, -0)).toBe(true);
  });
  it.each([1, 60])('supports %s aircraft with preserved ordering and selection', count => {
    const before = snapshot();
    before.world.aircraft = Array.from({ length: count }, (_, i) => ({ ...before.world.aircraft[0]!, aircraft_id: 'TWR' + i }));
    before.selected_aircraft_id = 'TWR' + (count - 1);
    const after = parseScenario(serializeScenario(before).text);
    expect(after.world.aircraft.map(a => a.aircraft_id)).toEqual(before.world.aircraft.map(a => a.aircraft_id));
    expect(after.selected_aircraft_id).toBe(before.selected_aircraft_id);
  });
  it.each([0, 61])('refuses unsupported aircraft count %s', count => {
    const before = snapshot();
    before.world.aircraft = Array.from({ length: count }, (_, i) => ({ ...snapshot().world.aircraft[0]!, aircraft_id: 'TWR' + i }));
    expect(() => createScenario(before)).toThrow('between 1 and 60');
  });
  it('refuses duplicate or noncanonical callsigns without silently renaming a saved identity', () => {
    const before = snapshot(); before.world.aircraft[1]!.aircraft_id = 'TWR101';
    expect(() => createScenario(before)).toThrow('Duplicate callsign');
    before.world.aircraft[1]!.aircraft_id = 'twr202';
    expect(() => createScenario(before)).toThrow('uppercase');
  });
  it('requires selection to belong to the saved world', () => {
    const before = snapshot(); before.selected_aircraft_id = 'FOREIGN';
    expect(() => createScenario(before)).toThrow('selected_aircraft_id');
  });
  it.each([-1, 0.5, Number.MAX_SAFE_INTEGER + 1, '7', true])('refuses invalid world version %s', value => {
    const doc = createScenario(snapshot()); (doc.world as unknown as Record<string, unknown>).version = value;
    expect(() => read(doc)).toThrow('safe integer');
  });
  it('preserves a valid large version without unsafe filename characters', () => {
    const before = snapshot(); before.world.version = Number.MAX_SAFE_INTEGER;
    const file = serializeScenario(before);
    expect(file.filename).toBe('towerops-scenario-v9007199254740991.json');
    expect(parseScenario(file.text).world.version).toBe(Number.MAX_SAFE_INTEGER);
  });
  it('rejects extra world and aircraft data rather than silently discarding it', () => {
    const doc = createScenario(snapshot());
    expect(() => read({ ...doc, world: { ...doc.world, approval: {} } })).toThrow('world needs exactly');
    expect(() => read({ ...doc, world: { ...doc.world, aircraft: [{ ...doc.world.aircraft[0], url: 'https://invalid.example/' }] } })).toThrow('Aircraft 1 needs exactly');
  });
  it.each(['x_nm','y_nm','altitude_ft','vx_nm_min','vy_nm_min','climb_ft_min'])('refuses malformed %s without coercion', key => {
    for (const value of ['1', null, true, NaN, Infinity]) {
      const doc = createScenario(snapshot());
      (doc.world.aircraft[0] as unknown as Record<string, unknown>)[key] = value;
      expect(() => read(doc)).toThrow('finite number');
    }
  });
  it('rejects nonfinite or coerced clock values', () => {
    const doc = createScenario(snapshot());
    for (const now of [true, null, '1002', Infinity, NaN]) expect(() => read({ ...doc, now })).toThrow('finite number');
    expect(() => parseScenario(JSON.stringify(doc).replace('"now":1002.5','"now":1e999'))).toThrow('finite number');
  });
  it('keeps finite clock offsets for the existing freshness gate to evaluate', () => {
    const before = snapshot(); before.now = before.world.observed_at + 99;
    expect(parseScenario(serializeScenario(before).text).now).toBe(1099);
  });
  it.each([
    ['min_horizontal_nm',2.5],['min_horizontal_nm',10.5],['min_horizontal_nm',3.1],
    ['min_vertical_ft',400],['min_vertical_ft',2600],['min_vertical_ft',1550],
    ['horizon_min',1.5],['horizon_min',10.5],['horizon_min',4.1],
  ])('refuses a %s setting that the current controls cannot represent: %s', (key, value) => {
    const doc = createScenario(snapshot()); (doc.policy as unknown as Record<string, unknown>)[key as string] = value;
    expect(() => read(doc)).toThrow('in steps');
  });
  it.each(['sample_step_min','max_state_age_sec','max_speed_nm_min','max_climb_ft_min'])('does not import an invisible change to %s', key => {
    const doc = createScenario(snapshot()); (doc.policy as unknown as Record<string, unknown>)[key] = 0;
    expect(() => read(doc)).toThrow('not configurable');
  });
  it('requires all policy fields and refuses unexpected policy fields', () => {
    const doc = createScenario(snapshot()), policy = { ...doc.policy } as Record<string, unknown>;
    delete policy.horizon_min;
    expect(() => read({ ...doc, policy })).toThrow('policy needs exactly');
    expect(() => read({ ...doc, policy: { ...doc.policy, approve_all: true } })).toThrow('policy needs exactly');
    expect(() => read({ ...doc, policy: { ...doc.policy, horizon_min: '8' } })).toThrow('finite number');
  });
  it.each([0, 0.75, 3.5, '2', true])('refuses unsupported time scale %s', time_scale => {
    expect(() => read({ ...createScenario(snapshot()), time_scale })).toThrow();
  });
  it.each([0.5, 1, 1.5, 2, 2.5, 3])('restores the supported time scale %s', time_scale => {
    expect(read({ ...createScenario(snapshot()), time_scale }).time_scale).toBe(time_scale);
  });
  it('rejects raw WorldState with a useful pointer to its existing reader', () => {
    expect(() => read(snapshot().world)).toThrow('Raw WorldState JSON uses the existing workbench');
  });
  it.each([0, 2, '1', true])('refuses unsupported format version %s', version => {
    expect(() => read({ ...createScenario(snapshot()), version })).toThrow('format version 1');
  });
  it.each([null, false, [], 4, 'text'])('rejects a non-object document %j', value => {
    expect(() => read(value)).toThrow('must be an object');
  });
  it('refuses unknown top-level metadata, approvals and prototype keys', () => {
    const doc = createScenario(snapshot());
    expect(() => read({ ...doc, approval: { decision: 'approve' } })).toThrow('Scenario needs exactly');
    expect(() => parseScenario(JSON.stringify(doc).replace('{','{"__proto__":{"polluted":true},'))).toThrow('Scenario needs exactly');
    expect(({} as Record<string, unknown>).polluted).toBeUndefined();
  });
  it('reports malformed JSON and bounds UTF-8 file input before parsing', () => {
    expect(() => parseScenario('{not json')).toThrow('not valid JSON');
    expect(() => parseScenario(' '.repeat(MAX_SCENARIO_BYTES + 1))).toThrow('256 KiB');
    expect(() => parseScenario('😀'.repeat(MAX_SCENARIO_BYTES / 4 + 1))).toThrow('256 KiB');
  });
});
