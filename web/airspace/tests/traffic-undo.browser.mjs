#!/usr/bin/env node
// Uses the repository's existing CDP transport pattern with an isolated static build/profile.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {readFile,writeFile,mkdir,mkdtemp,rm} from 'node:fs/promises';
import {createServer} from 'node:http';
import {createHash} from 'node:crypto';
import {spawn,execFileSync} from 'node:child_process';
import {join,resolve,extname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const args=process.argv.slice(2);
const option=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const root=resolve(option('--root',process.cwd()));
const output=resolve(option('--output',root+'-traffic-undo-receiving'));
const built=resolve(option('--dist',join(root,'web/airspace/dist')));
const executable=option('--browser','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
const suite=option('--suite','full'),expectMissingUndo=args.includes('--expect-missing-undo');
assert.ok(['basic','full'].includes(suite),'suite must be basic or full');
assert.ok(!expectMissingUndo||suite==='basic','missing-Undo expectation uses only the frozen basic methods');
assert.equal(fs.existsSync(output),false,'receiving output must be a new private directory');
await mkdir(output,{recursive:true});
const sha=data=>createHash('sha256').update(data).digest('hex');
const sourceFiles=[...new Set(execFileSync('git',['-C',root,'ls-files','--cached','--others','--exclude-standard','-z'],{encoding:'utf8'}).split('\0').filter(Boolean))];
const snapshot=()=>Object.fromEntries(sourceFiles.map(path=>[path,sha(fs.readFileSync(join(root,path)))]));
const beforeSource=snapshot();
function filesBelow(path,base=path){
 return fs.readdirSync(path,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?filesBelow(join(path,entry.name),base):[{path:join(path,entry.name).slice(base.length+1),sha256:sha(fs.readFileSync(join(path,entry.name))),bytes:fs.statSync(join(path,entry.name)).size}]);
}
const beforeBuild=filesBelow(built);
const mime={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.mjs':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.json':'application/json;charset=utf-8','.py':'text/x-python;charset=utf-8','.wasm':'application/wasm','.zip':'application/zip','.png':'image/png','.svg':'image/svg+xml'};
const server=createServer((req,res)=>{
 let path;try{path=resolve(built,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));}catch{res.writeHead(400);res.end();return;}
 if(path!==built&&!path.startsWith(built+sep)){res.writeHead(403);res.end();return;}
 if(path===built||fs.existsSync(path)&&fs.statSync(path).isDirectory())path=join(path,'index.html');
 if(!fs.existsSync(path)||!fs.statSync(path).isFile()){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',mime[extname(path)]||'application/octet-stream');
 res.setHeader('Cache-Control','no-store');fs.createReadStream(path).pipe(res);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base='http://127.0.0.1:'+server.address().port;
const profile=await mkdtemp(join(output,'profile-'));
const report={kind:'traffic-undo-actual-built-browser',receiverSha256:sha(await readFile(fileURLToPath(import.meta.url))),root,built,base,node:process.version,startedAt:new Date().toISOString(),baseCommit:execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),baseTree:execFileSync('git',['-C',root,'rev-parse','HEAD^{tree}'],{encoding:'utf8'}).trim(),sourceBefore:beforeSource,buildBefore:beforeBuild,checks:[],observations:[],pageErrors:[],requests:[],downloads:[],inputMethod:'Native CDP mouse events and Input.insertText after explicit DOM focus/selection; no product function or worker-result substitute.'};
let browser,browserClosed,socket,sessionId,browserLog='',sequence=0;
const pending=new Map(),sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function waitFor(check,label,attempts=200){let last;for(let i=0;i<attempts;i++){try{if(await check())return;}catch(error){last=error;}await sleep(100);}throw Error('Timed out: '+label+(last?' '+last.message:''));}
function command(method,params={},scoped=true){const id=++sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method));},10000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...scoped&&sessionId?{sessionId}:{}}));});}
async function evaluate(expression){const result=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description??result.exceptionDetails.text);return result.result.value;}
async function click(selector){
 const point=await evaluate('(()=>{const node=document.querySelector('+JSON.stringify(selector)+');if(!node)throw Error("Missing element: "+'+JSON.stringify(selector)+');node.scrollIntoView({block:"center"});const r=node.getBoundingClientRect();if(!r.width||!r.height)throw Error("Hidden element");if(node.disabled)throw Error("Disabled element");return {x:r.x+r.width/2,y:r.y+r.height/2};})()');
 for(const type of ['mouseMoved','mousePressed','mouseReleased'])await command('Input.dispatchMouseEvent',{type,...point,...type==='mouseMoved'?{}:{button:'left',clickCount:1}});
}
async function openDetails(selector){if(!await evaluate('document.querySelector('+JSON.stringify(selector)+').open'))await click(selector+' > summary');}
async function fill(selector,text){
 await click(selector);
 await evaluate('(()=>{const node=document.querySelector('+JSON.stringify(selector)+');node.focus();node.select();})()');
 await command('Input.insertText',{text});
 assert.equal(await evaluate('document.querySelector('+JSON.stringify(selector)+').value'),text,'native inserted input matches');
}
const editor=()=>evaluate('document.querySelector("#world-json").value');
const live=async()=>JSON.parse(await editor());
const selected=()=>evaluate('document.querySelector("#flight-list .selected button")?.textContent');
const ids=()=>evaluate('[...document.querySelectorAll("#flight-list button")].map(node=>node.textContent)');
async function selectFlight(id){
 const index=await evaluate('[...document.querySelectorAll("#flight-list button")].findIndex(node=>node.textContent==='+JSON.stringify(id)+')');
 assert.ok(index>=0);await click('#flight-list .flight-row:nth-child('+(index+1)+') button');assert.equal(await selected(),id);
}
async function screenshot(name){
 const result=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
 const data=Buffer.from(result.data,'base64');await writeFile(join(output,name),data);report.observations.push({screenshot:name,bytes:data.length,sha256:sha(data)});
}
const authoredWorld={version:17,observed_at:2400,aircraft:[
 {aircraft_id:'UNDO101',x_nm:-7.25,y_nm:1.125,altitude_ft:10000,vx_nm_min:1.375,vy_nm_min:0,climb_ft_min:0},
 {aircraft_id:'UNDO202',x_nm:7.75,y_nm:1.125,altitude_ft:10000,vx_nm_min:-1.625,vy_nm_min:0,climb_ft_min:0},
 {aircraft_id:'UNDO303',x_nm:9.875,y_nm:-8.625,altitude_ft:24000,vx_nm_min:0.125,vy_nm_min:0.75,climb_ft_min:-125}
]};
async function navigate(world=authoredWorld){
 await command('Emulation.setDeviceMetricsOverride',{width:1280,height:960,deviceScaleFactor:1,mobile:false});
 await command('Page.navigate',{url:base+'/'});
 await waitFor(()=>evaluate('document.readyState==="complete" && !!document.querySelector("#world-json")?.value && document.querySelector("#flight-list")?.children.length>0'),'actual built workbench ready');
 await openDetails('.state-workbench');
 await fill('#world-json',JSON.stringify(world,null,2));await click('#load-world');
 await waitFor(async()=>JSON.stringify(await ids())===JSON.stringify(world.aircraft.map(a=>a.aircraft_id)),'authored world loaded');
 await openDetails('details.control-card');await openDetails('.telemetry-wrap');
 assert.deepEqual(await live(),world);
}
async function undo(){
 const exists=await evaluate('!!document.querySelector("#undo-traffic-edit")');
 assert.ok(exists,'the actual workbench must expose Undo last traffic edit');
 assert.equal(await evaluate('document.querySelector("#undo-traffic-edit").disabled'),false,'undo must be available for this exact edit');
 await click('#undo-traffic-edit');
}

