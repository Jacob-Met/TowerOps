import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url), puppeteer=require('puppeteer');
const source=path.resolve(process.argv[2]), output=path.resolve(process.argv[3]);
await fs.mkdir(output,{recursive:false});
await fs.mkdir(path.join(output,'downloads'));
await fs.mkdir(path.join(output,'fixtures'));
const requests=[],pageErrors=[],outside=[],blocked=[],groups=[],downloads=[],progress=new Map();
let active='',browser,client;
const digest=value=>createHash('sha256').update(value).digest('hex');
const root=path.join(source,'web/airspace/dist');
const server=http.createServer(async(req,res)=>{
 try {
  const u=new URL(req.url,'http://127.0.0.1');
  const rel=decodeURIComponent(u.pathname.replace(/^\/TowerOps\/airspace\/?/,''));
  let file=path.resolve(root,rel||'index.html');
  if(file!==root&&!file.startsWith(root+path.sep))throw Error('path escape');
  if((await fs.stat(file)).isDirectory())file=path.join(file,'index.html');
  const bytes=await fs.readFile(file);
  const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.wasm':'application/wasm','.css':'text/css','.svg':'image/svg+xml'};
  requests.push({group:active,path:u.pathname,sha256:digest(bytes),bytes:bytes.length});
  res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});res.end(bytes);
 } catch {res.writeHead(404);res.end('Not found');}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const origin='http://127.0.0.1:'+server.address().port;
