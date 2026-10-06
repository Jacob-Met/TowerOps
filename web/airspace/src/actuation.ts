import { DEFAULT_POLICY, SafetyPolicy, WorldState, replaceAircraft, worldHash } from './core';
import { Advisory } from './planner';
import { Ack, Approval, GateRejected, screenBatch } from './gate';
import { AuditLog } from './audit';
const reject=(reason:string):never=>{throw new GateRejected(reason);};
export async function applyAdvisory(state:WorldState,a:Advisory,approval:Approval|null,ack:Ack|null,now:number,audit:AuditLog,policy:SafetyPolicy=DEFAULT_POLICY):Promise<WorldState> {
  await screenBatch(state,[a],now,audit,policy);
  if(!approval||approval.advisory_hash!==a.advisory_hash||approval.decision!=='approve'){await audit.append('reject',{reason:'human_approval_required',advisory_hash:a.advisory_hash});return reject('human_approval_required');}
  if(!Number.isFinite(approval.approved_at)||approval.approved_at<a.issued_at||approval.approved_at>a.expires_at||approval.approved_at>now){await audit.append('reject',{reason:'invalid_approval_time',advisory_hash:a.advisory_hash});return reject('invalid_approval_time');}
  await audit.append('approval',approval as unknown as Record<string,unknown>);
  if(!ack){await audit.append('reject',{reason:'ack_missing',advisory_hash:a.advisory_hash});return reject('ack_missing');}
  if(ack.advisory_hash!==a.advisory_hash||ack.status!=='accepted'){await audit.append('reject',{reason:'ack_invalid',advisory_hash:a.advisory_hash});return reject('ack_invalid');}
  if(!Number.isFinite(ack.acknowledged_at)||ack.acknowledged_at<approval.approved_at||ack.acknowledged_at<a.issued_at){await audit.append('reject',{reason:'invalid_ack_time',advisory_hash:a.advisory_hash});return reject('invalid_ack_time');}
  if(ack.acknowledged_at>a.expires_at||ack.acknowledged_at>now){await audit.append('reject',{reason:'ack_late',advisory_hash:a.advisory_hash});return reject('ack_late');}
  await audit.append('ack',ack as unknown as Record<string,unknown>);
  const target=state.aircraft.find(x=>x.aircraft_id===a.aircraft_id); if(!target)return reject('unknown_aircraft');
  const updated={...target,vx_nm_min:a.set_vx_nm_min,vy_nm_min:a.set_vy_nm_min,climb_ft_min:a.set_climb_ft_min};
  const next=replaceAircraft(state,updated,now);
  await audit.append('simulated_actuation',{advisory_hash:a.advisory_hash,before_world_hash:await worldHash(state),after_world_hash:await worldHash(next)});
  return next;
}
