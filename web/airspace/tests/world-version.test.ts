import { describe, expect, it } from 'vitest';
import { parseWorldState } from '../src/world-tools';

const world = (version: unknown) => ({
  version, observed_at: 1000,
  aircraft: [{ aircraft_id: 'TEST1', x_nm: 0, y_nm: 0, altitude_ft: 10000,
    vx_nm_min: 0, vy_nm_min: 0, climb_ft_min: 0 }],
});

describe('imported world version representation', () => {
  it('refuses integers outside the JavaScript safe range', () => {
    for (const version of [Number.MAX_SAFE_INTEGER + 1, Number.MAX_SAFE_INTEGER + 2, 1e20, Number.MAX_VALUE]) {
      expect(() => parseWorldState(world(version))).toThrow(/World version/);
    }
  });

  it('refuses a JSON integer token rounded before parser admission', () => {
    const raw = JSON.stringify(world(0)).replace('"version":0', '"version":9007199254740993');
    const decoded = JSON.parse(raw);
    expect(decoded.version).toBe(9007199254740992);
    expect(() => parseWorldState(decoded)).toThrow(/World version/);
  });

  it('preserves safe boundary values and the other world fields', () => {
    for (const version of [0, -0, 1, 42, 2 ** 32, Number.MAX_SAFE_INTEGER - 1, Number.MAX_SAFE_INTEGER]) {
      const input = world(version);
      const before = structuredClone(input);
      const parsed = parseWorldState(input);
      expect(parsed.version).toBe(version);
      expect(parsed).toEqual(before);
      expect(input).toEqual(before);
    }
  });

  it('retains existing malformed-version refusals', () => {
    for (const version of [-1, 0.5, NaN, Infinity, -Infinity, '1', null, true, {}, []]) {
      expect(() => parseWorldState(world(version))).toThrow(/World version/);
    }
  });

  it('does not mutate a refused imported world', () => {
    const input = world(Number.MAX_SAFE_INTEGER + 1);
    const before = structuredClone(input);
    expect(() => parseWorldState(input)).toThrow(/World version/);
    expect(input).toEqual(before);
  });
});
