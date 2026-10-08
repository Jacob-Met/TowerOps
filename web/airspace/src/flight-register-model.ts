import type { Aircraft } from './core';

export type FlightRegisterOrder = 'scenario' | 'callsign' | 'altitude-ascending' | 'altitude-descending';
export interface FlightRegisterProjection {
  aircraft: readonly Aircraft[];
  total: number;
  selectedHidden: boolean;
}

/** A view of the existing world; it never reorders or edits the world's aircraft. */
export function projectFlightRegister(
  aircraft: readonly Aircraft[],
  query: string,
  order: FlightRegisterOrder,
  selected: string,
): FlightRegisterProjection {
  const needle = query.trim().toUpperCase();
  const rows = aircraft
    .map((flight, index) => ({ flight, index }))
    .filter(({ flight }) => flight.aircraft_id.toUpperCase().includes(needle));
  rows.sort((a, b) => {
    let compared = 0;
    if (order === 'callsign') {
      compared = a.flight.aircraft_id < b.flight.aircraft_id ? -1 : a.flight.aircraft_id > b.flight.aircraft_id ? 1 : 0;
    } else if (order === 'altitude-ascending') {
      compared = a.flight.altitude_ft - b.flight.altitude_ft;
    } else if (order === 'altitude-descending') {
      compared = b.flight.altitude_ft - a.flight.altitude_ft;
    }
    return compared || a.index - b.index;
  });
  return {
    aircraft: rows.map(row => row.flight),
    total: aircraft.length,
    selectedHidden: aircraft.some(flight => flight.aircraft_id === selected)
      && !rows.some(row => row.flight.aircraft_id === selected),
  };
}
