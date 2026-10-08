/** Independent playback receiving controls over captured application modules.
 *
 * Node strips TypeScript syntax. Actual main/core/world-tools/audit and reference
 * JSON execute. A deliberately small DOM, canvas boundary and controlled Python
 * promise replace browser/bridge surfaces. No product source is rewritten.
 */
import assert from 'node:assert/strict';
import {readFileSync, writeFileSync} from 'node:fs';
import {resolve, dirname, relative} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash, webcrypto} from 'node:crypto';
import {stripTypeScriptTypes} from 'node:module';
import vm from 'node:vm';

const here=dirname(fileURLToPath(import.meta.url));
const args=Object.fromEntries(Array.from({length:(process.argv.length-2)/2},(_,i)=>
  [process.argv[2+i*2],process.argv[3+i*2]]));
const app=resolve(args['--app']??`${here}/baseline`);
const pinsPath=resolve(args['--pins']??`${here}/baseline-source-manifest.json`);
const output=resolve(args['--report']??`${here}/baseline-report.json`);
const pins=JSON.parse(readFileSync(pinsPath,'utf8'));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const clone=value=>JSON.parse(JSON.stringify(value));
const same=(a,b)=>assert.deepEqual(clone(a),clone(b));
const near=(actual,expected,message)=>assert.ok(Math.abs(actual-expected)<1e-6,
  `${message}: expected ${expected}, received ${actual}`);

function sourceCheck(){
  const result={};
  for(const [name,pin] of Object.entries(pins.source_before)){
    const raw=readFileSync(resolve(app,name));
    assert.equal(sha(raw),pin.sha256,`source pin changed: ${name}`);
    result[name]={bytes:raw.length,sha256:sha(raw)};
  }
  return result;
}
const before=sourceCheck();
const usedSources=new Set();
const transformed={};
function source(name){
  assert.ok(Object.hasOwn(pins.source_before,name),`unrecorded source import: ${name}`);
  usedSources.add(name);
  return readFileSync(resolve(app,name),'utf8');
}

