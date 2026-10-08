import { describe, expect, it, vi } from 'vitest';
import { WorldState, conflictingAircraft, worldHash } from '../src/core';
import { advisorySafe, planAdvisory } from '../src/planner';
import { parseWorldState } from '../src/world-tools';
import fixture from './identifier-parity.json';

describe('Python aircraft identifier ordering', () => {
  // The expected hashes, ordered participants and complete proposals were
  // produced by the unchanged native Python implementation, not this port.
  for (const sample of fixture.cases) {
    it(sample.name, async () => {
      const state: WorldState = structuredClone(sample.world);
      const before = JSON.stringify(state);
      if (sample.ui_callsigns) expect(parseWorldState(state)).toEqual(state);
      expect(await worldHash(state)).toBe(sample.world_hash);
      expect(conflictingAircraft(state).map(a => a.aircraft_id)).toEqual(sample.conflicting_aircraft);
      if (state.aircraft.length === 2) {
        expect(await planAdvisory(state, sample.now)).toEqual(sample.advisory);
        expect(sample.advisory).not.toBeNull();
        expect(await advisorySafe(state, sample.advisory!)).toBe(true);
      }
      expect(JSON.stringify(state)).toBe(before);
      const reversed = { ...state, aircraft: [...state.aircraft].reverse() };
      expect(await worldHash(reversed)).toBe(sample.world_hash);
      expect(conflictingAircraft(reversed).map(a => a.aircraft_id)).toEqual(sample.conflicting_aircraft);
    });
  }

  it('does not consult the process locale for identity or target selection', async () => {
    const sample = fixture.cases.find(value => value.name === 'internal punctuation')!;
    const comparison = vi.spyOn(String.prototype, 'localeCompare').mockImplementation(() => {
      throw new Error('Aircraft identity must not depend on locale collation');
    });
    try {
      expect(await worldHash(sample.world)).toBe(sample.world_hash);
      expect(await planAdvisory(sample.world, sample.now)).toEqual(sample.advisory);
    } finally {
      comparison.mockRestore();
    }
  });
});
