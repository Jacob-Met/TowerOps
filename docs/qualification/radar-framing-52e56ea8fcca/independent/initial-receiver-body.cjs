
const {stripTypeScriptTypes}=require('node:module');
const crypto=require('node:crypto');
const fs=require('node:fs');
const cache=new Map();
function moduleURL(name){
 if(cache.has(name))return cache.get(name);
 const source=SOURCE[name];if(typeof source!=='string')throw Error('Unbound source '+name);
 let js=stripTypeScriptTypes(source,{mode:'strip'});
 js=js.replace(/from\s*(['"])(\.\/[^'"]+)\1/g,(_,quote,ref)=>'from '+JSON.stringify(moduleURL(ref.slice(2))));
 const url='data:text/javascript;base64,'+Buffer.from(js).toString('base64');cache.set(name,url);return url;
}
function freeze(x){if(x&&typeof x==='object'){Object.freeze(x);for(const y of Object.values(x))freeze(y);}return x;}
function canvasRun(module,state,policy,width=800,height=600){
 const before=JSON.stringify({state,policy});freeze(state);freeze(policy);
 const calls=[],strokes=[],fills=[],translates=[],stack=[];let path=[],dash=[],attrs={};
 const canvas={width:0,height:0,getBoundingClientRect:()=>({width,height,left:0,top:0,right:width,bottom:height})};
 const context=new Proxy({},{
  get(_,key){
   if(key==='canvas')return canvas;if(key==='measureText')return text=>({width:String(text).length*6});
   if(key in attrs)return attrs[key];
   return (...args)=>{
    calls.push({method:key,args});
    if(key==='save')stack.push({attrs:{...attrs},dash:[...dash]});
    else if(key==='restore'){const saved=stack.pop();if(saved){attrs=saved.attrs;dash=saved.dash;}}
    else if(key==='setLineDash')dash=[...args[0]];
    else if(key==='beginPath')path=[];
    else if(key==='moveTo'||key==='lineTo'||key==='arc'||key==='rect'){
     if(key==='arc'&&args[2]<0)throw Error('Negative Canvas arc radius');
     path.push({method:key,args});
    }else if(key==='stroke')strokes.push({path:path.map(x=>({...x,args:[...x.args]})),style:attrs.strokeStyle,dash:[...dash],lineWidth:attrs.lineWidth});
    else if(key==='fillText')fills.push({text:String(args[0]),x:args[1],y:args[2],style:attrs.fillStyle});
    else if(key==='translate')translates.push({x:args[0],y:args[1]});
   };
  },
  set(_,key,value){attrs[key]=value;return true;}
 });
 canvas.getContext=()=>context;
 module.drawAirspace(canvas,state,'A',policy);
 const finite=calls.every(c=>c.args.every(x=>typeof x!=='number'||Number.isFinite(x)));
 const unchanged=JSON.stringify({state,policy})===before;
 return {calls,strokes,fills,markers:translates,finite,unchanged,width,height,
  label:typeof module.radarRangeLabel==='function'?module.radarRangeLabel(state,policy):null};
}
function aircraft(id,x,y,vx=0,vy=0,altitude=10000){return{aircraft_id:id,x_nm:x,y_nm:y,altitude_ft:altitude,vx_nm_min:vx,vy_nm_min:vy,climb_ft_min:0};}
function world(aircraft){return{version:4,observed_at:1234,aircraft};}
const policy={min_horizontal_nm:5,min_vertical_ft:1000,horizon_min:5,sample_step_min:.5,max_state_age_sec:10,max_speed_nm_min:6,max_climb_ft_min:3000};
function translated(w,dx,dy){return{...w,aircraft:w.aircraft.map(a=>({...a,x_nm:a.x_nm+dx,y_nm:a.y_nm+dy}))};}
const close=(a,b,t=1e-7)=>Math.abs(a-b)<=t*Math.max(1,Math.abs(a),Math.abs(b));
function assert(x,message){if(!x)throw Error(message);}
(async()=>{
 globalThis.window={devicePixelRatio:1};
 const module=await import(moduleURL('draw'));
 const results=[];
 function check(name,fn){try{const detail=fn();results.push({name,passed:true,detail});}catch(e){results.push({name,passed:false,error:String(e.message)});}}
 const near=world([aircraft('A',-2,1,0,0,10000),aircraft('B',2,1,0,0,13000)]);
 check('Equal translations retain each actual marker position',()=>{
  const ref=canvasRun(module,structuredClone(near),{...policy}),samples=[];
  assert(ref.markers.length===2,'Two rendered markers');
  for(const [dx,dy] of [[1000,-500],[-1200,800],[37,21]]){
   const r=canvasRun(module,translated(near,dx,dy),{...policy});assert(r.markers.length===2,'Two translated markers');
   assert(r.unchanged&&r.finite,'Finite read-only translated draw');
   const delta=r.markers.map((p,i)=>Math.hypot(p.x-ref.markers[i].x,p.y-ref.markers[i].y));samples.push({dx,dy,delta});
   assert(delta.every(d=>d<1e-6),'Translation changes positions: '+JSON.stringify(samples));
  }return samples;
 });
 check('Traffic ordering does not alter per-ID screen positions',()=>{
  const ref=canvasRun(module,structuredClone(near),{...policy}),r=canvasRun(module,world([...near.aircraft].reverse().map(a=>({...a}))),{...policy});
  assert(ref.markers.every((p,i)=>close(p.x,r.markers[1-i].x)&&close(p.y,r.markers[1-i].y)),'Ordering changed geometry');return true;
 });
 check('East/right, north/up and equal-axis scale survive a translated scene',()=>{
  const s=world([aircraft('A',100,200,0,0,10000),aircraft('B',104,200,0,0,13000),aircraft('C',100,204,0,0,16000)]);
  const r=canvasRun(module,s,{...policy});assert(r.markers.length===3,'Three rendered markers');
  const [a,b,c]=r.markers;assert(b.x>a.x&&close(b.y,a.y)&&c.y<a.y&&close(c.x,a.x),'Directional mapping changed');
  assert(close(b.x-a.x,a.y-c.y),'Anisotropic scale');assert(r.unchanged&&r.finite,'Finite immutable source');return {east:b.x-a.x,north:a.y-c.y};
 });
 check('Every current position and authored look-ahead endpoint stays visible',()=>{
  const s=world([aircraft('A',1000,500,-4,3,10000),aircraft('B',1004,503,5,-2,14000)]);
  const r=canvasRun(module,s,{...policy},390,500),paths=r.strokes.filter(p=>p.dash.length===2&&p.dash[0]===5&&p.dash[1]===5);
  assert(paths.length===2,'Two real trajectory strokes');
  const points=paths.flatMap(p=>p.path.filter(x=>x.method==='moveTo'||x.method==='lineTo').map(x=>x.args));
  assert(points.length===4,'Both path endpoints recorded');assert(points.every(([x,y])=>x>=0&&x<=r.width&&y>=0&&y<=r.height),'Projected endpoint outside canvas');
  assert(r.finite&&r.unchanged,'Finite immutable projection');return points;
 });
 check('Absolute tick text matches the world coordinates of its grid line',()=>{
  const s=world([aircraft('A',100,200,0,0,10000),aircraft('B',104,200,0,0,14000)]),r=canvasRun(module,s,{...policy});
  const [a,b]=r.markers,scale=(b.x-a.x)/4;assert(scale>0,'Positive reference scale');
  const lines=r.strokes.filter(p=>p.style==='#294148').map(p=>p.path.filter(x=>x.method==='moveTo'||x.method==='lineTo')).filter(p=>p.length===2);
  const grid=lines.map(([p,q])=>{const [x,y]=p.args,[u,v]=q.args;return close(x,u)?{axis:'x',pixel:x,value:100+(x-a.x)/scale}:close(y,v)?{axis:'y',pixel:y,value:200+(a.y-y)/scale}:null;}).filter(Boolean);
  const labels=r.fills.filter(x=>x.text.trim()!==''&&Number.isFinite(Number(x.text)));
  let axes=new Set();const wrong=[];
  for(const label of labels){
   const value=Number(label.text),matches=grid.filter(g=>close(value,g.value,1e-6)&&Math.abs((g.axis==='x'?label.x:label.y)-g.pixel)<=15);
   if(matches.length)matches.forEach(g=>axes.add(g.axis));else wrong.push(label);
  }
  assert(labels.length>=2&&axes.has('x')&&axes.has('y'),'No bound absolute ticks for both axes');
  assert(wrong.length===0,'Incorrect coordinate labels '+JSON.stringify(wrong));return {labels:labels.length,axes:[...axes]};
 });
 check('Range rings refer to the true world origin after recentering',()=>{
  const s=world([aircraft('A',0,0,0,0,10000),aircraft('B',6,2,0,0,14000)]),r=canvasRun(module,s,{...policy}),origin=r.markers[0];
  const arcs=r.strokes.filter(p=>p.style==='#37545a').flatMap(p=>p.path.filter(x=>x.method==='arc'));
  assert(arcs.length>0,'Visible origin range rings retained');
  assert(arcs.every(a=>close(a.args[0],origin.x)&&close(a.args[1],origin.y)),'Ring is attached to view center rather than world origin');return {origin,arcs:arcs.map(x=>x.args.slice(0,3))};
 });
 check('Empty, single and coincident traffic have finite bounded drawing',()=>{
  const cases=[world([]),world([aircraft('A',1000,-2000)]),world([aircraft('A',1000,-2000,0,0,10000),aircraft('B',1000,-2000,0,0,14000)])];
  const detail=[];for(const s of cases){const r=canvasRun(module,s,{...policy});assert(r.finite&&r.unchanged,'Invalid degenerate geometry');assert(r.markers.every(p=>p.x>=0&&p.x<=800&&p.y>=0&&p.y<=600),'Degenerate marker outside view');detail.push({markers:r.markers,label:r.label});}return detail;
 });
 check('Finite overflow becomes an explicit unavailable view with no invalid Canvas coordinates',()=>{
  const s=world([aircraft('A',1.5e308,1e308,5e307,5e307)]),r=canvasRun(module,s,{...policy});
  assert(r.finite&&r.unchanged,'Nonfinite Canvas command or source mutation');
  assert(r.markers.length===0,'Overflow plotted as an invented marker');
  assert(/unavailable|cannot|too large/i.test([r.label,...r.fills.map(x=>x.text)].join(' ')),'No explicit unavailable state');return {label:r.label,text:r.fills.map(x=>x.text)};
 });
 check('A collapsed canvas cannot produce a negative-radius or invalid draw',()=>{
  const r=canvasRun(module,structuredClone(near),{...policy},1,1);assert(r.finite&&r.unchanged,'Invalid collapsed draw');return {markers:r.markers.length,label:r.label};
 });
 console.log(JSON.stringify({schema:'towerops-independent-canvas-commands/1',source:PIN,source_sha256:Object.fromEntries(Object.entries(SOURCE).map(([k,v])=>[k,crypto.createHash('sha256').update(v).digest('hex')])),runtime:process.version,passed:results.filter(x=>x.passed).length,failed:results.filter(x=>!x.passed).length,results},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