async function assertUndoUnavailable(){
 assert.equal(await evaluate('document.querySelector("#undo-traffic-edit").disabled'),true,'stale Undo is disabled');
 await click('#export-world');const before=await live();
 const point=await evaluate('(()=>{const node=document.querySelector("#undo-traffic-edit");node.scrollIntoView({block:"center"});const r=node.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()');
 for(const type of ['mouseMoved','mousePressed','mouseReleased'])await command('Input.dispatchMouseEvent',{type,...point,...type==='mouseMoved'?{}:{button:'left',clickCount:1}});
 await click('#export-world');assert.deepEqual(await live(),before,'actual disabled Undo click cannot restore stale traffic');
}
async function press(key,code){
 for(const type of ['keyDown','keyUp'])await command('Input.dispatchKeyEvent',{type,key,code:key,windowsVirtualKeyCode:code,nativeVirtualKeyCode:code});
}
async function nativeProposal(){
 await click('#run-planner');
 await waitFor(()=>evaluate('!document.querySelector("#approve").disabled'),'real Python proposal admitted',600);
 assert.match(await evaluate('document.querySelector("#python-status").textContent'),/Live CPython/);
}
async function downloadTrace(name){
 const previous=new Set(report.downloads.filter(e=>e.method==='Browser.downloadWillBegin').map(e=>e.guid));
 await click('#download-current-trace');
 await waitFor(()=>report.downloads.some(e=>e.method==='Browser.downloadWillBegin'&&!previous.has(e.guid)),'actual trace download began');
 const start=report.downloads.find(e=>e.method==='Browser.downloadWillBegin'&&!previous.has(e.guid));
 await waitFor(()=>report.downloads.some(e=>e.method==='Browser.downloadProgress'&&e.guid===start.guid&&e.state==='completed'),'actual trace download completed');
 const data=await readFile(join(output,start.guid));
 await writeFile(join(output,name),data);
 report.observations.push({download:name,browserGuid:start.guid,suggestedFilename:start.suggestedFilename,bytes:data.length,sha256:sha(data)});
 return data;
}

