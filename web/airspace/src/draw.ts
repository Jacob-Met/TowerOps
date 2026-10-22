import {Aircraft,SafetyPolicy,WorldState,conflictPairs,horizontalUnsafeInterval,linearAbsUnsafeInterval,projected} from './core';
import { RadarFrame, RadarViewport, fitRadar, radarNumber, radarPoint, radarTicks, radarViewport } from './radar-geometry';
import { RadarClip, clipRadarSegment, insideRadarClip, radarViewCanProject } from './radar-view';
export { radarRangeLabel } from './radar-geometry';
const C={grid:'#294148',muted:'#91aaa5',safe:'#85d6c7',risk:'#f28e73',amber:'#e0bb72',ink:'#f1e9dc'};
export function drawAirspace(canvas:HTMLCanvasElement,state:WorldState,selected:string,policy:SafetyPolicy,manualFrame?:RadarFrame):RadarViewport|null{
 const r=canvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1),w=Math.max(1,r.width),h=Math.max(1,r.height);
 if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
 const ctx=canvas.getContext('2d');if(!ctx)return null;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#111f24';ctx.fillRect(0,0,w,h);
 const pad={l:64,r:28,t:24,b:40},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
 const automatic=fitRadar(state,policy),frame=automatic&&(manualFrame??automatic);
 let view=frame&&radarViewport(frame,cw,ch);
 if(manualFrame&&view&&!radarViewCanProject(view,state,policy))view=null;
 if(!view){
  ctx.fillStyle=C.amber;ctx.font='12px Consolas,monospace';ctx.fillText('RADAR VIEW UNAVAILABLE',12,Math.max(18,h/2-8),Math.max(1,w-24));
  ctx.fillStyle=C.muted;ctx.font='10px Consolas,monospace';ctx.fillText(manualFrame&&frame?'Use Auto fit or enlarge the radar.':frame?'Enlarge the radar to show traffic.':'Traffic or look-ahead coordinates cannot be drawn.',12,Math.max(34,h/2+12),Math.max(1,w-24));
  return null;
 }
 const bounds:RadarClip={left:pad.l,top:pad.t,right:pad.l+cw,bottom:pad.t+ch};
 const xy=(x:number,y:number)=>{const [px,py]=radarPoint(view,x,y);return [pad.l+px,pad.t+py] as const;};
 ctx.lineWidth=1;ctx.strokeStyle=C.grid;ctx.fillStyle=C.muted;ctx.font='9px Consolas,monospace';
 let previousLabelRight=-Infinity;
 for(const n of radarTicks(view.min_x_nm,view.max_x_nm,cw/80)){
  const [gx]=xy(n,view.center_y_nm);ctx.beginPath();ctx.moveTo(gx,pad.t);ctx.lineTo(gx,pad.t+ch);ctx.stroke();
  const label=radarNumber(n),labelWidth=ctx.measureText(label).width,x=Math.max(2,Math.min(w-labelWidth-2,gx-labelWidth/2));
  if(x>=previousLabelRight+8){ctx.fillText(label,x,pad.t+ch+14);previousLabelRight=x+labelWidth;}
 }
 for(const n of radarTicks(view.min_y_nm,view.max_y_nm,ch/60)){
  const [,gy]=xy(view.center_x_nm,n);ctx.beginPath();ctx.moveTo(pad.l,gy);ctx.lineTo(pad.l+cw,gy);ctx.stroke();
  const label=radarNumber(n);ctx.textAlign='right';ctx.fillText(label,pad.l-7,gy+3,pad.l-10);ctx.textAlign='left';
 }
 // Axes and distance reference rings remain at the actual world origin.
 ctx.save();ctx.beginPath();ctx.rect(pad.l,pad.t,cw,ch);ctx.clip();
 ctx.setLineDash([3,5]);ctx.strokeStyle='#466168';ctx.beginPath();
 if(view.min_x_nm<=0&&view.max_x_nm>=0){const [x]=xy(0,view.center_y_nm);ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+ch);}
 if(view.min_y_nm<=0&&view.max_y_nm>=0){const [,y]=xy(view.center_x_nm,0);ctx.moveTo(pad.l,y);ctx.lineTo(pad.l+cw,y);}
 ctx.stroke();ctx.setLineDash([]);
 for(const nm of [policy.min_horizontal_nm,policy.min_horizontal_nm*2]){
  if(!Number.isFinite(nm)||nm<=0||view.min_x_nm>nm||view.max_x_nm < -nm||view.min_y_nm>nm||view.max_y_nm < -nm)continue;
  const [ox,oy]=xy(0,0),radius=nm*view.scale;if(![ox,oy,radius].every(Number.isFinite))continue;
  ctx.strokeStyle='#37545a';ctx.beginPath();ctx.arc(ox,oy,radius,0,Math.PI*2);ctx.stroke();ctx.fillStyle=C.muted;ctx.fillText(nm+' NM',ox+radius+3,oy-3);
 }
 const byId=new Map(state.aircraft.map(a=>[a.aircraft_id,a]));
 for(const [aid,bid] of conflictPairs(state,policy)){
  const a=byId.get(aid)!,b=byId.get(bid)!;
  const hi=horizontalUnsafeInterval(a.x_nm-b.x_nm,a.y_nm-b.y_nm,a.vx_nm_min-b.vx_nm_min,a.vy_nm_min-b.vy_nm_min,policy.min_horizontal_nm,policy.horizon_min);
  const vi=linearAbsUnsafeInterval(a.altitude_ft-b.altitude_ft,a.climb_ft_min-b.climb_ft_min,policy.min_vertical_ft,policy.horizon_min);
  if(!hi||!vi)continue;const lo=Math.max(hi[0],vi[0]),end=Math.min(hi[1],vi[1]);if(lo>=end)continue;
  const t=(lo+end)/2,pa=projected(a,t),pb=projected(b,t),p1=xy(pa.x_nm,pa.y_nm),p2=xy(pb.x_nm,pb.y_nm),mx=manualFrame?p1[0]/2+p2[0]/2:(p1[0]+p2[0])/2,my=manualFrame?p1[1]/2+p2[1]/2:(p1[1]+p2[1])/2;
  const line=manualFrame?clipRadarSegment(p1,p2,bounds):[p1,p2];
  ctx.strokeStyle=C.risk;ctx.lineWidth=2;ctx.setLineDash([5,4]);
  if(line){ctx.beginPath();ctx.moveTo(line[0]![0],line[0]![1]);ctx.lineTo(line[1]![0],line[1]![1]);ctx.stroke();}
  ctx.setLineDash([]);if(!manualFrame||insideRadarClip([mx,my],bounds)){ctx.beginPath();ctx.arc(mx,my,9,0,Math.PI*2);ctx.stroke();}
 }
 ctx.restore();
 if(manualFrame){ctx.save();ctx.beginPath();ctx.rect(pad.l,pad.t,cw,ch);ctx.clip();}
 for(const a of state.aircraft)drawAircraft(ctx,a,xy,selected,policy.horizon_min,conflictPairs(state,policy).some(p=>p.includes(a.aircraft_id)),manualFrame?bounds:undefined);
 if(manualFrame)ctx.restore();
 ctx.fillStyle=C.muted;ctx.font='9px Consolas,monospace';ctx.fillText('EAST + / WEST - (NM)',pad.l,h-7);ctx.fillText('NORTH + / SOUTH - (NM)',pad.l,14);
 if(!state.aircraft.length){ctx.fillStyle=C.muted;ctx.font='12px Consolas,monospace';ctx.fillText('NO TRAFFIC',pad.l+12,pad.t+22);}
 return view;
}
function drawAircraft(ctx:CanvasRenderingContext2D,a:Aircraft,xy:(x:number,y:number)=>readonly [number,number],selected:string,horizon:number,risk:boolean,bounds?:RadarClip):void{
 const [x,y]=xy(a.x_nm,a.y_nm),[ex,ey]=xy(a.x_nm+a.vx_nm_min*horizon,a.y_nm+a.vy_nm_min*horizon),c=risk?C.risk:C.safe;
 const line=bounds?clipRadarSegment([x,y],[ex,ey],bounds):[[x,y],[ex,ey]];
 ctx.strokeStyle=c;ctx.lineWidth=1.5;ctx.setLineDash([5,5]);
 if(line){ctx.beginPath();ctx.moveTo(line[0]![0],line[0]![1]);ctx.lineTo(line[1]![0],line[1]![1]);ctx.stroke();}ctx.setLineDash([]);
 if(bounds&&!insideRadarClip([x,y],bounds))return;
 const angle=Math.atan2(-a.vy_nm_min,a.vx_nm_min);ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(10,0);ctx.lineTo(-7,-5);ctx.lineTo(-4,0);ctx.lineTo(-7,5);ctx.closePath();ctx.fill();ctx.restore();
 if(a.aircraft_id===selected){ctx.strokeStyle=C.amber;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,15,0,Math.PI*2);ctx.stroke();}
 ctx.fillStyle=C.ink;ctx.font='10px Consolas,monospace';ctx.fillText(a.aircraft_id,x+13,y-7);ctx.fillStyle=C.muted;ctx.font='9px Consolas,monospace';ctx.fillText(`${Math.round(a.altitude_ft/100)} x ${Math.hypot(a.vx_nm_min,a.vy_nm_min).toFixed(1)} NM/M`,x+13,y+6);
}
