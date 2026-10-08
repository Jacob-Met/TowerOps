import { describe, expect, it } from 'vitest';
import type { Aircraft } from '../src/core';
import { projectFlightRegister } from '../src/flight-register-model';

const flight = (aircraft_id: string, altitude_ft: number): Aircraft => ({
  aircraft_id, altitude_ft, x_nm: 0, y_nm: 0, vx_nm_min: 1, vy_nm_min: -2, climb_ft_min: 0,
});
const ids = (value: ReturnType<typeof projectFlightRegister>) => value.aircraft.map(a => a.aircraft_id);

describe('live flight register projection', () => {
  const input = [flight('ZED_2', 13000), flight('ALPHA-9', 9000), flight('ALPHA-1', 13000), flight('BRAVO', 9000)];
  it('keeps the default scenario order and original flight objects', () => {
    const frozen = Object.freeze(input.map(a => Object.freeze({ ...a })));
    const view = projectFlightRegister(frozen, '', 'scenario', 'ZED_2');
    expect(ids(view)).toEqual(['ZED_2', 'ALPHA-9', 'ALPHA-1', 'BRAVO']);
    expect(view.aircraft[0]).toBe(frozen[0]);
    expect(view.total).toBe(4);
    expect(view.selectedHidden).toBe(false);
  });
  it('matches callsigns literally and case-insensitively with outer whitespace ignored', () => {
    expect(ids(projectFlightRegister(input, '  aLpHa-  ', 'scenario', 'ZED_2'))).toEqual(['ALPHA-9', 'ALPHA-1']);
    expect(ids(projectFlightRegister(input, '_', 'scenario', 'ZED_2'))).toEqual(['ZED_2']);
    for (const query of ['.*', '[A-Z]', '<img>', '13000', 'ALPHA -']) {
      expect(ids(projectFlightRegister(input, query, 'scenario', 'ZED_2'))).toEqual([]);
    }
  });
  it('orders callsigns without changing the world array or its data', () => {
    const before = JSON.stringify(input);
    expect(ids(projectFlightRegister(input, '', 'callsign', 'BRAVO'))).toEqual(['ALPHA-1', 'ALPHA-9', 'BRAVO', 'ZED_2']);
    expect(JSON.stringify(input)).toBe(before);
  });
  it('orders exact altitude while retaining scenario order for equal altitudes', () => {
    expect(ids(projectFlightRegister(input, '', 'altitude-ascending', 'BRAVO'))).toEqual(['ALPHA-9', 'BRAVO', 'ZED_2', 'ALPHA-1']);
    expect(ids(projectFlightRegister(input, '', 'altitude-descending', 'BRAVO'))).toEqual(['ZED_2', 'ALPHA-1', 'ALPHA-9', 'BRAVO']);
    const roundedTie = [flight('HIGH', 10049), flight('LOW', 10001)];
    expect(ids(projectFlightRegister(roundedTie, '', 'altitude-ascending', 'HIGH'))).toEqual(['LOW', 'HIGH']);
  });
  it('reports a filtered-out selection without choosing a replacement', () => {
    const hidden = projectFlightRegister(input, 'alpha', 'callsign', 'BRAVO');
    expect(ids(hidden)).toEqual(['ALPHA-1', 'ALPHA-9']);
    expect(hidden.selectedHidden).toBe(true);
    expect(projectFlightRegister(input, 'alpha', 'callsign', 'ALPHA-9').selectedHidden).toBe(false);
    expect(projectFlightRegister(input, 'alpha', 'callsign', 'REMOVED').selectedHidden).toBe(false);
  });
  it('handles empty matches and a replaced empty input without inventing a selection', () => {
    expect(projectFlightRegister(input, 'MISSING', 'scenario', 'BRAVO')).toEqual({aircraft: [], total: 4, selectedHidden: true});
    expect(projectFlightRegister([], 'MISSING', 'scenario', 'BRAVO')).toEqual({aircraft: [], total: 0, selectedHidden: false});
  });
  it('uses current flight data when a scenario changes', () => {
    const changed = [flight('ZED_2', 8000), flight('ALPHA-1', 13000), flight('NEW', 12000)];
    expect(ids(projectFlightRegister(changed, '', 'altitude-ascending', 'BRAVO'))).toEqual(['ZED_2', 'NEW', 'ALPHA-1']);
    expect(projectFlightRegister(changed, '', 'scenario', 'BRAVO').selectedHidden).toBe(false);
  });
  it('projects all 60 supported flights while preserving their exact source sequence', () => {
    const world = Array.from({length: 60}, (_,i) => flight('FLT'+String((i*17)%60).padStart(2,'0'), 10000+((i*17)%5)*1000));
    const before = JSON.stringify(world);
    const filtered = projectFlightRegister(world, 'flt0', 'callsign', 'FLT59');
    expect(ids(filtered)).toEqual(['FLT00','FLT01','FLT02','FLT03','FLT04','FLT05','FLT06','FLT07','FLT08','FLT09']);
    expect(filtered.total).toBe(60);
    expect(filtered.selectedHidden).toBe(true);
    expect(ids(projectFlightRegister(world, '', 'callsign', 'FLT59'))).toEqual(Array.from({length:60},(_,i)=>'FLT'+String(i).padStart(2,'0')));
    expect(JSON.stringify(world)).toBe(before);
  });
});
