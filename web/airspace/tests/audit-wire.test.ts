import { describe, expect, it } from 'vitest';
import { AuditLog, rememberPythonAudit } from '../src/audit';
import fixtures from './python-audit-wire.json';

const copy = <T>(value:T):T => structuredClone(value);

describe('original Python audit hash inputs survive the browser transport', () => {
  it.each(fixtures.cases)('verifies actual Python $name without rewriting any event', async fixture => {
    const events = copy(fixture.events);
    const before = copy(events);
    rememberPythonAudit(events, fixture.audit_canonical);
    const audit = new AuditLog();
    audit.events = events;
    expect(await audit.verify()).toBe(true);
    expect(events).toEqual(before);
    expect(JSON.stringify(events)).not.toContain('audit_canonical');
  });

  it('pins the actual Python int/float distinction that was lost by JSON.parse', async () => {
    const fixture = fixtures.cases.find(item => item.name === 'integral_approval')!;
    expect(fixture.audit_canonical[1]).toContain('"approved_at":1001,');
    const audit = new AuditLog();
    audit.events = copy(fixture.events);
    expect(await audit.verify()).toBe(false);
    rememberPythonAudit(audit.events, fixture.audit_canonical);
    expect(await audit.verify()).toBe(true);
  });

  it.each([
    ['displayed approver', (audit:AuditLog) => { audit.events[1]!.payload.approver = 'changed after receipt'; }],
    ['displayed timestamp', (audit:AuditLog) => { audit.events[1]!.payload.approved_at = 1002; }],
    ['claimed event hash', (audit:AuditLog) => { audit.events[1]!.event_hash = 'f'.repeat(64); }],
    ['previous hash', (audit:AuditLog) => { audit.events[1]!.prev_hash = '0'.repeat(64); }],
    ['sequence', (audit:AuditLog) => { audit.events[1]!.seq = 9; }],
    ['removed event', (audit:AuditLog) => { audit.events.splice(1, 1); }],
    ['reordered events', (audit:AuditLog) => { audit.events.reverse(); }],
  ] as const)('refuses a changed %s even with retained original hash input', async (_name, change) => {
    const fixture = fixtures.cases[1]!;
    const audit = new AuditLog();
    audit.events = copy(fixture.events);
    rememberPythonAudit(audit.events, fixture.audit_canonical);
    change(audit);
    expect(await audit.verify()).toBe(false);
  });

  it.each([
    ['missing', undefined],
    ['wrong count', []],
    ['wrong type', ['not a JSON body', 7, null, true]],
    ['invalid JSON', ['{', '{', '{', '{']],
    ['unrelated bodies', ['{}', '{}', '{}', '{}']],
  ] as const)('refuses %s Python metadata without guessing a replacement', async (_name, bodies) => {
    const audit = new AuditLog();
    audit.events = copy(fixtures.cases[0]!.events);
    rememberPythonAudit(audit.events, bodies);
    expect(await audit.verify()).toBe(false);
  });

  it('checks the supplied bytes as well as their decoded payload', async () => {
    const fixture = fixtures.cases[0]!;
    const audit = new AuditLog();
    audit.events = copy(fixture.events);
    const bodies = [...fixture.audit_canonical];
    bodies[0] = JSON.stringify(JSON.parse(bodies[0]!), null, 2);
    rememberPythonAudit(audit.events, bodies);
    expect(await audit.verify()).toBe(false);
  });

  it('can append after received history without changing the native prefix', async () => {
    const fixture = fixtures.cases[1]!;
    const audit = new AuditLog();
    audit.events = copy(fixture.events);
    const bodies = [...fixture.audit_canonical];
    rememberPythonAudit(audit.events, bodies);
    await audit.append('browser_review', { reviewer: 'independent test' });
    expect(await audit.verify()).toBe(true);
    expect(audit.events.slice(0, fixture.events.length)).toEqual(fixture.events);
    expect(bodies).toEqual(fixture.audit_canonical);
    expect(audit.events.at(-1)!.prev_hash).toBe(fixture.events.at(-1)!.event_hash);
  });

  it('does not transfer source metadata to an unrelated array', async () => {
    const fixture = fixtures.cases[1]!;
    const audit = new AuditLog();
    audit.events = copy(fixture.events);
    rememberPythonAudit(audit.events, fixture.audit_canonical);
    const received = audit.events;
    audit.events = copy(received);
    expect(await audit.verify()).toBe(false);
    audit.events = received;
    expect(await audit.verify()).toBe(true);
  });
});
