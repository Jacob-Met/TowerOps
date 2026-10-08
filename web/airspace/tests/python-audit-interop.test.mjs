import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import reference from './python-reference.json';
import { DEFAULT_POLICY } from '../src/core';
import { AuditLog } from '../src/audit';

// Exercise the exact Python function shipped in the Worker. The native
// interpreter is a receiving oracle, not a reimplementation of the bridge.
const root = fileURLToPath(new URL('../../..', import.meta.url));
const worker = readFileSync(new URL('../src/python-worker.ts', import.meta.url), 'utf8');
const bridge = worker.match(/await py\.runPythonAsync\(`([\s\S]*?)`\);/)?.[1];
if (!bridge) throw new Error('The shipped browser_request definition was not found');

function applyThroughPython(now) {
  const state = structuredClone(reference.scenarios[0].state);
  state.observed_at = now;
  const requests = {
    plan: { op: 'plan', state, now, policy: DEFAULT_POLICY },
    approvalAt: now + 0.2,
    acknowledgedAt: now + 0.4,
    applyAt: now + 0.5,
  };
  const driver = `${bridge}\n
import sys
requests = json.load(sys.stdin)
q = requests['plan']
plan = json.loads(browser_request(json.dumps(q)))['advisory']
if plan is None:
    raise RuntimeError('The baseline crossing must produce an advisory')
q.update(op='apply', advisory=plan,
    approval={'advisory_hash': plan['advisory_hash'], 'decision': 'approve',
              'approved_at': requests['approvalAt'], 'approver': 'synthetic-controller'},
    ack={'advisory_hash': plan['advisory_hash'], 'status': 'accepted',
         'acknowledged_at': requests['acknowledgedAt']}, now=requests['applyAt'])
print(browser_request(json.dumps(q)))
`;
  return JSON.parse(execFileSync(process.env.TOWEROPS_PYTHON ?? 'python3', ['-c', driver], {
    cwd: root,
    input: JSON.stringify(requests),
    encoding: 'utf8',
    timeout: 15_000,
  }));
}

describe('real Python Worker audit received by the browser verifier', () => {
  it.each([1000, 0.8, 0.6])('keeps a valid approval/readback chain at clock %s valid', async now => {
    const result = applyThroughPython(now);
    expect(result.error).toBeUndefined();
    expect(result.valid).toBe(true);
    expect(result.events.map(event => event.kind)).toEqual([
      'screen_pass', 'approval', 'ack', 'simulated_actuation',
    ]);
    const audit = new AuditLog();
    audit.events = result.events;
    expect(await audit.verify(), result.audit_json).toBe(true);
  });
});
