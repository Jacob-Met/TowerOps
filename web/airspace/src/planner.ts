import { Aircraft, DEFAULT_POLICY, SafetyPolicy, WorldState, conflictingAircraft, pairConflict, worldHash, hashObject } from './core';
import { maneuverCandidates } from './maneuvers';
export interface AdvisoryBody {
  aircraft_id:string; world_hash:string; set_vx_nm_min:number; set_vy_nm_min:number;
  set_climb_ft_min:number; issued_at:number; expires_at:number; rationale:string;
}
export type Advisory=AdvisoryBody&{advisory_hash:string};
export async function advisorySafe(state:WorldState,a:AdvisoryBody,policy:SafetyPolicy=DEFAULT_POLICY):Promise<boolean> {
  if(a.world_hash!==await worldHash(state)) return false;
  if(Math.hypot(a.set_vx_nm_min,a.set_vy_nm_min)>policy.max_speed_nm_min||Math.abs(a.set_climb_ft_min)>policy.max_climb_ft_min) return false;
  const target=state.aircraft.find(x=>x.aircraft_id===a.aircraft_id); if(!target) return false;
  const candidate={...target,vx_nm_min:a.set_vx_nm_min,vy_nm_min:a.set_vy_nm_min,climb_ft_min:a.set_climb_ft_min};
  return state.aircraft.every(other=>other.aircraft_id===candidate.aircraft_id||!pairConflict(candidate,other,policy));
}
export async function planAdvisory(state:WorldState,now:number,policy:SafetyPolicy=DEFAULT_POLICY):Promise<Advisory|null> {
  if(!state.aircraft.some((a,i)=>state.aircraft.slice(i+1).some(b=>pairConflict(a,b,policy)))) return null;
  const targets=[...conflictingAircraft(state,policy)].reverse(),hash=await worldHash(state);
  for(const target of targets) for(const [vx,vy,climb] of maneuverCandidates(target,policy)) {
    const body:AdvisoryBody={aircraft_id:target.aircraft_id,world_hash:hash,set_vx_nm_min:vx,set_vy_nm_min:vy,set_climb_ft_min:climb,issued_at:now,expires_at:now+8,rationale:'synthetic projected-separation recovery'};
    if(await advisorySafe(state,body,policy)) return {...body,advisory_hash:await hashObject(body)};
  }
  return null;
}
