import { SafetyPolicy, WorldState, canonicalJson } from './core';
import { Advisory } from './planner';

export interface NativeAdvisoryOptions {
  world_hash: string;
  reviewed_at: number;
  candidate_count: number;
  advisories: Advisory[];
}

export interface AdvisoryOptionsReview {
  readonly baseline_key: string;
  readonly world_hash: string;
  readonly reviewed_at: number;
  readonly candidate_count: number;
  readonly advisories: readonly Readonly<Advisory>[];
}

export function optionsSnapshotKey(state: WorldState, policy: SafetyPolicy, now: number): string {
  return canonicalJson({ state, policy, now });
}

export function optionsAreCurrent(
  review: Pick<AdvisoryOptionsReview, 'baseline_key'>,
  state: WorldState, policy: SafetyPolicy, now: number,
): boolean {
  return review.baseline_key === optionsSnapshotKey(state, policy, now);
}

export function receiveAdvisoryOptions(
  result: NativeAdvisoryOptions, requested_key: string,
  state: WorldState, policy: SafetyPolicy, now: number,
): AdvisoryOptionsReview {
  if (requested_key !== optionsSnapshotKey(state, policy, now)) {
    throw new Error('The world, clock or policy changed. Review alternatives again.');
  }
  // Validate the response contract, without substituting a browser planner or
  // recomputing Python's hashes from JavaScript float serialization.
  const hash = /^[a-f0-9]{64}$/;
  if (!result || !hash.test(result.world_hash) || result.reviewed_at !== now ||
      !Number.isSafeInteger(result.candidate_count) || result.candidate_count < 0 ||
      !Array.isArray(result.advisories) || result.advisories.length > result.candidate_count) {
    throw new Error('Python returned an incomplete alternatives review. No proposal changed.');
  }
  const seen = new Set<string>();
  for (const advisory of result.advisories) {
    if (!advisory || !hash.test(advisory.advisory_hash) || seen.has(advisory.advisory_hash) ||
        advisory.world_hash !== result.world_hash ||
        !state.aircraft.some(a => a.aircraft_id === advisory.aircraft_id) ||
        ![advisory.set_vx_nm_min, advisory.set_vy_nm_min, advisory.set_climb_ft_min].every(Number.isFinite) ||
        advisory.issued_at !== now || advisory.expires_at !== now + 8 ||
        typeof advisory.rationale !== 'string') {
      throw new Error('Python returned an incomplete alternatives review. No proposal changed.');
    }
    seen.add(advisory.advisory_hash);
  }
  return Object.freeze({
    baseline_key: requested_key,
    world_hash: result.world_hash,
    reviewed_at: result.reviewed_at,
    candidate_count: result.candidate_count,
    advisories: Object.freeze(result.advisories.map(advisory => Object.freeze({ ...advisory }))),
  });
}

export function selectAdvisoryOption(
  review: AdvisoryOptionsReview, advisory_hash: string,
  state: WorldState, policy: SafetyPolicy, now: number,
): Advisory {
  if (!optionsAreCurrent(review, state, policy, now)) {
    throw new Error('The world, clock or policy changed. Review alternatives again.');
  }
  const advisory = review.advisories.find(option => option.advisory_hash === advisory_hash);
  if (!advisory) throw new Error('Choose a proposal from the current native review.');
  // The exact reviewed native body is the only source for selection. UI row
  // text, rounded displays and caller-owned response objects are never parsed.
  return { ...advisory };
}
