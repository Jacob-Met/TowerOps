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
proxy.on('connect',(req,socket)=>{socket.on('error',error=>blocked.push({method:'CONNECT_SOCKET_ERROR',url:req.url,error:String(error)}));blocked.push({method:'CONNECT',url:req.url});socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');});
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

 await group('pending_old_trace_verification_cannot_repaint_loaded_scenario',async(page,evidence)=>{
   const saved=await save(page);
   await plan(page);await page.click('#approve');await acknowledge(page);
   await expand(page,'.telemetry-wrap');await page.click('#verify-audit');
   await page.waitForFunction(()=>document.querySelector('#audit-verdict').textContent.startsWith('HASH CHAIN VALID'));
   const old=await snapshot(page);
   const eventCount=Number(old.audit_verdict.match(/(\d+) EVENTS/)[1]);
   assert.ok(eventCount>0);await review(page,saved.file);
   await page.evaluate(()=>{
     const original=crypto.subtle.digest.bind(crypto.subtle);
     let armed=true;
     window.reviewDigestCalls=0;window.reviewDigestCompleted=0;
     crypto.subtle.digest=function(...args){
       window.reviewDigestCalls++;
       const computed=original(...args);
       if(armed){
         armed=false;window.reviewDigestHeld=true;
         return new Promise((resolve,reject)=>{
           window.reviewReleaseDigest=()=>computed.then(value=>{
             window.reviewDigestCompleted++;resolve(value);
           },reject);
         });
       }
       return computed.then(value=>{window.reviewDigestCompleted++;return value;});
     };
   });
   await page.click('#verify-audit');
   await page.waitForFunction(()=>window.reviewDigestHeld===true);
   await apply(page);
   const loaded=await snapshot(page);
   evidence.old_verdict=old.audit_verdict;evidence.after_apply_verdict=loaded.audit_verdict;
   assert.equal(loaded.audit,'');assert.equal(loaded.audit_status,'0 EVENTS / VALID');
   assert.equal(loaded.audit_verdict,'');
   await page.evaluate(()=>window.reviewReleaseDigest());
   await page.waitForFunction(n=>window.reviewDigestCompleted>=n,{},eventCount);
   await settle(page);
   const completed=await snapshot(page);
   evidence.after_old_verification_completed=completed.audit_verdict;
   evidence.real_digest_calls=await page.evaluate(()=>window.reviewDigestCalls);
   evidence.real_digest_completions=await page.evaluate(()=>window.reviewDigestCompleted);
   evidence.source_edits=false;evidence.hash_values_altered=false;
   assert.equal(completed.audit,'');assert.equal(completed.audit_status,'0 EVENTS / VALID');
   assert.deepEqual(completed.world,loaded.world);
   assert.equal(completed.audit_verdict,'','A verification of the discarded trace must not publish into the replacement scenario');
 });
}finally{
 const receipt={schema:'towerops.scenario.independent-browser.v1',source,source_tree:process.env.REVIEW_SOURCE_TREE||'9d4d1320fcd59b7a635adb6439ca512650e2df71',
   node:process.version,browser:browser?await browser.version():null,groups,pageErrors,outside,blocked,requests,
   downloads:downloads.map(x=>({guid:x.guid,name:x.suggestedFilename,status:progress.get(x.guid)})),
   external_accounts_used:false,production_data_used:false,full_real_python_worker:true,source_edits:false};
 await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 await browser?.close();
 await new Promise(r=>server.close(r));await new Promise(r=>proxy.close(r));
}
if(groups.length!==1||groups.some(x=>!x.passed)||pageErrors.length)process.exitCode=1;