async function check(name,run){try{await run();report.checks.push({name,status:'passed'});console.log('PASS '+name);}catch(error){report.checks.push({name,status:'failed',error:error.stack});console.log('FAIL '+name+': '+error.message);}}
try{
 browser=spawn(executable,['--headless=new','--no-sandbox','--disk-cache-size=1','--media-cache-size=1','--disable-gpu','--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
 browserClosed=new Promise(resolve=>{browser.once('close',resolve);browser.once('error',resolve);});
 browser.stderr.on('data',data=>{browserLog=(browserLog+data.toString()).slice(-10000);});
 let launchError,port,endpoint;browser.on('error',error=>{launchError=error;});
 await waitFor(async()=>{if(launchError)throw launchError;if(browser.exitCode!==null)throw Error('Browser exited '+browser.exitCode+' '+browserLog);[port,endpoint]=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).trim().split('\n');return port&&endpoint;},'private browser startup');
 socket=new WebSocket('ws://127.0.0.1:'+port+endpoint);
 socket.addEventListener('message',event=>{
  const msg=JSON.parse(event.data);
  if(msg.id){const task=pending.get(msg.id);if(!task)return;pending.delete(msg.id);clearTimeout(task.timer);msg.error?task.reject(Error(msg.error.message)):task.resolve(msg.result);}
  else if(msg.method==='Runtime.exceptionThrown')report.pageErrors.push(msg.params.exceptionDetails.exception?.description??msg.params.exceptionDetails.text);
  else if(msg.method==='Network.requestWillBeSent')report.requests.push(msg.params.request.url);
  else if(msg.method==='Browser.downloadWillBegin'||msg.method==='Browser.downloadProgress')report.downloads.push({method:msg.method,...msg.params});
 });
 await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
 report.browser=await command('Browser.getVersion',{},false);
 const {targetId}=await command('Target.createTarget',{url:'about:blank'},false);
 ({sessionId}=await command('Target.attachToTarget',{targetId,flatten:true},false));
 await command('Page.enable');await command('Runtime.enable');await command('Network.enable');
 await command('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:output,eventsEnabled:true},false);
 await command('Page.addScriptToEvaluateOnNewDocument',{source:'window.__trafficUndoWorkerMessages=[];(()=>{const original=Worker.prototype.postMessage;const seen=new WeakSet();Worker.prototype.postMessage=function(message,...rest){if(!seen.has(this)){seen.add(this);this.addEventListener("message",event=>window.__trafficUndoWorkerMessages.push({direction:"received",data:structuredClone(event.data)}));}window.__trafficUndoWorkerMessages.push({direction:"sent",data:structuredClone(message)});return Reflect.apply(original,this,[message,...rest]);};})();'});
 await check('an accidental selected-flight removal can be recovered exactly',async()=>{
  await navigate();await selectFlight('UNDO202');const before=await live();await click('#remove-selected');
  await waitFor(async()=>(await ids()).length===2,'successful accidental removal');const removed=await live();
  assert.deepEqual(removed.aircraft,before.aircraft.filter(a=>a.aircraft_id!=='UNDO202'));assert.equal(removed.version,before.version+1);
  report.observations.push({name:'accidental-removal',before,removed,selectedAfterRemoval:await selected(),undoPresent:await evaluate('!!document.querySelector("#undo-traffic-edit")')});
  await screenshot('removal-before-undo.png');await undo();
  const recovered=await live();assert.deepEqual(recovered.aircraft,before.aircraft);assert.equal(await selected(),'UNDO202');assert.equal(recovered.version,removed.version+1);assert.equal(recovered.observed_at,before.observed_at);
  assert.equal(await evaluate('document.querySelector("#undo-traffic-edit").disabled'),true,'the one-step entry is consumed');
  report.observations.push({name:'removal-recovered',recovered,selected:await selected()});await screenshot('removal-recovered.png');
 });
 await check('a refused duplicate callsign keeps the original world and editable input',async()=>{
  await navigate();const before=await live();await fill('#flight-id','UNDO202');await click('#add-custom-flight');
  assert.match(await evaluate('document.querySelector("#builder-feedback").textContent'),/NOT ADDED/);
  assert.deepEqual(await live(),before);assert.equal(await evaluate('document.querySelector("#flight-id").value'),'UNDO202');assert.equal(await selected(),'UNDO101');
 });
 await check('an authored raw JSON draft survives a successful native traffic perturbation',async()=>{
  await navigate();const before=await live(),draft='{"keep my unfinished draft": ';
  await fill('#world-json',draft);await click('#perturb-track');assert.equal(await editor(),draft);assert.equal(await selected(),'UNDO101');
  await click('#export-world');const changed=await live(),expected=structuredClone(before);
  expected.version++;expected.aircraft[0].vx_nm_min+=0.4;expected.aircraft[0].vy_nm_min+=0.3;
  assert.deepEqual(changed,expected);
 });

 if(suite==='full'){
  await check('crossing-flight, custom-flight and vector edits each undo their actual successful world change',async()=>{
   for(const kind of ['crossing','custom','vector']){
    await navigate();await selectFlight('UNDO303');const before=await live();
    if(kind==='custom'){await fill('#flight-id','NEWUNDO');await click('#add-custom-flight');}
    else await click(kind==='crossing'?'#add-traffic':'#perturb-track');
    const changed=await live();assert.equal(changed.version,before.version+1);assert.notDeepEqual(changed.aircraft,before.aircraft);
    await undo();const recovered=await live();assert.deepEqual(recovered.aircraft,before.aircraft);assert.equal(recovered.version,changed.version+1);assert.equal(recovered.observed_at,before.observed_at);assert.equal(await selected(),'UNDO303');
    report.observations.push({name:kind+'-recovered',before,changed,recovered,selected:await selected()});
   }
  });
  await check('the real selected-flight preview and Apply can be undone exactly while the injection draft is retained',async()=>{
   await navigate();await selectFlight('UNDO303');await fill('#flight-id','MYDRAFT');const before=await live();
   await click('#edit-selected-track');await fill('#flight-x','3.625');await fill('#flight-level','245');
   await click('#preview-track-edit');assert.equal(await evaluate('document.querySelector("#apply-track-edit").disabled'),false);
   await click('#apply-track-edit');const changed=await live();assert.equal(changed.aircraft[2].x_nm,3.625);assert.equal(changed.aircraft[2].altitude_ft,24500);assert.equal(changed.version,before.version+1);
   assert.equal(await evaluate('document.querySelector("#flight-id").value'),'MYDRAFT');
   await undo();const recovered=await live();assert.deepEqual(recovered.aircraft,before.aircraft);assert.equal(recovered.version,changed.version+1);assert.equal(await selected(),'UNDO303');assert.equal(await evaluate('document.querySelector("#flight-id").value'),'MYDRAFT');
   report.observations.push({name:'selected-edit-recovered',before,changed,recovered});await screenshot('selected-edit-recovered.png');
  });
  await check('failed and unchanged edit attempts preserve the previous entry and an open edit blocks Undo',async()=>{
   await navigate();await selectFlight('UNDO202');const before=await live();await click('#remove-selected');const removed=await live();
   await fill('#flight-id','UNDO101');await click('#add-custom-flight');assert.match(await evaluate('document.querySelector("#builder-feedback").textContent'),/NOT ADDED/);
   assert.deepEqual(await live(),removed);assert.equal(await evaluate('document.querySelector("#undo-traffic-edit").disabled'),false);
   await click('#edit-selected-track');assert.equal(await evaluate('document.querySelector("#undo-traffic-edit").disabled'),true);
   await click('#preview-track-edit');assert.match(await evaluate('document.querySelector("#builder-feedback").textContent'),/NOT PREVIEWED/);
   assert.equal(await evaluate('document.querySelector("#apply-track-edit").disabled'),true);await click('#cancel-track-edit');assert.deepEqual(await live(),removed);
   await undo();assert.deepEqual((await live()).aircraft,before.aircraft);assert.equal(await selected(),'UNDO202');
  });
  await check('a policy change permanently expires Undo even when the original policy value is restored',async()=>{
   await navigate();await click('#remove-selected');await openDetails('.policy-editor');
   await click('#policy-horizontal');await press('Home',36);assert.equal(await evaluate('document.querySelector("#policy-horizontal").value'),'3');
   await assertUndoUnavailable();await click('#policy-horizontal');await press('Home',36);for(let i=0;i<4;i++)await press('ArrowRight',39);
   assert.equal(await evaluate('document.querySelector("#policy-horizontal").value'),'5');await assertUndoUnavailable();
   report.observations.push({name:'policy-round-trip-refused',world:await live(),status:await evaluate('document.querySelector("#traffic-undo-status").textContent')});
  });
  await check('actual traffic advancement and pause prevent stale restoration',async()=>{
   await navigate();await click('#remove-selected');const removed=await live();await click('#toggle-run');
   await waitFor(async()=>(await live()).version>removed.version,'actual RAF traffic advancement');
   await click('#toggle-run');assert.equal(await evaluate('document.querySelector("#toggle-run").textContent'),'Run traffic');
   await assertUndoUnavailable();const moved=await live();assert.ok(moved.version>removed.version);assert.ok(moved.observed_at>removed.observed_at);assert.notDeepEqual(moved.aircraft,removed.aircraft);
   report.observations.push({name:'advancement-refused',removed,moved});
  });
  await check('loading an identical world and Reset each end the prior Undo context',async()=>{
   await navigate();await click('#remove-selected');const removed=await live();
   await fill('#world-json',JSON.stringify(removed));await click('#load-world');assert.deepEqual(await live(),removed);await assertUndoUnavailable();
   await click('#perturb-track');assert.equal(await evaluate('document.querySelector("#undo-traffic-edit").disabled'),false);
   await click('#reset-world');await assertUndoUnavailable();assert.equal(await selected(),'TWR419');
   assert.equal(await evaluate('document.querySelector("#toggle-run").textContent'),'Run traffic');assert.equal(await evaluate('document.querySelector("#speed-value").textContent'),'1.0x');
   report.observations.push({name:'same-world-load-and-reset-refused',worldAfterReset:await live()});
  });
  await check('Undo clears a real native approval, preserves exact native audit bytes and raw draft, and fits a narrow page',async()=>{
   await navigate();await nativeProposal();await click('#approve');await click('#readback');
   await waitFor(()=>evaluate('document.querySelector("#audit-status").textContent==="4 EVENTS / VALID"'),'real native four-event apply trace',600);
   const applied=await live(),selectedBefore=await selected();const auditBefore=await downloadTrace('trace-before-undo.json');assert.equal(JSON.parse(auditBefore).length,4);
   await click('#add-traffic');const added=await live();assert.equal(added.version,applied.version+1);
   await nativeProposal();await click('#approve');assert.equal(await evaluate('document.querySelector("#readback").disabled'),false);
   const draft='{"my pending raw scenario": ';await fill('#world-json',draft);await undo();
   assert.equal(await editor(),draft,'Undo retains the exact uncommitted raw draft');
   assert.equal(await evaluate('document.querySelector("#approve").disabled'),true);assert.equal(await evaluate('document.querySelector("#readback").disabled'),true);
   for(const id of ['gate-screen','gate-approval','gate-ack'])assert.match(await evaluate('document.querySelector("#'+id+'").className'),/wait/);
   assert.equal(await selected(),selectedBefore);const auditAfter=await downloadTrace('trace-after-undo.json');assert.deepEqual(auditAfter,auditBefore,'actual downloaded native JSON bytes retained');
   await click('#export-world');const recovered=await live();assert.deepEqual(recovered.aircraft,applied.aircraft);assert.equal(recovered.version,added.version+1);assert.equal(recovered.observed_at,applied.observed_at);
   const messages=await evaluate('window.__trafficUndoWorkerMessages');assert.ok(messages.some(e=>e.direction==='sent'&&e.data.request?.op==='apply'));assert.ok(messages.filter(e=>e.direction==='sent'&&e.data.request?.op==='plan').length>=2);
   report.observations.push({name:'native-approval-audit-and-draft-recovered',applied,added,recovered,selected:selectedBefore,auditSha256:sha(auditBefore),workerMessages:messages});
   await screenshot('native-audit-recovered.png');
   await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
   await evaluate('document.querySelector("#undo-traffic-edit").scrollIntoView({block:"center"})');
   await waitFor(()=>evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'narrow page has no horizontal overflow');
   assert.match(await evaluate('document.querySelector("#traffic-undo-status").textContent'),/One-step/);await screenshot('undo-narrow.png');
  });
 }

 report.workerMessages=await evaluate('window.__trafficUndoWorkerMessages');
 assert.deepEqual(report.pageErrors,[],'actual page has no unhandled errors');
 assert.deepEqual(report.requests.filter(url=>/^https?:/.test(url)&&!url.startsWith(base+'/')),[],'no non-loopback page requests');
}catch(error){report.fatal=error.stack;console.log('FATAL '+error.stack);}
finally{
 report.sourceAfter=snapshot();report.sourceChanged=sourceFiles.filter(path=>beforeSource[path]!==report.sourceAfter[path]);
 report.buildAfter=filesBelow(built);report.buildChanged=JSON.stringify(beforeBuild)!==JSON.stringify(report.buildAfter);
 try{
  if(socket?.readyState===WebSocket.OPEN)await Promise.race([command('Browser.close',{},false).catch(()=>{}),browserClosed,sleep(1000)]);
  if(browserClosed)await Promise.race([browserClosed,sleep(5000)]);
  if(browser&&browser.exitCode===null&&browser.signalCode===null){browser.kill('SIGTERM');await Promise.race([browserClosed,sleep(5000)]);}
  socket?.close();for(const task of pending.values())clearTimeout(task.timer);pending.clear();
  await new Promise(resolve=>server.close(resolve));await rm(profile,{recursive:true,force:true,maxRetries:4,retryDelay:100});
  report.cleanup={status:'passed',privateProfileRemoved:!fs.existsSync(profile)};
 }catch(error){report.cleanup={status:'failed',error:error.stack};}
 report.browserLog=browserLog;report.finishedAt=new Date().toISOString();
 report.status=!report.fatal&&report.checks.every(check=>check.status==='passed')&&!report.sourceChanged.length&&!report.buildChanged&&report.cleanup.status==='passed'?'passed':'failed';
 report.suite=suite;report.expectation=expectMissingUndo?'exact missing-Undo witness with two successful controls':'all selected product controls pass';
 report.expectedMissingUndoMatched=expectMissingUndo&&report.checks.length===3&&report.checks[0].status==='failed'&&report.checks[0].error.includes('the actual workbench must expose Undo last traffic edit')&&report.checks.slice(1).every(check=>check.status==='passed')&&report.observations.some(value=>value.name==='accidental-removal'&&value.undoPresent===false)&&!report.fatal&&!report.pageErrors.length&&!report.sourceChanged.length&&!report.buildChanged&&report.cleanup.status==='passed';
 await writeFile(join(output,'browser-report.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,passed:report.checks.filter(check=>check.status==='passed').length,failed:report.checks.filter(check=>check.status==='failed').length,pageErrors:report.pageErrors.length,sourceChanged:report.sourceChanged,buildChanged:report.buildChanged,cleanup:report.cleanup,report:join(output,'browser-report.json')}));
 if(expectMissingUndo?!report.expectedMissingUndoMatched:report.status!=='passed')process.exitCode=1;
 if(expectMissingUndo)console.log(JSON.stringify({expectedMissingUndoMatched:report.expectedMissingUndoMatched,actualReportStatus:report.status}));
}
