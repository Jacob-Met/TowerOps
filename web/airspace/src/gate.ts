import { Advisory, advisorySafe } from './planner';
import { DEFAULT_POLICY, SafetyPolicy, WorldState, worldHash } from './core';
import { AuditLog } from './audit';
export interface Approval { advisory_hash:string; decision:string; approved_at:number; approver:string }
export interface Ack { advisory_hash:string; status:string; acknowledged_at:number }
export class GateRejected extends Error { constructor(public reason:string){super(reason);this.name='GateRejected';} }
const reject=(reason:string):never=>{throw new GateRejected(reason);};
export async function screenBatch(state:WorldState,advisories:Advisory[],now:number,audit:AuditLog,policy:SafetyPolicy=DEFAULT_POLICY):Promise<string[]> {
  if(!Number.isFinite(state.observed_at)||!Number.isFinite(now)){await audit.append('reject',{reason:'invalid_state_time'});return reject('invalid_state_time');}
  if(state.observed_at>now){await audit.append('reject',{reason:'future_state',world_hash:await worldHash(state)});return reject('future_state');}
  if(now-state.observed_at>policy.max_state_age_sec){await audit.append('reject',{reason:'stale_state',world_hash:await worldHash(state)});return reject('stale_state');}
  const byAircraft=new Map<string,Set<string>>();
  for(const a of advisories){const set=byAircraft.get(a.aircraft_id)??new Set<string>();set.add(a.advisory_hash);byAircraft.set(a.aircraft_id,set);}
  if([...byAircraft.values()].some(s=>s.size>1)){await audit.append('reject',{reason:'conflicting_recommendations',world_hash:await worldHash(state)});return reject('conflicting_recommendations');}
  const hashes:string[]=[];
  for(const a of advisories){
    if(!Number.isFinite(a.issued_at)||!Number.isFinite(a.expires_at)||a.issued_at<state.observed_at||a.issued_at>now||a.expires_at<a.issued_at){await audit.append('reject',{reason:'invalid_advisory_time',advisory_hash:a.advisory_hash});return reject('invalid_advisory_time');}
    if(a.world_hash!==await worldHash(state)){await audit.append('reject',{reason:'world_hash_mismatch',advisory_hash:a.advisory_hash});return reject('world_hash_mismatch');}
    if(now>a.expires_at){await audit.append('reject',{reason:'expired_advisory',advisory_hash:a.advisory_hash});return reject('expired_advisory');}
    if(!await advisorySafe(state,a,policy)){await audit.append('reject',{reason:'unsafe_advisory',advisory_hash:a.advisory_hash});return reject('unsafe_advisory');}
    hashes.push(a.advisory_hash);
  }
  await audit.append('screen_pass',{world_hash:await worldHash(state),advisory_hashes:hashes}); return hashes;
}
