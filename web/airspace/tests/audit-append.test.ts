import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuditLog, rememberPythonAudit, ZERO_HASH } from '../src/audit';
import { applyAdvisory } from '../src/actuation';
import { planAdvisory } from '../src/planner';
import type { Ack, Approval } from '../src/gate';
import auditFixtures from './python-audit-wire.json';
import reference from './python-reference.json';

afterEach(() => vi.restoreAllMocks());

describe('AuditLog append ownership and ordering', () => {
  it('serializes concurrent calls in invocation order into one verifiable chain', async () => {
    const audit = new AuditLog();
    const hashes = await Promise.all(Array.from({ length: 12 }, (_, index) =>
      audit.append('queued', { index }),
    ));

    expect(audit.events.map(event => event.seq)).toEqual(Array.from({ length: 12 }, (_, i) => i));
    expect(audit.events.map(event => event.payload.index)).toEqual(Array.from({ length: 12 }, (_, i) => i));
    expect(audit.events.map(event => event.event_hash)).toEqual(hashes);
    expect(audit.events[0]!.prev_hash).toBe(ZERO_HASH);
    expect(await audit.verify()).toBe(true);
  });

  it('snapshots nested payloads when called, including calls waiting behind another append', async () => {
    const audit = new AuditLog();
    const payload = { nested: { approver: 'original', values: [1, -0, 3] } };
    const expected = structuredClone(payload);
    const first = audit.append('first', {});
    const queued = audit.append('queued', payload);
    payload.nested.approver = 'changed while queued';
    payload.nested.values.push(4);
    await Promise.all([first, queued]);
    payload.nested.approver = 'changed after completion';
    payload.nested.values[1] = 0;

    expect(audit.events[1]!.payload).toEqual(expected);
    const recorded = audit.events[1]!.payload as typeof payload;
    expect(Object.is(recorded.nested.values[1], -0)).toBe(true);
    expect(recorded.nested).not.toBe(payload.nested);
    expect(await audit.verify()).toBe(true);
  });

  it('refuses invalid payloads without consuming a sequence or preventing later appends', async () => {
    const audit = new AuditLog();
    for (const value of [NaN, Infinity, undefined, () => 1]) {
      await expect(audit.append('invalid', { value })).rejects.toBeDefined();
    }
    expect(audit.events).toEqual([]);
    await audit.append('valid', { value: 1 });
    expect(audit.events[0]!.seq).toBe(0);
    expect(await audit.verify()).toBe(true);
  });

  it('continues queued work after a digest rejection without publishing a failed event', async () => {
    const audit = new AuditLog();
    vi.spyOn(globalThis.crypto.subtle, 'digest').mockRejectedValueOnce(new Error('injected digest failure'));
    const failed = audit.append('failed', {});
    const next = audit.append('next', { value: 2 });
    const results = await Promise.allSettled([failed, next]);

    expect(results[0]).toMatchObject({ status: 'rejected', reason: { message: 'injected digest failure' } });
    expect(results[1]!.status).toBe('fulfilled');
    expect(audit.events.map(event => [event.seq, event.kind])).toEqual([[0, 'next']]);
    expect(await audit.verify()).toBe(true);
  });

  it('keeps received Python history and its original canonical bodies when appends overlap', async () => {
    const fixture = auditFixtures.cases.find(item => item.name === 'integral_approval')!;
    const audit = new AuditLog();
    audit.events = structuredClone(fixture.events);
    const originalBodies = [...fixture.audit_canonical];
    rememberPythonAudit(audit.events, originalBodies);
    const before = structuredClone(audit.events);

    await Promise.all([
      audit.append('review_one', { reviewer: 'one' }),
      audit.append('review_two', { reviewer: 'two' }),
    ]);

    expect(audit.events.slice(0, before.length)).toEqual(before);
    expect(originalBodies).toEqual(fixture.audit_canonical);
    expect(audit.events.slice(before.length).map(event => event.seq)).toEqual([before.length, before.length + 1]);
    expect(await audit.verify()).toBe(true);
  });

  it('refuses queued work if its history is replaced before hashing begins', async () => {
    const audit = new AuditLog();
    const original = audit.events;
    const pending = audit.append('old_history', {});
    audit.events = [];

    await expect(pending).rejects.toThrow('Audit history changed before append');
    expect(original).toEqual([]);
    expect(audit.events).toEqual([]);
    await audit.append('new_history', {});
    expect(audit.events.map(event => event.kind)).toEqual(['new_history']);
    expect(await audit.verify()).toBe(true);
  });

  it('refuses publication if history is replaced while the real digest is pending', async () => {
    const audit = new AuditLog();
    const original = audit.events;
    const realDigest = globalThis.crypto.subtle.digest.bind(globalThis.crypto.subtle);
    let release!: () => void;
    let started!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    const hashing = new Promise<void>(resolve => { started = resolve; });
    vi.spyOn(globalThis.crypto.subtle, 'digest').mockImplementationOnce((algorithm, data) => {
      started();
      return held.then(() => realDigest(algorithm, data));
    });
    const pending = audit.append('old_history', {});
    await hashing;
    audit.events = [];
    release();

    await expect(pending).rejects.toThrow('Audit history changed during append');
    expect(original).toEqual([]);
    expect(audit.events).toEqual([]);
    await audit.append('new_history', {});
    expect(audit.events.map(event => event.kind)).toEqual(['new_history']);
    expect(await audit.verify()).toBe(true);
  });

  it('retains the real advisory approval and acknowledgement when callers reuse their objects', async () => {
    const scenario = reference.scenarios.find(item => item.name === 'demo_crossing')!;
    const state = structuredClone(scenario.state);
    const before = structuredClone(state);
    const advisory = await planAdvisory(state, scenario.now);
    expect(advisory).not.toBeNull();
    if (!advisory) throw new Error('The crossing fixture must produce an advisory');
    const approval: Approval = {
      advisory_hash: advisory.advisory_hash, decision: 'approve',
      approved_at: scenario.now + 0.2, approver: 'synthetic-controller',
    };
    const ack: Ack = {
      advisory_hash: advisory.advisory_hash, status: 'accepted',
      acknowledged_at: scenario.now + 0.4,
    };
    const audit = new AuditLog();
    const after = await applyAdvisory(state, advisory, approval, ack, scenario.now + 0.5, audit);
    expect(after).toEqual(scenario.after_state);
    expect(state).toEqual(before);
    expect(audit.events).toEqual(scenario.audit_events);
    expect(await audit.verify()).toBe(true);

    approval.approver = 'caller reused approval';
    approval.approved_at = -1;
    ack.status = 'caller reused acknowledgement';
    ack.acknowledged_at = -1;

    expect(audit.events).toEqual(scenario.audit_events);
    expect(audit.events.map(event => event.kind)).toEqual(['screen_pass', 'approval', 'ack', 'simulated_actuation']);
    expect(await audit.verify()).toBe(true);
  });
});
