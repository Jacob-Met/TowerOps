import { describe, expect, it } from 'vitest';
import reference from './python-reference.json';
import { DEFAULT_POLICY, WorldState, conflictPairs, worldHash } from '../src/core';
import { planAdvisory } from '../src/planner';
import { AuditLog } from '../src/audit';
import { applyAdvisory } from '../src/actuation';
import { Approval, Ack } from '../src/gate';
type Case={name:string;state:WorldState;world_hash:string;now:number;before_conflict:boolean;conflict_pairs:string[][];advisory:Record<string,unknown>|null;advisory_hash:string|null;after_state:WorldState|null;after_world_hash:string|null;after_conflict:boolean|null;audit_events:unknown[];audit_valid:boolean;missing_ack:{reason:string;events:unknown[];state_unchanged:boolean}|null};
const cases=(reference as unknown as {scenarios:Case[]}).scenarios;
describe('TypeScript port matches real TowerOps Python runs',()=>{
  it.each(cases)('$name',async c=>{
    expect(await worldHash(c.state)).toBe(c.world_hash);
    expect(conflictPairs(c.state)).toEqual(c.conflict_pairs);
    const plan=await planAdvisory(c.state,c.now);
    expect(plan).toEqual(c.advisory?{...c.advisory,advisory_hash:c.advisory_hash}:null);
    expect(Boolean(c.conflict_pairs.length)).toBe(c.before_conflict);
    if(!plan)return;
    const approval:Approval={advisory_hash:plan.advisory_hash,decision:'approve',approved_at:c.now+0.2,approver:'synthetic-controller'};
    const ack:Ack={advisory_hash:plan.advisory_hash,status:'accepted',acknowledged_at:c.now+0.4};
    const audit=new AuditLog(); const after=await applyAdvisory(c.state,plan,approval,ack,c.now+0.5,audit,DEFAULT_POLICY);
    expect(after).toEqual(c.after_state); expect(await worldHash(after)).toBe(c.after_world_hash);
    expect(conflictPairs(after).length>0).toBe(c.after_conflict); expect(audit.events).toEqual(c.audit_events); expect(await audit.verify()).toBe(c.audit_valid);
    const denied=new AuditLog(); await expect(applyAdvisory(c.state,plan,approval,null,c.now+0.5,denied)).rejects.toMatchObject({reason:c.missing_ack?.reason});
    expect(denied.events).toEqual(c.missing_ack?.events); expect(c.missing_ack?.state_unchanged).toBe(true);
  });
});
