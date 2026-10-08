export interface Aircraft {
  aircraft_id: string; x_nm: number; y_nm: number; altitude_ft: number;
  vx_nm_min: number; vy_nm_min: number; climb_ft_min: number;
}
export interface WorldState { version: number; observed_at: number; aircraft: Aircraft[] }
export interface SafetyPolicy {
  min_horizontal_nm: number; min_vertical_ft: number; horizon_min: number;
  sample_step_min: number; max_state_age_sec: number; max_speed_nm_min: number;
  max_climb_ft_min: number;
}
export const DEFAULT_POLICY: SafetyPolicy = { min_horizontal_nm:5,min_vertical_ft:1000,horizon_min:5,sample_step_min:0.5,max_state_age_sec:10,max_speed_nm_min:6,max_climb_ft_min:3000 };
export type Interval = readonly [number,number];
const INTEGER_KEYS=new Set(['version','seq']);
export function canonicalJson(value:unknown,key=''):string {
  if(value===null) return 'null';
  if(typeof value==='string'||typeof value==='boolean') return JSON.stringify(value);
  if(typeof value==='number') {
    if(!Number.isFinite(value)) throw new Error('TowerOps state must be finite');
    if(Object.is(value,-0)) return INTEGER_KEYS.has(key)?'0':'-0.0';
    if(!INTEGER_KEYS.has(key)) {
      // Python json uses float repr: scientific outside [1e-4, 1e16),
      // with an explicit sign and at least two exponent digits.
      const [mantissa,exponentText]=value.toExponential().split('e');
      const exponent=Number(exponentText);
      if(exponent < -4 || exponent >= 16)
        return `${mantissa}e${exponent<0?'-':'+'}${Math.abs(exponent).toString().padStart(2,'0')}`;
      if(Number.isInteger(value)) return `${value}.0`;
    }
    return JSON.stringify(value);
  }
  if(Array.isArray(value)) return `[${value.map(v=>canonicalJson(v,key)).join(',')}]`;
  if(typeof value==='object') { const o=value as Record<string,unknown>; return `{${Object.keys(o).sort().map(k=>`${JSON.stringify(k)}:${canonicalJson(o[k],k)}`).join(',')}}`; }
  throw new Error('Unsupported canonical JSON value');
}
export async function hashObject(value:unknown):Promise<string> {
  const bytes=new TextEncoder().encode(canonicalJson(value));
  const digest=await globalThis.crypto.subtle.digest('SHA-256',bytes);
  return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
}
export async function worldHash(state:WorldState):Promise<string> {
  const aircraft=[...state.aircraft].sort((a,b)=>a.aircraft_id.localeCompare(b.aircraft_id));
  return hashObject({version:state.version,observed_at:state.observed_at,aircraft});
}
export function projected(a:Aircraft,minutes:number):Aircraft {
  return {...a,x_nm:a.x_nm+a.vx_nm_min*minutes,y_nm:a.y_nm+a.vy_nm_min*minutes,altitude_ft:a.altitude_ft+a.climb_ft_min*minutes};
}
export function replaceAircraft(state:WorldState,updated:Aircraft,observed_at:number):WorldState {
  return {version:state.version+1,observed_at,aircraft:state.aircraft.map(a=>a.aircraft_id===updated.aircraft_id?updated:a)};
}
export function linearAbsUnsafeInterval(offset:number,rate:number,limit:number,horizon:number):Interval|null {
  if(limit<=0||horizon<0) return null;
  if(rate===0) return Math.abs(offset)<limit?[0,horizon]:null;
  const t1=(-limit-offset)/rate,t2=(limit-offset)/rate;
  const lo=Math.max(0,Math.min(t1,t2)),hi=Math.min(horizon,Math.max(t1,t2));
  return lo<hi?[lo,hi]:null;
}
export function horizontalUnsafeInterval(dx:number,dy:number,dvx:number,dvy:number,limit:number,horizon:number):Interval|null {
  if(limit<=0||horizon<0) return null;
  const a=dvx*dvx+dvy*dvy,b=2*(dx*dvx+dy*dvy),c=dx*dx+dy*dy-limit*limit;
  if(a===0) return c<0?[0,horizon]:null;
  const disc=b*b-4*a*c; if(disc<=0) return null;
  const root=Math.sqrt(disc),r1=(-b-root)/(2*a),r2=(-b+root)/(2*a);
  const lo=Math.max(0,Math.min(r1,r2)),hi=Math.min(horizon,Math.max(r1,r2));
  return lo<hi?[lo,hi]:null;
}
export function pairConflict(a:Aircraft,b:Aircraft,policy:SafetyPolicy=DEFAULT_POLICY):boolean {
  const values=[a.x_nm,a.y_nm,a.altitude_ft,a.vx_nm_min,a.vy_nm_min,a.climb_ft_min,b.x_nm,b.y_nm,b.altitude_ft,b.vx_nm_min,b.vy_nm_min,b.climb_ft_min];
  if(values.some(v=>!Number.isFinite(v))) return true;
  const h=horizontalUnsafeInterval(a.x_nm-b.x_nm,a.y_nm-b.y_nm,a.vx_nm_min-b.vx_nm_min,a.vy_nm_min-b.vy_nm_min,policy.min_horizontal_nm,policy.horizon_min);
  if(!h) return false;
  const v=linearAbsUnsafeInterval(a.altitude_ft-b.altitude_ft,a.climb_ft_min-b.climb_ft_min,policy.min_vertical_ft,policy.horizon_min);
  return !!v&&Math.max(h[0],v[0])<Math.min(h[1],v[1]);
}
export function conflictPairs(state:WorldState,policy:SafetyPolicy=DEFAULT_POLICY):Array<[string,string]> {
  const out:Array<[string,string]>=[];
  for(let i=0;i<state.aircraft.length;i++) for(let j=i+1;j<state.aircraft.length;j++) {
    const a=state.aircraft[i]!,b=state.aircraft[j]!; if(pairConflict(a,b,policy)) out.push([a.aircraft_id,b.aircraft_id]);
  }
  return out;
}
export function conflictingAircraft(state:WorldState,policy:SafetyPolicy=DEFAULT_POLICY):Aircraft[] {
  const sorted=[...state.aircraft].sort((a,b)=>a.aircraft_id.localeCompare(b.aircraft_id));
  return sorted.filter(a=>sorted.some(b=>b.aircraft_id!==a.aircraft_id&&pairConflict(a,b,policy)));
}
