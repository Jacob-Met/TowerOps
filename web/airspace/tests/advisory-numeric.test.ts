import { describe, expect, it } from 'vitest';
import { AuditLog } from '../src/audit';
import { applyAdvisory } from '../src/actuation';
import { WorldState, worldHash } from '../src/core';
import { Ack, Approval, screenBatch } from '../src/gate';
import { Advisory, AdvisoryBody, advisorySafe } from '../src/planner';

const commandFields = ['set_vx_nm_min', 'set_vy_nm_min', 'set_climb_ft_min'] as const;
const positionFields = ['x_nm', 'y_nm', 'altitude_ft'] as const;

function singleton(): WorldState {
  return {
    version: 1, observed_at: 1000,
    aircraft: [{ aircraft_id: 'ALONE', x_nm: 0, y_nm: 0, altitude_ft: 12000,
      vx_nm_min: 3, vy_nm_min: 0, climb_ft_min: 0 }],
  };
}

async function proposal(state: WorldState, changes: Partial<AdvisoryBody> = {}): Promise<Advisory> {
  return {
    aircraft_id: 'ALONE', world_hash: await worldHash(state),
    set_vx_nm_min: 2, set_vy_nm_min: 1, set_climb_ft_min: 0,
    issued_at: 1001, expires_at: 1008, rationale: 'synthetic numeric admission control',
    // The screening boundary must reject malformed values independently of a
    // caller's opaque advisory identifier; this is not a signed attestation.
    advisory_hash: 'synthetic-numeric-control', ...changes,
  };
}

async function expectUnsafe(state: WorldState, advisory: Advisory): Promise<void> {
  const before = structuredClone(state);
  expect(await advisorySafe(state, advisory)).toBe(false);
  const audit = new AuditLog();
  await expect(screenBatch(state, [advisory], 1001, audit))
    .rejects.toMatchObject({ reason: 'unsafe_advisory' });
  expect(audit.events.map(e => e.kind)).toEqual(['reject']);
  expect(audit.events[0]!.payload).toEqual({ reason: 'unsafe_advisory', advisory_hash: advisory.advisory_hash });
  expect(await audit.verify()).toBe(true);
  expect(state).toEqual(before);
}

describe('numeric admission does not depend on another aircraft', () => {
  it.each(commandFields)('rejects NaN in %s through the screening gate', async field => {
    const state = singleton();
    await expectUnsafe(state, await proposal(state, { [field]: Number.NaN }));
  });

  it.each(commandFields.flatMap(field => [true, '1', null].map(value => ({ field, value }))))
    ('rejects coercible command $field=$value', async ({ field, value }) => {
      const state = singleton();
      await expectUnsafe(state, await proposal(state, { [field]: value as unknown as number }));
    });

  it.each(positionFields.flatMap(field => [false, '0', null].map(value => ({ field, value }))))
    ('rejects a retained nonnumeric position $field=$value', async ({ field, value }) => {
      const state = singleton();
      state.aircraft[0]![field] = value as unknown as number;
      await expectUnsafe(state, await proposal(state));
    });

  it.each([[0, 0, 0], [6, 0, 3000], [0, -6, -3000]])
    ('preserves finite approved rates (%s, %s, %s), including the exact bounds', async (vx, vy, climb) => {
      const state = singleton(), before = structuredClone(state);
      const advisory = await proposal(state, { set_vx_nm_min: vx, set_vy_nm_min: vy, set_climb_ft_min: climb });
      const approval: Approval = { advisory_hash: advisory.advisory_hash, decision: 'approve',
        approved_at: 1001.2, approver: 'synthetic-controller' };
      const ack: Ack = { advisory_hash: advisory.advisory_hash, status: 'accepted', acknowledged_at: 1001.4 };
      expect(await advisorySafe(state, advisory)).toBe(true);
      const audit = new AuditLog();
      const after = await applyAdvisory(state, advisory, approval, ack, 1001.5, audit);
      expect(after.version).toBe(2);
      expect(after.aircraft[0]).toEqual({ ...state.aircraft[0], vx_nm_min: vx, vy_nm_min: vy, climb_ft_min: climb });
      expect(audit.events.map(e => e.kind)).toEqual(['screen_pass', 'approval', 'ack', 'simulated_actuation']);
      expect(await audit.verify()).toBe(true);
      expect(state).toEqual(before);
    });

  it('still rejects an unknown target with finite rates', async () => {
    const state = singleton();
    await expectUnsafe(state, await proposal(state, { aircraft_id: 'ABSENT' }));
  });
});
