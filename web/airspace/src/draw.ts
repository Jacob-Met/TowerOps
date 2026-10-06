import {Aircraft,SafetyPolicy,WorldState,conflictPairs,horizontalUnsafeInterval,linearAbsUnsafeInterval,projected} from './core';
const C={grid:'#294148',muted:'#91aaa5',safe:'#85d6c7',risk:'#f28e73',amber:'#e0bb72',ink:'#f1e9dc'};
export function drawAirspace(canvas:HTMLCanvasElement,state:WorldState,selected:string,policy:SafetyPolicy):void{
 const r=canvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1),w=Math.max(1,r.width),h=Math.max(1,r.height);
 if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
 const ctx=canvas.getContext('2d');if(!ctx)return;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#111f24';ctx.fillRect(0,0,w,h);
 const pad={l:34,r:18,t:18,b:26},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b,range=viewRange(state,policy),scale=Math.min(cw,ch)/(range*2),cx=pad.l+cw/2,cy=pad.t+ch/2;
 const xy=(x:number,y:number)=>[cx+x*scale,cy-y*scale] as const;
 ctx.lineWidth=1;ctx.strokeStyle=C.grid;ctx.fillStyle=C.muted;ctx.font='9px Consolas,monospace';
 const gridStep=Math.max(5,Math.ceil(range/20)*5);for(let n=-range;n<=range;n+=gridStep){const [gx]=xy(n,0),[,gy]=xy(0,n);ctx.beginPath();ctx.moveTo(gx,pad.t);ctx.lineTo(gx,pad.t+ch);ctx.stroke();ctx.beginPath();ctx.moveTo(pad.l,gy);ctx.lineTo(pad.l+cw,gy);ctx.stroke();if(n!==0){ctx.fillText(String(n),gx+3,cy+12);ctx.fillText(String(-n),cx+5,gy-3);}}
 ctx.setLineDash([3,5]);ctx.strokeStyle='#466168';ctx.beginPath();ctx.moveTo(cx,pad.t);ctx.lineTo(cx,pad.t+ch);ctx.moveTo(pad.l,cy);ctx.lineTo(pad.l+cw,cy);ctx.stroke();ctx.setLineDash([]);
 for(const nm of [policy.min_horizontal_nm,policy.min_horizontal_nm*2]){ctx.strokeStyle='#37545a';ctx.beginPath();ctx.arc(cx,cy,nm*scale,0,Math.PI*2);ctx.stroke();ctx.fillStyle=C.muted;ctx.fillText(`${nm} NM`,cx+nm*scale+3,cy-3);}
 const byId=new Map(state.aircraft.map(a=>[a.aircraft_id,a]));
 for(const [aid,bid] of conflictPairs(state,policy)){
  const a=byId.get(aid)!,b=byId.get(bid)!;
  const hi=horizontalUnsafeInterval(a.x_nm-b.x_nm,a.y_nm-b.y_nm,a.vx_nm_min-b.vx_nm_min,a.vy_nm_min-b.vy_nm_min,policy.min_horizontal_nm,policy.horizon_min);
  const vi=linearAbsUnsafeInterval(a.altitude_ft-b.altitude_ft,a.climb_ft_min-b.climb_ft_min,policy.min_vertical_ft,policy.horizon_min);
  if(!hi||!vi)continue;const lo=Math.max(hi[0],vi[0]),end=Math.min(hi[1],vi[1]);if(lo>=end)continue;
  const t=(lo+end)/2,pa=projected(a,t),pb=projected(b,t),p1=xy(pa.x_nm,pa.y_nm),p2=xy(pb.x_nm,pb.y_nm),mx=(p1[0]+p2[0])/2,my=(p1[1]+p2[1])/2;
  ctx.strokeStyle=C.risk;ctx.lineWidth=2;ctx.setLineDash([5,4]);ctx.beginPath();ctx.moveTo(p1[0],p1[1]);ctx.lineTo(p2[0],p2[1]);ctx.stroke();ctx.setLineDash([]);ctx.beginPath();ctx.arc(mx,my,9,0,Math.PI*2);ctx.stroke();
 }
 for(const a of state.aircraft)drawAircraft(ctx,a,xy,selected,policy.horizon_min,conflictPairs(state,policy).some(p=>p.includes(a.aircraft_id)));
 ctx.fillStyle=C.muted;ctx.font='9px Consolas,monospace';ctx.fillText('EAST / WEST',pad.l+4,h-7);ctx.fillText('NORTH',w-55,pad.t+10);
}
export function viewRange(state:WorldState,policy:SafetyPolicy):number{const extent=Math.max(12,...state.aircraft.flatMap(a=>{const end=projected(a,policy.horizon_min);return [Math.abs(a.x_nm),Math.abs(a.y_nm),Math.abs(end.x_nm),Math.abs(end.y_nm)];}));return Math.ceil((extent+2)/5)*5;}
function drawAircraft(ctx:CanvasRenderingContext2D,a:Aircraft,xy:(x:number,y:number)=>readonly [number,number],selected:string,horizon:number,risk:boolean):void{
 const [x,y]=xy(a.x_nm,a.y_nm),[ex,ey]=xy(a.x_nm+a.vx_nm_min*horizon,a.y_nm+a.vy_nm_min*horizon),c=risk?C.risk:C.safe;
 ctx.strokeStyle=c;ctx.lineWidth=1.5;ctx.setLineDash([5,5]);ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(ex,ey);ctx.stroke();ctx.setLineDash([]);
 const angle=Math.atan2(-a.vy_nm_min,a.vx_nm_min);ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(10,0);ctx.lineTo(-7,-5);ctx.lineTo(-4,0);ctx.lineTo(-7,5);ctx.closePath();ctx.fill();ctx.restore();
 if(a.aircraft_id===selected){ctx.strokeStyle=C.amber;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,15,0,Math.PI*2);ctx.stroke();}
 ctx.fillStyle=C.ink;ctx.font='10px Consolas,monospace';ctx.fillText(a.aircraft_id,x+13,y-7);ctx.fillStyle=C.muted;ctx.font='9px Consolas,monospace';ctx.fillText(`${Math.round(a.altitude_ft/100)} x ${Math.hypot(a.vx_nm_min,a.vy_nm_min).toFixed(1)} NM/M`,x+13,y+6);
}
