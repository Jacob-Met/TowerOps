import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { MAX_TRACE_BYTES, checkTraceSize, traceDownload } from '../src/decision-trace';

const root = fileURLToPath(new URL('../../..', import.meta.url));
const source = readFileSync(new URL('../src/python-worker.ts', import.meta.url), 'utf8');
const bridge = source.match(/await py\.runPythonAsync\(`([\s\S]*?)`\);/)?.[1];
if (!bridge) throw new Error('The actual Python Worker bridge was not found');

function nativeRequest(request) {
  return JSON.parse(execFileSync(process.env.TOWEROPS_PYTHON ?? 'python3', ['-c', `${bridge}\nimport sys\nprint(browser_request(sys.stdin.read()))\n`], {
    cwd: root, input: JSON.stringify(request), encoding: 'utf8', timeout: 15_000,
  }));
}

describe('native decision-trace delivery', () => {
  it('reviews a trace without any world, policy, advisory, approval or ack in the request', () => {
    const result = nativeRequest({op: 'review_trace', trace_json: '[]'});
    expect(result).toEqual({chain_valid: true, ok: true, event_count: 0, advisories: [], rejects: [], issues: []});
    expect(Object.keys(result)).not.toContain('state');
  });

  it.each(['{', '[null]', '{}'])('returns a bounded delivery error for malformed trace %s', raw => {
    const result = nativeRequest({op: 'review_trace', trace_json: raw});
    expect(Object.keys(result)).toEqual(['error']);
    expect(result.error).toMatch(/Decision trace|Expected an event list/);
    expect(result.error).not.toContain('Traceback');
  });

  it('downloads and reopens exact native JSON including float spellings and Unicode', async () => {
    const raw = execFileSync(process.env.TOWEROPS_PYTHON ?? 'python3', ['-c', `
import json
from towerops import AuditLog
log = AuditLog()
log.append('reject', {'reason': 'révision <history>', 'approved_at': 1.0, 'offset': -0.0, 'tiny': 1e-5})
print(json.dumps(log.events, ensure_ascii=False), end='')
`], {cwd: root, encoding: 'utf8', timeout: 15_000});
    const reopened = await traceDownload(raw).text();
    expect(reopened).toBe(raw);
    expect(raw).toContain('1.0');
    expect(raw).toContain('-0.0');
    expect(raw).toContain('1e-05');
    expect(nativeRequest({op: 'review_trace', trace_json: reopened})).toMatchObject({chain_valid: true, ok: true, event_count: 1});
    // A JavaScript parse/stringify cycle changes the original native hashes.
    expect(nativeRequest({op: 'review_trace', trace_json: JSON.stringify(JSON.parse(raw))})).toMatchObject({chain_valid: false, ok: false});
  });

  it('applies the browser review bound to UTF-8 bytes while downloads retain the original text', async () => {
    expect(() => checkTraceSize(' '.repeat(MAX_TRACE_BYTES))).not.toThrow();
    const oversized = 'é'.repeat(MAX_TRACE_BYTES / 2 + 1);
    expect(oversized.length).toBeLessThan(MAX_TRACE_BYTES);
    expect(() => checkTraceSize(oversized)).toThrow('2 MiB');
    expect(await traceDownload(oversized).text()).toBe(oversized);
  });
});
