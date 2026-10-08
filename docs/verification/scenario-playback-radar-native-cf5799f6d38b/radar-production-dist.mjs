import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import http from 'node:http';
import puppeteer from '/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
const argv = process.argv.slice(2), option = name => argv[argv.indexOf(name) + 1];
for (const name of ['--repo','--manifest','--build-manifest','--base-commit','--source-tree','--out']) {
 if (!argv.includes(name) || !option(name)) throw new Error(name+' is required');
}
const source=path.resolve(option('--repo')),web=path.join(source,'web/airspace'),out=path.resolve(option('--out'));
const dist=path.resolve(argv.includes('--dist')?option('--dist'):path.join(web,'dist'));
if (fs.existsSync(out)) throw new Error('Refusing an existing output directory');
assert.match(option('--base-commit'),/^[0-9a-f]{40}$/);assert.match(option('--source-tree'),/^[0-9a-f]{40}$/);
const digest=b=>({bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')});
fs.mkdirSync(out,{recursive:true});
const sourceManifestBytes=fs.readFileSync(option('--manifest')),sourceManifest=JSON.parse(sourceManifestBytes);
const buildManifestBytes=fs.readFileSync(option('--build-manifest')),buildManifest=JSON.parse(buildManifestBytes);
assert.equal(sourceManifest.tree,option('--source-tree'));assert.equal(sourceManifest.base_commit,option('--base-commit'));
const binding={source_before:Object.fromEntries(sourceManifest.files.map(entry=>[entry.path,entry.sha256]))};
const snapshot=()=>Object.fromEntries(Object.keys(binding.source_before).map(p=>{
 const file=path.resolve(source,p);assert.ok(file.startsWith(source+path.sep),'Source path escapes receiving root');
 return[p,digest(fs.readFileSync(file)).sha256];
}));
const buildSnapshot=()=>Object.fromEntries(buildManifest.files.map(entry=>{
 const file=path.resolve(dist,entry.path);assert.ok(file.startsWith(dist+path.sep),'Build path escapes receiving root');
 const actual=digest(fs.readFileSync(file));assert.equal(actual.sha256,entry.sha256,entry.path);assert.equal(actual.bytes,entry.bytes,entry.path);
 return[entry.path,actual];
}));
const report={schema:'towerops-radar-owner-predicates-production-dist-receiving/1',base_commit:option('--base-commit'),source_tree:option('--source-tree'),started_at:new Date().toISOString(),boundary:'The exact nineteen owner browser predicates against the frozen normal production build. Native Canvas observation forwards each original drawing call. Real app handlers and self-hosted CPython run unchanged; no public deployment claim.',source_manifest:digest(sourceManifestBytes),build_manifest:digest(buildManifestBytes),receiver:digest(fs.readFileSync(new URL(import.meta.url))),source_before:snapshot(),build_before:buildSnapshot(),checks:[],captures:{},python_resources:{},page_errors:[],request_failures:[]};
assert.deepEqual(report.source_before,binding.source_before);
const check=(name,condition,details)=>{report.checks.push({name,passed:!!condition,...(details===undefined?{}:{details})});assert.ok(condition,name)};
const pythonNames=new Set(['towerops.py','advisory_options.py','audit_replay.py','decision_trace.py','pyodide.mjs','pyodide.asm.js','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json']);
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.wasm':'application/wasm','.zip':'application/zip','.png':'image/png','.py':'text/plain'};
const nativeServer=http.createServer((req,res)=>{
 try{
  const url=new URL(req.url,'http://127.0.0.1'),file=path.resolve(dist,'.'+(url.pathname==='/'?'/index.html':decodeURIComponent(url.pathname)));
  if(!file.startsWith(dist+path.sep)||!fs.statSync(file).isFile()){res.writeHead(404);res.end('not found');return;}
  const bytes=fs.readFileSync(file),name=path.basename(file);
  if(url.pathname.startsWith('/python/')&&pythonNames.has(name))report.python_resources[name]={source:file,...digest(bytes)};
  res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});res.end(bytes);
 }catch{res.writeHead(404);res.end('not found');}
});
const server={httpServer:nativeServer,listen:()=>new Promise(resolve=>nativeServer.listen(0,'127.0.0.1',resolve)),close:()=>new Promise(resolve=>{nativeServer.closeAllConnections();nativeServer.close(resolve);})};
await server.listen();
const base='http://127.0.0.1:'+server.httpServer.address().port,profile=path.join(out,'profile');
let browser;
try{
 browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,userDataDir:profile,args:['--no-first-run','--no-default-browser-check','--disable-background-networking']});
 report.browser=await browser.version();report.node=process.version;
 const page=await browser.newPage();await page.setViewport({width:1440,height:1000,deviceScaleFactor:1});
 page.on('pageerror',e=>report.page_errors.push(String(e)));page.on('requestfailed',r=>report.request_failures.push({url:r.url(),error:r.failure()?.errorText}));
 await page.evaluateOnNewDocument(()=>{
  const p=CanvasRenderingContext2D.prototype;
  for(const name of ['fillRect','fillText','translate','arc','moveTo','lineTo']){
   const original=p[name];
   p[name]=function(...args){
    if(this.canvas.id==='airspace'){
     if(name==='fillRect'&&args[0]===0&&args[1]===0)window.__radarFrame={events:[],canvas:{width:this.canvas.width,height:this.canvas.height,cssWidth:this.canvas.getBoundingClientRect().width,cssHeight:this.canvas.getBoundingClientRect().height}};
     if(window.__radarFrame)window.__radarFrame.events.push({method:name,args,fillStyle:this.fillStyle,strokeStyle:this.strokeStyle,textAlign:this.textAlign});
    }
    return original.apply(this,args);
   };
  }
 });
 await page.goto(base,{waitUntil:'networkidle0'});await page.waitForFunction(()=>document.querySelector('#flight-list').children.length===2);
 const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const capture=async(name,screenshot=false)=>{await settle();const data=await page.evaluate(()=>({frame:window.__radarFrame,range:document.querySelector('#range-label').textContent,world:JSON.parse(document.querySelector('#world-json').value),selected:document.querySelector('.flight-row.selected button')?.textContent,audit:document.querySelector('#audit-status').textContent,clock:document.querySelector('#sim-clock').textContent}));if(screenshot){const p=path.join(out,name+'.png');await(await page.$('.radar-panel')).screenshot({path:p});data.screenshot={path:name+'.png',...digest(fs.readFileSync(p))}}report.captures[name]=data;return data};
 const openDetail=async(selector)=>{if(!(await page.$eval(selector,el=>el.open)))await page.click(selector+' > summary')};
 const typeRaw=async(raw)=>{await openDetail('.state-workbench');await page.focus('#world-json');await page.$eval('#world-json',el=>el.select());await page.keyboard.type(raw);await page.keyboard.press('Tab');};
 const load=async(state)=>{await typeRaw(JSON.stringify(state));await page.click('#load-world');await page.waitForFunction(()=>document.querySelector('#world-json-feedback').textContent.startsWith('Loaded '));await settle();};
 const plane=(id,x,y,alt=10000)=>({aircraft_id:id,x_nm:x,y_nm:y,altitude_ft:alt,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0});
 const near={version:7,observed_at:1000,aircraft:[plane('WEST',-2,0),plane('EAST',2,0,12000)]};
 const far={...near,aircraft:near.aircraft.map(a=>({...a,x_nm:a.x_nm+1000,y_nm:a.y_nm+1000}))};
 const initial=await capture('initial');
 check('initial canonical crossing and automatic range are rendered',initial.world.aircraft.length===2&&initial.range==='AUTO FIT +/- 15 NM');
 await load(near);const a=await capture('near',true);
 check('actual WorldState import retains exact near coordinates',JSON.stringify(a.world)===JSON.stringify(near));
 await load(far);const b=await capture('translated',true);
 check('actual WorldState import retains exact translated coordinates',JSON.stringify(b.world)===JSON.stringify(far));
 const points=c=>c.frame.events.filter(e=>e.method==='translate').map(e=>e.args);
 const separation=c=>{const p=points(c);return Math.hypot(p[0][0]-p[1][0],p[0][1]-p[1][1])};
 check('translated four-NM separation keeps native screen scale',Math.abs(separation(a)-separation(b))<1e-7&&separation(b)>40,{near_px:separation(a),translated_px:separation(b)});
 const yTicks=b.frame.events.filter(e=>e.method==='fillText'&&e.textAlign==='right'&&/^-?\d+(\.\d+)?$/.test(e.args[0]));
 check('native north ticks show positive absolute world coordinates increasing upward',yTicks.some(e=>e.args[0]==='1000')&&yTicks.every((e,i)=>!i||Number(e.args[0])>Number(yTicks[i-1].args[0])&&e.args[2]<yTicks[i-1].args[2]),yTicks);
 check('offset view does not relocate world-origin reference rings',!b.frame.events.some(e=>e.method==='fillText'&&/^(5|10) NM$/.test(e.args[0])));
 await openDetail('.telemetry-wrap');const buttons=await page.$$('#flight-list button');await buttons[1].click();const selected=await capture('selected');
 check('real pointer selection follows the selected flight without modifying world or audit',selected.selected==='EAST'&&JSON.stringify(selected.world)===JSON.stringify(far)&&selected.audit===b.audit);
 const draft='{ "radar_review": "keep this unfinished draft", ';
 await typeRaw(draft);await(await page.$$('#flight-list button'))[0].click();await settle();
 check('raw JSON draft survives blur and selection-triggered rendering',await page.$eval('#world-json',el=>el.value)===draft);
 await page.setViewport({width:390,height:844,deviceScaleFactor:1});await settle();
 const narrow=await page.evaluate(()=>({frame:window.__radarFrame,draft:document.querySelector('#world-json').value,range:document.querySelector('#range-label').textContent,scrollWidth:document.documentElement.scrollWidth,innerWidth:innerWidth}));
 const narrowPath=path.join(out,'translated-narrow.png');await(await page.$('.radar-panel')).screenshot({path:narrowPath});narrow.screenshot={path:'translated-narrow.png',...digest(fs.readFileSync(narrowPath))};report.captures.narrow=narrow;
 check('390px desktop emulation retains the draft and draws finite separated traffic',narrow.draft===draft&&points(narrow).length===2&&separation(narrow)>20&&points(narrow).flat().every(Number.isFinite),{separation_px:separation(narrow),canvas:narrow.frame.canvas,document_width:narrow.scrollWidth,viewport:narrow.innerWidth});
 await page.click('#export-world');await settle();const exported=await capture('exported');
 check('explicit export still restores the unchanged live world',JSON.stringify(exported.world)===JSON.stringify(far));
 await page.setViewport({width:1440,height:1000,deviceScaleFactor:1});
 await page.click('#reset-world');await settle();const reset=await capture('reset');
 check('reset retains the canonical crossing and selected TWR419',reset.selected==='TWR419'&&reset.world.version===initial.world.version&&JSON.stringify(reset.world)===JSON.stringify(initial.world));
 await page.click('#run-planner');await page.waitForFunction(()=>document.querySelector('#proposal-state').textContent==='PROPOSAL READY',{timeout:90000});
 const planned=await capture('planned');
 check('real CPython planner proposes without changing world coordinates',JSON.stringify(planned.world)===JSON.stringify(reset.world)&&await page.$eval('#python-status',el=>el.textContent.includes('Live CPython')));
 await page.click('#approve');await page.waitForFunction(()=>document.querySelector('#gate-approval').classList.contains('done'));const approved=await capture('approved');
 check('approval changes its gate without changing the world',JSON.stringify(approved.world)===JSON.stringify(reset.world)&&await page.$eval('#readback',el=>!el.disabled));
 await page.click('#readback');await page.waitForFunction(()=>document.querySelector('#gate-ack').classList.contains('done'),{timeout:30000});const after=await capture('readback',true);
 check('native readback still applies one world revision and a valid four-event audit',after.world.version===reset.world.version+1&&after.audit==='4 EVENTS / VALID',after.audit);
 const overflow={version:8,observed_at:1000,aircraft:[{...plane('OVERFLOW',1,0),vx_nm_min:Number.MAX_VALUE}]};
 await load(overflow);const unavailable=await capture('unavailable',true);
 check('finite admitted projection overflow is visibly unavailable without inventing coordinates',JSON.stringify(unavailable.world)===JSON.stringify(overflow)&&unavailable.range==='RADAR VIEW UNAVAILABLE'&&unavailable.frame.events.some(e=>e.method==='fillText'&&e.args[0]==='RADAR VIEW UNAVAILABLE')&&points(unavailable).length===0);
 const invalid=JSON.stringify(overflow).replace(String(Number.MAX_VALUE),'1e309');
 await typeRaw(invalid);await page.click('#load-world');await page.waitForFunction(()=>document.querySelector('#world-json-feedback').textContent.startsWith('NOT LOADED:'));
 check('nonfinite import remains rejected by the existing parser',await page.$eval('#world-json-feedback',el=>el.textContent.includes('must be a finite number')));
 await page.click('#export-world');const retained=await capture('after-rejected-import');
 check('rejected import retains the last admitted world',JSON.stringify(retained.world)===JSON.stringify(overflow));
 check('no page script errors',report.page_errors.length===0,report.page_errors);
 report.source_after=snapshot();check('all frozen product and test source remains unchanged',JSON.stringify(report.source_before)===JSON.stringify(report.source_after));
 report.passed=true;
}catch(e){report.error=String(e);process.exitCode=1;}
finally{if(browser)await browser.close();await server.close();fs.rmSync(profile,{recursive:true,force:true});try{report.build_after=buildSnapshot();assert.deepEqual(report.build_after,report.build_before);report.build_unchanged=true;}catch(error){report.build_unchanged=false;report.error=String(error);report.passed=false;process.exitCode=1;}report.finished_at=new Date().toISOString();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});}
console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,failed:report.checks.filter(x=>!x.passed),error:report.error,result:path.join(out,'result.json')}));