const proxy=http.createServer((req,res)=>{blocked.push({method:req.method,url:req.url});res.writeHead(403);res.end('Offline independent review');});
proxy.on('connect',(req,socket)=>{blocked.push({method:'CONNECT',url:req.url});socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');});
await new Promise(r=>proxy.listen(0,'127.0.0.1',r));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(test,label,limit=40000){const start=Date.now();while(Date.now()-start<limit){if(await test())return;await sleep(25);}throw Error('Timed out '+label);}
async function settle(page){await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
async function expand(page,selector){if(!await page.$eval(selector,x=>x.open))await page.click(selector+' > summary');}
async function field(page,id,value){await page.$eval('#'+id,(x,v)=>{x.value=String(v);x.dispatchEvent(new Event('input',{bubbles:true}));},value);await settle(page);}
async function pageFor(){const page=await browser.newPage();await page.setViewport({width:1360,height:1000});page.on('pageerror',e=>pageErrors.push({group:active,error:String(e)}));page.on('request',r=>{const u=r.url();if(!u.startsWith(origin+'/')&&!u.startsWith('blob:')&&!u.startsWith('data:'))outside.push({group:active,url:u});});await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});await expand(page,'.scenario-workbench');return page;}
async function snapshot(page){await settle(page);return page.evaluate(()=>({
 world:JSON.parse(document.querySelector('#world-json').value),
 selected:document.querySelector('#edit-selected-track').textContent,
 policy:['policy-horizontal','policy-vertical','policy-horizon'].map(x=>Number(document.getElementById(x).value)),
 rate:Number(document.querySelector('#speed-range').value),rate_label:document.querySelector('#speed-value').textContent,
 clock:document.querySelector('#sim-clock').textContent,proposal:document.querySelector('#proposal-output').textContent,
 approval_disabled:document.querySelector('#approve').disabled,readback_disabled:document.querySelector('#readback').disabled,
 audit:document.querySelector('#audit-events').textContent,audit_status:document.querySelector('#audit-status').textContent,
 audit_verdict:document.querySelector('#audit-verdict').textContent,
 gates:['gate-screen','gate-approval','gate-ack'].map(x=>document.getElementById(x).textContent),
 python:document.querySelector('#python-status').textContent
}));}
async function save(page){const n=downloads.length;await page.click('#save-scenario');await until(()=>downloads.length>n,'download start');const event=downloads[n];await until(()=>progress.get(event.guid)==='completed','download finish');const file=path.join(output,'downloads',event.guid),text=await fs.readFile(file,'utf8');return{file,text,document:JSON.parse(text),filename:event.suggestedFilename,sha256:digest(text)};}
async function fixture(name,value){const file=path.join(output,'fixtures',name);await fs.writeFile(file,typeof value==='string'?value:JSON.stringify(value));return file;}
async function choose(page,file){const pending=page.waitForFileChooser();await page.click('#choose-scenario');await(await pending).accept([file]);}
async function review(page,file){await choose(page,file);await page.waitForFunction(()=>!document.querySelector('#scenario-review').hidden&&!document.querySelector('#load-scenario').disabled);await settle(page);}
async function apply(page){await page.click('#load-scenario');await page.waitForFunction(()=>document.querySelector('#scenario-status').textContent.startsWith('Scenario loaded'));await settle(page);}
async function plan(page,{advisory=true}={}){await page.click('#run-planner');await until(async()=>/Live CPython/.test(await page.$eval('#python-status',x=>x.textContent)),'actual CPython plan');await settle(page);if(advisory)assert.equal(await page.$eval('#approve',x=>x.disabled),false);}
async function acknowledge(page){await page.click('#readback');await until(async()=>/Simulated setpoint applied/.test(await page.$eval('#proposal-output',x=>x.textContent)),'actual CPython readback');await settle(page);}
async function group(name,fn){active=name;const start=Date.now();let page;const record={name};try{page=await pageFor();await fn(page,record);record.passed=true;}catch(error){record.passed=false;record.error=String(error);if(page){record.failed_snapshot=await snapshot(page).catch(()=>null);await page.screenshot({path:path.join(output,name+'.png'),fullPage:true}).catch(()=>{});}}finally{record.elapsed_ms=Date.now()-start;groups.push(record);console.log(JSON.stringify(record));await page?.close();}}

try{
 browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,
   args:['--disable-background-networking','--no-first-run','--disable-quic','--proxy-server=http://127.0.0.1:'+proxy.address().port],
   userDataDir:path.join(output,'profile')});
 client=await browser.target().createCDPSession();
 await client.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(output,'downloads'),eventsEnabled:true});
 client.on('Browser.downloadWillBegin',e=>downloads.push(e));client.on('Browser.downloadProgress',e=>progress.set(e.guid,e.state));

 await group('clock_freshness_reaches_actual_python_gate',async(page,evidence)=>{
   const initial=await save(page);
   const fresh=initial.document;
   const stale={...fresh,now:fresh.world.observed_at+fresh.policy.max_state_age_sec+2.75};
   const before=await snapshot(page);
   await review(page,await fixture('stale-clock.json',stale));
   assert.deepEqual(await snapshot(page),before);
   await apply(page);
   const imported=await save(page);assert.deepEqual(imported.document,stale);
   await plan(page,{advisory:false});
   const refused=await snapshot(page);
   assert.equal(refused.approval_disabled,true);
   assert.equal(refused.readback_disabled,true);
   assert.match(refused.python,/Live CPython/);
   assert.deepEqual(refused.world,stale.world);
   await review(page,initial.file);await apply(page);await plan(page);
   const accepted=await snapshot(page);
   assert.equal(accepted.approval_disabled,false);
   assert.deepEqual(accepted.world,fresh.world);
   evidence.stale={now:stale.now,observed_at:stale.world.observed_at,proposal:refused.proposal,python:refused.python};
   evidence.fresh={now:fresh.now,proposal:accepted.proposal,python:accepted.python};
   evidence.same_world_two_clock_controls=true;
 });

 await group('new_scenario_discards_prior_audit_verification_result',async(page,evidence)=>{
   const saved=await save(page);
   await plan(page);await page.click('#approve');await acknowledge(page);
   await expand(page,'.telemetry-wrap');await page.click('#verify-audit');
   await page.waitForFunction(()=>document.querySelector('#audit-verdict').textContent.startsWith('HASH CHAIN VALID'));
   const old=await snapshot(page);
   assert.match(old.audit_verdict,/HASH CHAIN VALID - [1-9]\d* EVENTS/);
   await review(page,saved.file);await apply(page);
   const loaded=await snapshot(page);
   evidence.previous_verdict=old.audit_verdict;evidence.loaded_verdict=loaded.audit_verdict;
   evidence.loaded_event_list=loaded.audit;evidence.loaded_audit_status=loaded.audit_status;
   evidence.old_authority_buttons_cleared=loaded.approval_disabled&&loaded.readback_disabled;
   assert.equal(loaded.audit,'');
   assert.equal(loaded.audit_status,'0 EVENTS / VALID');
   assert.equal(loaded.approval_disabled,true);assert.equal(loaded.readback_disabled,true);
   assert.equal(loaded.audit_verdict,'','Previous verification belongs to a discarded trace');
 });

 await group('file_bytes_preserve_signed_zero_policy_selection_and_clock',async(page,evidence)=>{
   const initial=await save(page);
   const document={...initial.document,
     world:{version:41,observed_at:2500.25,aircraft:[
       {aircraft_id:'REVIEWB',x_nm:6.75,y_nm:0,altitude_ft:9500,vx_nm_min:-1,vy_nm_min:0.1,climb_ft_min:250},
       {aircraft_id:'REVIEWA',x_nm:0,y_nm:0,altitude_ft:9000,vx_nm_min:0,vy_nm_min:1,climb_ft_min:0}]},
     policy:{...initial.document.policy,min_horizontal_nm:3.5,min_vertical_ft:600,horizon_min:8.5},
     now:2507.75,time_scale:0.5,selected_aircraft_id:'REVIEWB'};
   let input=JSON.stringify(document).replace('"x_nm":0','"x_nm":-0').replace('"vx_nm_min":0','"vx_nm_min":-0').replace('"climb_ft_min":0','"climb_ft_min":-0');
   const expected=JSON.parse(input);assert.equal(Object.is(expected.world.aircraft[1].x_nm,-0),true);
   await review(page,await fixture('exact-numeric-world.json',input));await apply(page);
   const saved=await save(page);assert.deepEqual(saved.document,expected);
   const visible=await snapshot(page);
   assert.deepEqual(visible.policy,[3.5,600,8.5]);assert.equal(visible.rate,0.5);assert.equal(visible.rate_label,'0.5x');
   assert.equal(visible.selected,'Edit REVIEWB');
   assert.equal(visible.clock,'T+'+Math.floor(expected.now-initial.document.now)+' SEC');
   await expand(page,'.control-card');await page.click('#edit-selected-track');
   await field(page,'flight-x',5);await page.click('#preview-track-edit');
   assert.equal(await page.$eval('#apply-track-edit',x=>x.disabled),false);
   await page.click('#apply-track-edit');await settle(page);
   const edited=await save(page);
   assert.equal(edited.document.world.version,42);
   assert.equal(edited.document.world.aircraft[0].x_nm,5);
   assert.deepEqual(edited.document.world.aircraft[1],expected.world.aircraft[1]);
   evidence.download_sha256=saved.sha256;evidence.imported_world_version=41;evidence.edited_world_version=42;
   evidence.signed_zero_retained=true;evidence.unedited_aircraft_retained=true;
 });

 await group('approval_change_invalidates_review_without_erasing_approval',async(page,evidence)=>{
   const saved=await save(page);await plan(page);
   await review(page,saved.file);const before=await snapshot(page);
   await page.click('#approve');await settle(page);
   const approved=await snapshot(page);
   assert.equal(await page.$eval('#scenario-review',x=>x.hidden),true);
   assert.equal(await page.$eval('#load-scenario',x=>x.disabled),true);
   assert.equal(approved.readback_disabled,false);
   assert.deepEqual(approved.world,before.world);
   await page.$eval('#load-scenario',x=>x.click());await settle(page);
   assert.deepEqual(await snapshot(page),approved);
   await acknowledge(page);
   evidence.prior_review_cannot_be_applied=true;evidence.valid_approval_still_applies=true;
 });

 await group('late_file_read_cannot_replace_completed_native_readback',async(page,evidence)=>{
   const saved=await save(page);await plan(page);await page.click('#approve');
   await page.evaluate(()=>{const original=File.prototype.text;File.prototype.text=function(){const data=original.call(this);return new Promise(resolve=>{window.reviewRelease=()=>data.then(resolve);});};});
   await choose(page,saved.file);await page.waitForFunction(()=>typeof window.reviewRelease==='function');
   await acknowledge(page);
   const applied=await snapshot(page);
   await page.evaluate(()=>window.reviewRelease());await settle(page);
   assert.equal(await page.$eval('#scenario-review',x=>x.hidden),true);
   assert.equal(await page.$eval('#load-scenario',x=>x.disabled),true);
   assert.deepEqual(await snapshot(page),applied);
   evidence.completed_world_version=applied.world.version;evidence.late_read_held=true;
   evidence.audit_status=applied.audit_status;
 });

 await group('selected_edit_cancel_retains_draft_and_pending_decision',async(page,evidence)=>{
   const saved=await save(page);await plan(page);await page.click('#approve');
   await expand(page,'.control-card');
   const drafts={'flight-id':'DRAFT9','flight-x':3.5,'flight-y':-7,'flight-level':160,'flight-bearing':55,'flight-speed':180,'flight-climb':250};
   for(const[id,value]of Object.entries(drafts))await field(page,id,value);
   const before=await snapshot(page);
   await review(page,saved.file);await page.click('#edit-selected-track');await settle(page);
   assert.equal(await page.$eval('#scenario-review',x=>x.hidden),true);
   assert.equal(await page.$eval('#choose-scenario',x=>x.disabled),true);
   await field(page,'flight-x',11);await page.click('#preview-track-edit');await page.click('#cancel-track-edit');await settle(page);
   assert.deepEqual(await snapshot(page),before);
   for(const[id,value]of Object.entries(drafts))assert.equal(await page.$eval('#'+id,x=>x.value),String(value));
   assert.equal(await page.$eval('#load-scenario',x=>x.disabled),true);
   await acknowledge(page);
   evidence.draft_retained=true;evidence.pending_decision_retained=true;evidence.stale_import_not_revived=true;
 });

}finally{
 const receipt={schema:'towerops.scenario.independent-browser.v1',source,source_tree:'9d4d1320fcd59b7a635adb6439ca512650e2df71',
   node:process.version,browser:browser?await browser.version():null,groups,pageErrors,outside,blocked,requests,
   downloads:downloads.map(x=>({guid:x.guid,name:x.suggestedFilename,status:progress.get(x.guid)})),
   external_accounts_used:false,production_data_used:false,full_real_python_worker:true,source_edits:false};
 await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 await browser?.close();
 await new Promise(r=>server.close(r));await new Promise(r=>proxy.close(r));
}
if(groups.length!==6||groups.some(x=>!x.passed)||pageErrors.length)process.exitCode=1;
