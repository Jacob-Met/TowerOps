import { describe, expect, it } from 'vitest';
import { AuditLog } from '../src/audit';
import { applyAdvisory } from '../src/actuation';
import { DEFAULT_POLICY, conflictPairs } from '../src/core';
import { advisorySafe, planAdvisory } from '../src/planner';
import { ConflictWindow, createAircraft, parseWorldState } from '../src/world-tools';

describe('visitor-authored TowerOps worlds', () => {
  it('converts a visitor bearing and speed into world velocity', () => {
    const east = createAircraft({ aircraft_id:'NORTH1', x_nm:0, y_nm:0, altitude_ft:10000, heading_deg:90, speed_kt:120, climb_ft_min:0 });
    expect(east.vx_nm_min).toBeCloseTo(2);
    expect(east.vy_nm_min).toBeCloseTo(0);
  });

  it('rejects duplicate callsigns before the safety solver sees them', () => {
    const raw = { version:1, observed_at:1000, aircraft:[
      { aircraft_id:'SAME', x_nm:0, y_nm:0, altitude_ft:10000, vx_nm_min:0, vy_nm_min:1, climb_ft_min:0 },
      { aircraft_id:'same', x_nm:2, y_nm:0, altitude_ft:10000, vx_nm_min:0, vy_nm_min:-1, climb_ft_min:0 },
    ] };
    expect(() => parseWorldState(raw)).toThrow(/Duplicate callsign/);
  });

  it('solves a visitor crossing through plan, approval, readback and verified audit', async () => {
    const world = parseWorldState({ version:7, observed_at:1000, aircraft:[
      { aircraft_id:'EAST1', x_nm:-6, y_nm:0, altitude_ft:10000, vx_nm_min:1, vy_nm_min:0, climb_ft_min:0 },
      { aircraft_id:'WEST1', x_nm:6, y_nm:0, altitude_ft:10000, vx_nm_min:-1, vy_nm_min:0, climb_ft_min:0 },
    ] });
    const windows:ConflictWindow[] = (await import('../src/world-tools')).conflictWindows(world, DEFAULT_POLICY);
    expect(windows[0]?.start_min).toBeCloseTo(3.5);
    const advisory = await planAdvisory(world, world.observed_at, DEFAULT_POLICY);
    expect(advisory).not.toBeNull();
    if (!advisory) throw new Error('Expected a safe bounded advisory.');
    expect(await advisorySafe(world, advisory, DEFAULT_POLICY)).toBe(true);
    const audit = new AuditLog();
    const approval = { advisory_hash:advisory.advisory_hash, decision:'approve', approved_at:1000.2, approver:'visitor-controller' };
    const ack = { advisory_hash:advisory.advisory_hash, status:'accepted', acknowledged_at:1000.4 };
    const changed = await applyAdvisory(world, advisory, approval, ack, 1000.5, audit, DEFAULT_POLICY);
    expect(conflictPairs(changed, DEFAULT_POLICY)).toHaveLength(0);
    expect(await audit.verify()).toBe(true);
  });
});