import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { DEFAULT_POLICY, canonicalJson, hashObject, worldHash } from '../src/core';
import { AuditLog } from '../src/audit';

const root = fileURLToPath(new URL('../../..', import.meta.url));
const worker = readFileSync(new URL('../src/python-worker.ts', import.meta.url), 'utf8');
const bridge = worker.match(/await py\.runPythonAsync\(`([\s\S]*?)`\);/)?.[1];
if (!bridge) throw new Error('The shipped browser_request definition was not found');

function python(script, input) {
  return JSON.parse(execFileSync(process.env.TOWEROPS_PYTHON ?? 'python3',
    [...(process.env.TOWEROPS_TEST_OPTIMIZE === '1' ? ['-O'] : []), '-c', script], {
      cwd: root, input: JSON.stringify(input), encoding: 'utf8', timeout: 15_000,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    }));
}
function native(request) {
  return python(`${bridge}
import sys
from towerops import canonical_bytes
result = json.loads(browser_request(sys.stdin.read()))
if 'events' in result:
    result['canonical_events'] = [canonical_bytes({k: v for k, v in event.items()
        if k != 'event_hash'}).decode('utf-8') for event in result['events']]
print(json.dumps(result))
`, request);
}

const transactions = [
  { name: 'positive microsecond approval', clock: 0, approved: 0.000001, acknowledged: 0.000002, applied: 0.000003 },
  { name: 'UI offsets yielding a small fraction', clock: -0.199999 },
  { name: 'large fractional clock control', clock: 1000000000000000.25 },
  { name: 'large clock in Python exponent notation', clock: 10000000000000000 },
];

describe('Python float canonical bytes received by native TypeScript consumers', () => {
  it.each(transactions)('$name preserves admitted state and audit hashes', async item => {
    const state = { version: 7, observed_at: item.clock, aircraft: [
      { aircraft_id: 'PARITY-L', x_nm: -8, y_nm: 0, altitude_ft: 10000, vx_nm_min: 3, vy_nm_min: 0, climb_ft_min: 0 },
      { aircraft_id: 'PARITY-R', x_nm: 8, y_nm: 0, altitude_ft: 10000, vx_nm_min: -3, vy_nm_min: 0, climb_ft_min: 0 },
    ] };
    const { advisory } = native({ op: 'plan', state, policy: DEFAULT_POLICY, now: item.clock });
    expect(advisory).toBeTruthy();
    const result = native({ op: 'apply', state, policy: DEFAULT_POLICY, advisory,
      approval: { advisory_hash: advisory.advisory_hash, decision: 'approve',
        approved_at: item.approved ?? item.clock + 0.2, approver: 'parity-review' },
      ack: { advisory_hash: advisory.advisory_hash, status: 'accepted',
        acknowledged_at: item.acknowledged ?? item.clock + 0.4 },
      now: item.applied ?? item.clock + 0.5, audit_json: '[]' });
    expect(result.error).toBeUndefined();
    expect(result.valid).toBe(true);
    expect(result.state.version).toBe(8);
    expect(result.events.map(event => event.kind)).toEqual([
      'screen_pass', 'approval', 'ack', 'simulated_actuation',
    ]);
    expect(await worldHash(state)).toBe(advisory.world_hash);
    const { advisory_hash, ...body } = advisory;
    expect(await hashObject(body)).toBe(advisory_hash);
    expect(result.events.map(({ event_hash, ...event }) => canonicalJson(event))).toEqual(result.canonical_events);
    const audit = new AuditLog(); audit.events = result.events;
    expect(await audit.verify(), result.audit_json).toBe(true);
    audit.events = structuredClone(result.events);
    audit.events[1].payload.approver += '!';
    expect(await audit.verify()).toBe(false);
  });

  it('matches actual Python canonical bytes at signed format and finite limits', () => {
    const decimalInputs = ['1e-4', '-1e-4', '1e-5', '-1e-5', '1e15', '1e16',
      '0.0', '-0.0', '5e-324', '-5e-324', '1.7976931348623157e308', '-1.7976931348623157e308'];
    const expected = python(`import json, sys
from towerops import canonical_bytes
values = json.load(sys.stdin)
print(json.dumps({'floats': [canonical_bytes(float(v)).decode('utf-8') for v in values],
    'integer_keys': canonical_bytes({'seq': 7, 'version': 8, 'value': -0.0}).decode('utf-8')}))
`, decimalInputs);
    expect(decimalInputs.map(value => canonicalJson(Number(value)))).toEqual(expected.floats);
    for (const value of decimalInputs.map(Number)) {
      expect(Object.is(JSON.parse(canonicalJson(value)), value)).toBe(true);
    }
    expect(canonicalJson({ seq: 7, version: 8, value: -0.0 })).toBe(expected.integer_keys);
    for (const value of [NaN, Infinity, -Infinity]) {
      expect(() => canonicalJson(value)).toThrow('TowerOps state must be finite');
    }
  });
});
