import { Aircraft, SafetyPolicy, WorldState, conflictPairs, horizontalUnsafeInterval, linearAbsUnsafeInterval, projected } from './core';
export interface FlightInput { aircraft_id:string; x_nm:number; y_nm:number; altitude_ft:number; heading_deg:number; speed_kt:number; climb_ft_min:number }
export interface ConflictWindow { aircraft_a:string; aircraft_b:string; start_min:number; end_min:number; horizontal_nm:number; vertical_ft:number }
export function createAircraft(input:FlightInput):Aircraft {
  const aircraft_id=input.aircraft_id.trim().toUpperCase();
  if(!/^[A-Z0-9_-]{1,10}$/.test(aircraft_id)) throw new Error('Use a 1-10 character callsign (letters, digits, _ or -).');
  const values=[input.x_nm,input.y_nm,input.altitude_ft,input.heading_deg,input.speed_kt,input.climb_ft_min];
  if(values.some(v=>!Number.isFinite(v))) throw new Error('Every flight field must be a finite number.');
  if(input.altitude_ft<0||input.speed_kt<0||input.speed_kt>360||Math.abs(input.climb_ft_min)>3000) throw new Error('Altitude, speed, or climb is outside the simulator envelope.');
  const rad=(((input.heading_deg%360)+360)%360)*Math.PI/180, speed=input.speed_kt/60;
  return {aircraft_id,x_nm:input.x_nm,y_nm:input.y_nm,altitude_ft:input.altitude_ft,vx_nm_min:speed*Math.sin(rad),vy_nm_min:speed*Math.cos(rad),climb_ft_min:input.climb_ft_min};
}export function parseWorldState(value:unknown):WorldState {
  if(!value||typeof value!=='object'||Array.isArray(value)) throw new Error('World JSON must be an object.');
  const world=value as Record<string,unknown>;
  if(typeof world.version!=='number'||!Number.isInteger(world.version)||world.version<0) throw new Error('World version must be a non-negative integer.');
  if(typeof world.observed_at!=='number'||!Number.isFinite(world.observed_at)) throw new Error('observed_at must be a finite timestamp in seconds.');
  if(!Array.isArray(world.aircraft)||world.aircraft.length<1||world.aircraft.length>60) throw new Error('Supply between 1 and 60 aircraft.');
  const seen=new Set<string>();
  const aircraft=world.aircraft.map((entry,index):Aircraft=>{
    if(!entry||typeof entry!=='object'||Array.isArray(entry)) throw new Error(`Aircraft ${index+1} must be an object.`);
    const item=entry as Record<string,unknown>;
    if(typeof item.aircraft_id!=='string'||!/^[A-Za-z0-9_-]{1,10}$/.test(item.aircraft_id)) throw new Error(`Aircraft ${index+1} needs a 1-10 character callsign.`);
    const aircraft_id=item.aircraft_id.toUpperCase();
    if(seen.has(aircraft_id)) throw new Error(`Duplicate callsign: ${aircraft_id}.`);
    seen.add(aircraft_id);
    const fields=['x_nm','y_nm','altitude_ft','vx_nm_min','vy_nm_min','climb_ft_min'] as const;
    for(const field of fields) if(typeof item[field]!=='number'||!Number.isFinite(item[field])) throw new Error(`${aircraft_id}.${field} must be a finite number.`);
    return {aircraft_id,x_nm:item.x_nm as number,y_nm:item.y_nm as number,altitude_ft:item.altitude_ft as number,vx_nm_min:item.vx_nm_min as number,vy_nm_min:item.vy_nm_min as number,climb_ft_min:item.climb_ft_min as number};
  });
  return {version:world.version,observed_at:world.observed_at,aircraft};
}export function conflictWindows(state:WorldState,policy:SafetyPolicy):ConflictWindow[] {
  const byId=new Map(state.aircraft.map(a=>[a.aircraft_id,a])),windows:ConflictWindow[]=[];
  for(const [aircraft_a,aircraft_b] of conflictPairs(state,policy)){
    const a=byId.get(aircraft_a),b=byId.get(aircraft_b); if(!a||!b)continue;
    const h=horizontalUnsafeInterval(a.x_nm-b.x_nm,a.y_nm-b.y_nm,a.vx_nm_min-b.vx_nm_min,a.vy_nm_min-b.vy_nm_min,policy.min_horizontal_nm,policy.horizon_min);
    const v=linearAbsUnsafeInterval(a.altitude_ft-b.altitude_ft,a.climb_ft_min-b.climb_ft_min,policy.min_vertical_ft,policy.horizon_min);
    if(!h||!v)continue; const start_min=Math.max(h[0],v[0]),end_min=Math.min(h[1],v[1]); if(start_min>=end_min)continue;
    const t=(start_min+end_min)/2,pa=projected(a,t),pb=projected(b,t);
    windows.push({aircraft_a,aircraft_b,start_min,end_min,horizontal_nm:Math.hypot(pa.x_nm-pb.x_nm,pa.y_nm-pb.y_nm),vertical_ft:Math.abs(pa.altitude_ft-pb.altitude_ft)});
  }
  return windows.sort((a,b)=>a.start_min-b.start_min||a.aircraft_a.localeCompare(b.aircraft_a));
}