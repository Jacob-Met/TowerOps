import { describe, expect, it } from 'vitest';
import reference from './python-reference.json';
import { DEFAULT_POLICY, WorldState } from '../src/core';
import { Advisory } from '../src/planner';
import {
  NativeAdvisoryOptions, optionsSnapshotKey, receiveAdvisoryOptions, selectAdvisoryOption,
} from '../src/advisory-options';

const source = reference.scenarios[0]!;
function fixture() {
  const state = structuredClone(source.state) as WorldState;
  const policy = { ...DEFAULT_POLICY };
  const now = source.now;
  const advisory = { ...source.advisory, advisory_hash: source.advisory_hash } as Advisory;
  const result: NativeAdvisoryOptions = {
    world_hash: source.world_hash, reviewed_at: now, candidate_count: 1, advisories: [advisory],
  };
  const key = optionsSnapshotKey(state, policy, now);
  return { state, policy, now, result, key };
}

describe('native alternatives review binding', () => {
  it('selects the exact native body and hash without reconstructing displayed values', () => {
    const f = fixture();
    const review = receiveAdvisoryOptions(f.result, f.key, f.state, f.policy, f.now);
    const selected = selectAdvisoryOption(review, f.result.advisories[0]!.advisory_hash, f.state, f.policy, f.now);
    expect(selected).toEqual(f.result.advisories[0]);
    expect(selected).not.toBe(f.result.advisories[0]);
  });

  it('isolates the reviewed source from later response and selection mutations', () => {
    const f = fixture();
    const expected = { ...f.result.advisories[0]! };
    const review = receiveAdvisoryOptions(f.result, f.key, f.state, f.policy, f.now);
    f.result.advisories[0]!.set_vy_nm_min = 999;
    f.result.advisories.length = 0;
    const selected = selectAdvisoryOption(review, expected.advisory_hash, f.state, f.policy, f.now);
    selected.set_climb_ft_min = 999;
    expect(selectAdvisoryOption(review, expected.advisory_hash, f.state, f.policy, f.now)).toEqual(expected);
    expect(Object.isFrozen(review.advisories[0])).toBe(true);
  });

  it.each(['world', 'version', 'policy', 'clock'])('refuses a stale response and selection after a changed %s', field => {
    const f = fixture();
    const review = receiveAdvisoryOptions(f.result, f.key, f.state, f.policy, f.now);
    if (field === 'world') f.state.aircraft[0]!.x_nm += 0.1;
    if (field === 'version') f.state.version++;
    if (field === 'policy') f.policy.min_horizontal_nm += 0.5;
    if (field === 'clock') f.now += 0.01;
    expect(() => receiveAdvisoryOptions(f.result, f.key, f.state, f.policy, f.now)).toThrow(/world, clock or policy changed/);
    expect(() => selectAdvisoryOption(review, f.result.advisories[0]!.advisory_hash, f.state, f.policy, f.now)).toThrow(/world, clock or policy changed/);
  });

  it('accepts a new object representing the same exact snapshot', () => {
    const f = fixture();
    const review = receiveAdvisoryOptions(f.result, f.key, structuredClone(f.state), { ...f.policy }, f.now);
    expect(selectAdvisoryOption(review, f.result.advisories[0]!.advisory_hash, f.state, f.policy, f.now)).toEqual(f.result.advisories[0]);
  });

  it('never substitutes the first proposal for an unknown selection', () => {
    const f = fixture();
    const review = receiveAdvisoryOptions(f.result, f.key, f.state, f.policy, f.now);
    expect(() => selectAdvisoryOption(review, 'unknown', f.state, f.policy, f.now)).toThrow(/current native review/);
  });

  it.each(['count', 'world hash', 'duplicate', 'clock'])('refuses incomplete native metadata: %s', field => {
    const f = fixture();
    if (field === 'count') f.result.candidate_count = 0;
    if (field === 'world hash') f.result.advisories[0]!.world_hash = '0'.repeat(64);
    if (field === 'duplicate') { f.result.candidate_count++; f.result.advisories.push({ ...f.result.advisories[0]! }); }
    if (field === 'clock') f.result.reviewed_at++;
    expect(() => receiveAdvisoryOptions(f.result, f.key, f.state, f.policy, f.now)).toThrow(/incomplete alternatives review/);
  });

  it('keeps a complete empty review distinct from a selectable proposal', () => {
    const f = fixture();
    f.result.advisories = [];
    f.result.candidate_count = 0;
    const review = receiveAdvisoryOptions(f.result, f.key, f.state, f.policy, f.now);
    expect(review.advisories).toEqual([]);
    expect(() => selectAdvisoryOption(review, 'anything', f.state, f.policy, f.now)).toThrow(/current native review/);
  });
});