function documentFromHtml(html){
  const elements=new Map();
  const document={activeElement:null};
  class Element {
    constructor(tag='div',id='',attributes=''){
      this.tagName=tag.toUpperCase();this.id=id;this.children=[];this.listeners=new Map();
      this.attributes=new Map();this.textContent='';this.value='';this.disabled=false;
      this.hidden=false;this.readOnly=false;this.className='';
      for(const m of attributes.matchAll(/([\w:-]+)(?:="([^"]*)"|'([^']*)'|=([^\s>]+))?/g)){
        const value=m[2]??m[3]??m[4]??'';this.attributes.set(m[1],value);
        if(m[1]==='value')this.value=value;
        if(m[1]==='disabled')this.disabled=true;
        if(m[1]==='hidden')this.hidden=true;
      }
    }
    get valueAsNumber(){return this.value===''?NaN:Number(this.value);}
    append(...nodes){this.children.push(...nodes);}
    replaceChildren(...nodes){this.children=[...nodes];this.textContent='';}
    querySelector(selector){
      assert.equal(selector,'i','unexpected presentation selector');
      return this.indicator??=new Element('i');
    }
    addEventListener(type,fn){const list=this.listeners.get(type)??[];list.push(fn);this.listeners.set(type,list);}
    toggleAttribute(name,force){
      const enabled=force??!this.attributes.has(name);
      if(enabled)this.attributes.set(name,'');else this.attributes.delete(name);
      if(name==='disabled')this.disabled=enabled;
      return enabled;
    }
    focus(){document.activeElement=this;}
  }
  for(const m of html.matchAll(/<([a-z][\w-]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)){
    assert.ok(!elements.has(m[3]),`duplicate native HTML id: ${m[3]}`);
    const node=new Element(m[1],m[3],m[2]);
    node.textContent=html.slice(m.index+m[0].length).split('<',1)[0];
    elements.set(m[3],node);
  }
  document.getElementById=id=>{
    assert.ok(elements.has(id),`native handler requested missing HTML id: ${id}`);
    return elements.get(id);
  };
  document.createElement=tag=>new Element(tag);
  return {document,Element,elements};
}

async function harness(){
  const dom=documentFromHtml(source('index.html'));
  const frames=[],draws=[],bridgeCalls=[];
  let bridgePending=null;
  const context=vm.createContext({document:dom.document,console,crypto:webcrypto,
    TextEncoder,TextDecoder,HTMLElement:dom.Element,HTMLInputElement:dom.Element,
    HTMLCanvasElement:dom.Element,HTMLTextAreaElement:dom.Element,
    window:{addEventListener(){}},requestAnimationFrame:fn=>{frames.push(fn);return frames.length;}});
  const modules=new Map();
  async function synthetic(name,values){
    const module=new vm.SyntheticModule(Object.keys(values),function(){
      for(const [key,value] of Object.entries(values))this.setExport(key,value);
    },{context,identifier:name});
    await module.link(()=>{throw new Error('synthetic boundary imported another module');});
    await module.evaluate();return module;
  }
  const outside=name=>()=>{throw new Error(`outside playback review: ${name}`);};
  const boundaries={
    '../style.css':{},
    './draw':{drawAirspace:(_canvas,state)=>draws.push(clone(state)),viewRange:()=>12},
    './track-edit':{TrackEditInput:undefined,TrackEditPreview:undefined,TrackEditSession:undefined,
      applyTrackEdit:outside('applyTrackEdit'),beginTrackEdit:outside('beginTrackEdit'),
      previewTrackEdit:outside('previewTrackEdit')},
    './planner':{Advisory:undefined},
    './gate':{Ack:undefined,Approval:undefined,GateRejected:class extends Error{
      constructor(reason){super(reason);this.reason=reason;}}},
    './python':{towerPython:request=>{
      bridgeCalls.push(clone(request));
      assert.equal(request.op,'plan','actuation is outside this review');
      assert.equal(bridgePending,null,'multiple bridge requests');
      return new Promise((resolve,reject)=>{bridgePending={resolve,reject};});
    }},
  };
  async function load(name){
    if(modules.has(name))return modules.get(name);
    const pending=(async()=>{
      if(Object.hasOwn(boundaries,name))return synthetic(name,boundaries[name]);
      if(name==='../tests/python-reference.json')
        return synthetic(name,{default:JSON.parse(source('tests/python-reference.json'))});
      const file=name==='main'?'src/main.ts':`src/${name.replace(/^\.\//,'')}.ts`;
      const raw=source(file);
      const javascript=stripTypeScriptTypes(raw,{mode:'strip',sourceUrl:pathToFileURL(resolve(app,file)).href});
      transformed[file]=sha(javascript);
      const native=new vm.SourceTextModule(javascript,{context,identifier:resolve(app,file)});
      await native.link(specifier=>load(specifier));
      await native.evaluate();
      if(name==='main')return native;
      // The application's build erases type-only imports. Node's syntax-only
      // stripper keeps their import names, so expose inert type names alongside
      // the exact native value exports. No executed value is substituted here.
      const names=[...raw.matchAll(/(?:^|\n)export\s+(?:interface|type)\s+(\w+)/g)].map(m=>m[1]);
      const values={...Object.fromEntries(Object.keys(native.namespace).map(k=>[k,native.namespace[k]]))};
      for(const name of names)if(!Object.hasOwn(values,name))values[name]=undefined;
      return synthetic(`${file}:type-erased-exports`,values);
    })();
    modules.set(name,pending);return pending;
  }
  await load('main');
  const settle=async()=>{await new Promise(resolve=>setImmediate(resolve));};
  await settle();
  const node=id=>dom.document.getElementById(id);
  async function event(id,type='click'){
    const target=node(id);assert.equal(target.disabled,false,`${id} is disabled`);
    const handlers=target.listeners.get(type)??[];
    assert.ok(handlers.length,`no native ${type} handler for ${id}`);
    for(const fn of handlers)fn({type,target,currentTarget:target,preventDefault(){}});
    await settle();
  }
  async function input(id,value){
    const target=node(id),numeric=Number(value);
    for(const [name,compare] of [['min',(x,y)=>x>=y],['max',(x,y)=>x<=y]])
      if(target.attributes.has(name))assert.ok(compare(numeric,Number(target.attributes.get(name))),
        `authored ${id} value outside native ${name}`);
    target.value=String(value);await event(id,'input');
  }
  async function frame(time){
    assert.equal(frames.length,1,'native animation scheduling changed');
    frames.shift()(time);await settle();
  }
  async function world(){await event('export-world');return JSON.parse(node('world-json').value);}
  const display=()=>({button:node('toggle-run').textContent,disabled:node('toggle-run').disabled,
    slider:node('speed-range').value,readout:node('speed-value').textContent,
    clock:node('sim-clock').textContent});
  return {node,event,input,frame,world,display,settle,bridgeCalls,draws,
    rejectBridge:async()=>{assert.ok(bridgePending,'native planner did not reach bridge');
      bridgePending.reject(new Error('independent controlled bridge rejection'));bridgePending=null;await settle();}};
}

async function advance(h,start=1000){
  await h.event('toggle-run');await h.frame(start);await h.frame(start+40);
  return h.world();
}
const controls=[];
function control(name,fn){controls.push({name,fn});}

control('native_rate_input_changes_actual_world_progression',async out=>{
  const one=await harness(),three=await harness();
  const initial=await one.world();await three.input('speed-range',3);
  const a=await advance(one),b=await advance(three);
  out.initial=initial;out.one=a;out.three=b;out.displays=[one.display(),three.display()];
  near(a.observed_at-initial.observed_at,2.4,'native one-rate clock');
  near(b.observed_at-initial.observed_at,7.2,'native maximum-rate clock');
  for(let i=0;i<initial.aircraft.length;i++){
    near(a.aircraft[i].x_nm,initial.aircraft[i].x_nm+initial.aircraft[i].vx_nm_min*0.04,'native x projection');
    near(b.aircraft[i].y_nm,initial.aircraft[i].y_nm+initial.aircraft[i].vy_nm_min*0.12,'native y projection');
  }
  assert.equal(three.display().slider,'3');assert.equal(three.display().readout,'3.0x');
});

control('manual_pause_and_resume_preserve_world_and_discard_paused_wall_time',async out=>{
  const h=await harness();const moving=await advance(h);
  await h.event('toggle-run');out.paused=h.display();
  await h.frame(5000);await h.frame(6000);out.frozen=await h.world();same(out.frozen,moving);
  await h.event('toggle-run');await h.frame(10000);const prime=await h.world();
  await h.frame(10040);const resumed=await h.world();
  out.moving=moving;out.prime=prime;out.resumed=resumed;out.final=h.display();
  assert.equal(out.paused.button,'Run traffic');assert.equal(out.final.button,'Pause traffic');
  near(prime.observed_at,moving.observed_at,'resume priming frame');
  near(resumed.observed_at-moving.observed_at,2.4,'resume uses next frame only');
});

for(const [rate,wasRunning] of [[3,false],[0.5,true]]){
  control(`reset_restores_unit_progression_from_${rate}_${wasRunning?'running':'paused'}`,async out=>{
    const h=await harness(),unit=await harness();const original=await h.world();
    await h.input('speed-range',rate);out.changed=await advance(h);
    if(!wasRunning)await h.event('toggle-run');
    await h.event('reset-world');out.reset=h.display();out.restored=await h.world();
    await h.frame(3000);await h.frame(5000);out.whilePaused=await h.world();
    out.resumed=await advance(h,7000);out.unit=await advance(unit,7000);out.final=h.display();
    same(out.restored,original);same(out.whilePaused,original);
    assert.equal(out.reset.button,'Run traffic');assert.equal(out.reset.slider,'1');
    // World progression is checked before the visible readout, so a cosmetic
    // fix cannot hide a retained internal rate from this counterexample.
    same(out.resumed,out.unit);
    assert.equal(out.reset.readout,'1.0x');assert.equal(out.final.readout,'1.0x');
  });
}

for(const [name,action] of [
  ['add_traffic',h=>h.event('add-traffic')],
  ['perturb_track',h=>h.event('perturb-track')],
  ['policy_change',h=>h.input('policy-horizon',6)],
]){
  control(`${name}_automatic_pause_updates_control_and_preserves_rate`,async out=>{
    const h=await harness();await h.input('speed-range',2);out.before=await advance(h);
    await action(h);out.paused=h.display();out.changed=await h.world();
    await h.frame(3000);await h.frame(3040);out.frozen=await h.world();
    await h.event('toggle-run');await h.frame(7000);await h.frame(7040);
    out.resumed=await h.world();out.final=h.display();
    same(out.frozen,out.changed);
    near(out.resumed.observed_at-out.changed.observed_at,4.8,'automatic pause preserves selected rate');
    assert.equal(out.paused.slider,'2');assert.equal(out.paused.readout,'2.0x');
    assert.equal(out.final.button,'Pause traffic');
    assert.equal(out.paused.button,'Run traffic','automatic pause leaves the control describing actual state');
  });
}

control('planner_pending_and_rejected_bridge_keep_pause_control_truthful',async out=>{
  const h=await harness();out.before=await advance(h);
  await h.event('run-planner');out.busy=h.display();out.requests=clone(h.bridgeCalls);
  await h.frame(3000);out.whilePending=await h.world();
  await h.rejectBridge();out.rejected=h.display();
  await h.frame(5000);out.afterRejection=await h.world();
  same(out.whilePending,out.before);same(out.afterRejection,out.before);
  assert.equal(out.requests.length,1);assert.equal(out.requests[0].op,'plan');
  assert.equal(out.busy.disabled,true);assert.equal(out.rejected.disabled,false);
  assert.equal(out.busy.button,'Run traffic','planner pauses before the controlled promise resolves');
  assert.equal(out.rejected.button,'Run traffic','bridge failure must leave a truthful paused control');
});

const results=[];
for(const {name,fn} of controls){
  const observed={};const start=performance.now();
  try{await fn(observed);results.push({name,passed:true,observed,milliseconds:performance.now()-start});
    process.stdout.write(`PASS ${name}\n`);
  }catch(error){results.push({name,passed:false,observed,error:{name:error.name,message:error.message,
      stack:error.stack},milliseconds:performance.now()-start});process.stdout.write(`FAIL ${name}: ${error.message}\n`);}
}
const after=sourceCheck();same(after,before);
const report={schema:'independent-towerops-playback-receiving.v1',label:args['--label']??'baseline',
  upstream_commit:pins.upstream_commit,upstream_tree:pins.upstream_tree,app,
  runtime:{node:process.version,executable:process.execPath,exec_arguments:process.execArgv},
  driver_sha256:sha(readFileSync(fileURLToPath(import.meta.url))),source_manifest_sha256:sha(readFileSync(pinsPath)),
  sources:before,sources_unchanged:true,used_sources:[...usedSources].sort(),transformed_sha256:transformed,
  results,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).length,
  boundaries:{dom:'Small event/value/disabled-state model populated from exact native index.html IDs and defaults.',
    native_modules:'Actual captured main.ts, core.ts, world-tools.ts and audit.ts plus actual reference JSON.',
    typescript:'Node syntax stripping with inert erased-type export names; not native tsc/Vite/Vitest qualification.',
    draw:'Canvas rendering and range presentation stubbed; actual state is read via the native export-world event.',
    python:'One controlled pending/rejected plan promise; no actual Python planner, gate or actuation claim.',
    unexercised:'Track edit and gate/apply paths are excluded; no scenario-file, numeric or audit algorithm assertion.',
    browser:'No browser, visual, layout, deployment or operational-airspace qualification.'}};
writeFileSync(output,JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify({passed:report.passed,failed:report.failed,sources_unchanged:true,report:output})+'\n');
process.exitCode=report.failed?1:0;
