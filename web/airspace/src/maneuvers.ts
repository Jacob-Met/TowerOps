import { Aircraft, DEFAULT_POLICY, SafetyPolicy } from './core';
function nextDownPositive(value:number):number {
  if(value<=0) return value;
  const buf=new ArrayBuffer(8),view=new DataView(buf); view.setFloat64(0,value,false);
  view.setBigUint64(0,view.getBigUint64(0,false)-1n,false); return view.getFloat64(0,false);
}
export function maneuverCandidates(target:Aircraft,policy:SafetyPolicy=DEFAULT_POLICY):Array<[number,number,number]> {
  const out:Array<[number,number,number]>=[],seen=new Set<string>();
  const emit=(vx:number,vy:number,climb:number)=>{const k=`${vx}|${vy}|${climb}`;if(!seen.has(k)){seen.add(k);out.push([vx,vy,climb]);}};
  const speed=policy.max_speed_nm_min,vx=target.vx_nm_min;
  if(Number.isFinite(vx)&&Math.abs(vx)<=speed){
    let max=Math.sqrt(Math.max(0,speed*speed-vx*vx));
    while(Math.hypot(vx,max)>speed&&max>0) max=nextDownPositive(max);
    for(const vy of [2,-2,3,-3,0].map(v=>Math.max(-max,Math.min(max,v)))) emit(vx,vy,target.climb_ft_min);
    for(const vy of [max,-max,max/2,-max/2,max/4,-max/4]) emit(vx,vy,target.climb_ft_min);
  }
  for(const climb of [0,1000,-1000,2000,-2000,3000,-3000]) emit(target.vx_nm_min,target.vy_nm_min,climb);
  for(const dvx of [1,-1,2,-2]) emit(target.vx_nm_min+dvx,target.vy_nm_min,target.climb_ft_min);
  for(const vy of [2,-2,3,-3]) for(const climb of [0,1000,-1000,2000,-2000]) emit(target.vx_nm_min,vy,climb);
  return out;
}
