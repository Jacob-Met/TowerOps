// SPDX-License-Identifier: MIT
// Native browser receiving for the live traffic register. No app or worker substitutes.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,lstat} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {openBrowser} from './cdp.mjs';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const configPath=process.argv[2]?resolve(process.argv[2]):join(root,'CANDIDATE-INPUTS-v1.json');
const configRaw=await readFile(configPath),config=JSON.parse(configRaw);
assert.match(config.run_name,/^candidate-[a-z0-9-]+$/);
const out=join(root,'evidence',config.run_name);
const profile='/home/jacob/towerops-radar-profiles-401c5d17da79/independent-register-'+config.run_name;
for(const p of [out,profile])await assert.rejects(lstat(p),{code:'ENOENT'});
await mkdir(out);
const sha=b=>createHash('sha256').update(b).digest('hex');
const report={schema:'towerops.flight-register-native-receiving.v1',parent:config.parent,source:config.source_root,source_pins:config.changed_source,inputs_sha256:sha(configRaw),method_sha256:sha(await readFile(fileURLToPath(import.meta.url))),helper_sha256:sha(await readFile(new URL('./cdp.mjs',import.meta.url))),started_at:new Date().toISOString(),node:process.version,checks:[],protected_states:[],observations:[],failure:null};
const check=(name,ok,details={})=>{report.checks.push({name,passed:!!ok,details});assert.ok(ok,name);};
const equal=(name,actual,expected)=>{let same=true;try{assert.deepEqual(actual,expected);}catch{same=false;}check(name,same,same?{}:{actual,expected});};
async function pinSource(){const changed=[];for(const [p,h] of Object.entries(config.source_files))if(sha(await readFile(join(config.source_root,p)))!==h)changed.push(p);return changed;}
const workerObserver='window.__registerIO={requests:[],responses:[]};const RegisterNativeWorker=window.Worker;window.Worker=class extends RegisterNativeWorker{constructor(...args){super(...args);this.addEventListener("message",e=>window.__registerIO.responses.push(structuredClone(e.data)));}postMessage(value,...args){window.__registerIO.requests.push(structuredClone(value));return super.postMessage(value,...args);}};';
const snapshotScript='('+(()=>{
 const text=id=>document.getElementById(id).textContent;
 const input=id=>{const e=document.getElementById(id);return {value:e.value,disabled:e.disabled,readOnly:e.readOnly};};
 const control=id=>{const e=document.getElementById(id);return {text:e.textContent,disabled:e.disabled,hidden:e.hidden};};
 return {clock:text('sim-clock'),run:control('toggle-run'),speed:input('speed-range'),speedText:text('speed-value'),selectedControl:text('edit-selected-track'),worldDraft:input('world-json'),worldFeedback:text('world-json-feedback'),proposal:text('proposal-output'),proposalState:text('proposal-state'),gates:['gate-screen','gate-approval','gate-ack'].map(id=>({id,text:text(id),className:document.getElementById(id).className})),commands:['run-planner','approve','readback'].map(control),audit:text('audit-status'),auditRows:[...document.querySelectorAll('#audit-events li')].map(e=>e.textContent),builder:text('builder-mode'),builderFeedback:text('builder-feedback'),fields:['flight-id','flight-x','flight-y','flight-level','flight-bearing','flight-speed','flight-climb'].map(input),trackControls:['preview-track-edit','apply-track-edit','cancel-track-edit'].map(control),trackPreview:text('track-edit-preview'),policy:['policy-horizontal','policy-vertical','policy-horizon'].map(input),scenarioStatus:text('scenario-status'),scenarioAvailability:text('scenario-availability'),scenarioControls:['save-scenario','choose-scenario','cancel-scenario','load-scenario'].map(control),worker:window.__registerIO};
}).toString()+')()';
let browser,server;
try{
 assert.deepEqual(await pinSource(),[]);
 assert.equal(report.helper_sha256,'be20b757f9cd7b3b85bcc701b589d61ad338123be70d75acb914eda529af5639');
 const {createServer}=await import(pathToFileURL(config.vite_module).href);
 server=await createServer({root:join(config.source_root,'web/airspace'),configFile:false,base:'./',cacheDir:join(root,'cache',config.run_name),server:{host:'127.0.0.1',port:0,fs:{allow:config.allowed_roots}}});await server.listen();
 browser=await openBrowser({profile,evidence:out,width:1440,height:1000});const c=browser.cdp;report.browser=browser.version;
 await c.send('Page.addScriptToEvaluateOnNewDocument',{source:workerObserver});
 await c.send('Page.navigate',{url:'http://127.0.0.1:'+server.httpServer.address().port+'/'});
 await c.wait('document.querySelector("#world-json")?.value?.includes("aircraft") && document.querySelector("#flight-matches").textContent==="2 of 2 flights shown"');
 const settle=()=>c.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
 async function click(id){await c.click('#'+id);await settle();}
 async function open(selector){if(!await c.evaluate('document.querySelector('+JSON.stringify(selector)+').open'))await c.click(selector+' > summary');await settle();}
 const text=id=>c.evaluate('document.getElementById('+JSON.stringify(id)+').textContent');
 const value=id=>c.evaluate('document.getElementById('+JSON.stringify(id)+').value');
 const rowIds=()=>c.evaluate('[...document.querySelectorAll("#flight-list button")].map(e=>e.textContent)');
 const active=()=>c.evaluate('({id:document.activeElement?.id,text:document.activeElement?.textContent})');
 const snapshot=()=>c.evaluate(snapshotScript);
 async function preserve(name,held){const actual=await snapshot();report.protected_states.push({name,sha256:sha(JSON.stringify(actual))});equal(name,actual,held);}
 async function key(name,code,keyCode,modifiers=0){
  for(const type of ['keyDown','keyUp']){const p={type,key:name,code,windowsVirtualKeyCode:keyCode,nativeVirtualKeyCode:keyCode,modifiers};const char=name==='Enter'?'\r':name.length===1?name:'';if(type==='keyDown'&&!modifiers&&char){p.text=char;p.unmodifiedText=char;}await c.send('Input.dispatchKeyEvent',p);}await settle();
 }
 async function order(index){await c.click('#flight-order');await key('Home','Home',36);for(let n=0;n<index;n++)await key('ArrowDown','ArrowDown',40);await key('Enter','Enter',13);}
 async function query(raw){await c.fill('#flight-filter',raw);await settle();}
 async function exportWorld(){await open('.state-workbench');await click('export-world');return value('world-json');}
 async function loadWorld(world){await open('.state-workbench');await c.fill('#world-json',JSON.stringify(world));await click('load-world');await c.wait('document.querySelector("#world-json-feedback").textContent.startsWith("Loaded ")');await settle();}
 async function native(op){return c.evaluate('(()=>{const q=[...window.__registerIO.requests].reverse().find(x=>x.request.op==='+JSON.stringify(op)+');return q?{request:q,response:window.__registerIO.responses.find(x=>x.id===q.id)}:null;})()');}

 report.phase='sixty-flight search and selection';
 const world=JSON.parse(await readFile(join(root,'evidence/baseline-89529c5/world-60.json'),'utf8'));report.fixture=world;
 await loadWorld(world);await open('.telemetry-wrap');
 equal('Normal 60-flight input retains scenario order by default',await rowIds(),world.aircraft.map(a=>a.aircraft_id));
 equal('Register exposes the full and visible counts separately',{all:await text('flight-count'),shown:await text('flight-matches')},{all:'60 FLIGHTS',shown:'60 of 60 flights shown'});
 const initialWorld=await exportWorld();const held=await snapshot();report.sixty_flight_held=held;
 await query('  eSt_  ');
 const est=world.aircraft.filter(a=>a.aircraft_id.startsWith('EST_'));
 equal('Literal case-insensitive callsign search keeps raw input and exact matches',{raw:await value('flight-filter'),ids:await rowIds(),count:await text('flight-matches')},{raw:'  eSt_  ',ids:est.map(a=>a.aircraft_id),count:'20 of 60 flights shown'});
 check('A filtered-out selection remains explicit without selecting another row',await text('flight-hidden-selection-text')==='Selected '+world.aircraft[0].aircraft_id+' is outside this search.'&&await c.evaluate('!document.querySelector("#flight-hidden-selection").hidden && !document.querySelector("#flight-list .selected")'));
 await preserve('Searching preserves simulation, approval controls, audit, drafts and worker traffic',held);
 await order(1);equal('Native order control sorts matching callsigns',await rowIds(),est.map(a=>a.aircraft_id).sort());
 await order(2);equal('Ascending altitude retains scenario order for equal values',await rowIds(),[...est].sort((a,b)=>a.altitude_ft-b.altitude_ft).map(a=>a.aircraft_id));
 await order(3);equal('Descending altitude retains scenario order for equal values',await rowIds(),[...est].sort((a,b)=>b.altitude_ft-a.altitude_ft).map(a=>a.aircraft_id));
 await preserve('All three ordering actions preserve protected state exactly',held);
 await click('flight-show-selected');
 equal('Show selected reveals the existing flight and returns focus to search',{query:await value('flight-filter'),ids:await rowIds(),focus:(await active()).id},{query:world.aircraft[0].aircraft_id,ids:[world.aircraft[0].aircraft_id],focus:'flight-filter'});
 await preserve('Show selected changes only the register view',held);
 await query('<img src=x onerror=window.__registerInjected=1>');
 check('Markup-like search is literal input with an honest empty result',await value('flight-filter')==='<img src=x onerror=window.__registerInjected=1>'&&await c.evaluate('document.querySelector("#flight-no-matches").hidden===false && !document.querySelector("#flight-register img") && !window.__registerInjected')&&(await rowIds()).length===0);
 await preserve('A no-match query preserves all 60 live aircraft and operational state',held);
 await click('flight-filter-clear');
 equal('Clear search restores all rows without resetting the chosen order',{count:(await rowIds()).length,order:await value('flight-order'),focus:(await active()).id},{count:60,order:'altitude-descending',focus:'flight-filter'});
 equal('View controls leave the exact exported live world unchanged',await exportWorld(),initialWorld);
 await order(1);
 await c.click('#flight-list .flight-row:nth-child(1) button');await settle();
 const ordered=await rowIds();check('A deliberate row click keeps that same visible button focused',(await active()).text===ordered[0]);
 await key('Tab','Tab',9);equal('Tab proceeds to the adjacent flight button',(await active()).text,ordered[1]);
 await c.evaluate('window.__registerFocusedFlight=document.activeElement');
 await key('Enter','Enter',13);
 check('Enter selects the intended flight and retains the original button node',await text('edit-selected-track')==='Edit '+ordered[1]&&await c.evaluate('document.activeElement===window.__registerFocusedFlight && document.activeElement.getAttribute("aria-pressed")==="true"'));
 await c.send('Emulation.setDeviceMetricsOverride',{width:1439,height:1000,deviceScaleFactor:1,mobile:false});await settle();
 check('A normal resize redraw preserves the focused row node',await c.evaluate('document.activeElement===window.__registerFocusedFlight && window.__registerFocusedFlight.isConnected'));
 equal('Explicit register selection does not edit the world',await exportWorld(),initialWorld);

 report.phase='live updates and narrow layout';
 await click('toggle-run');await query('STH');const beforeLiveClock=await text('sim-clock'),beforeLiveMeta=await c.evaluate('document.querySelector("#flight-list").textContent');
 await c.wait('document.querySelector("#sim-clock").textContent!=='+JSON.stringify(beforeLiveClock)+' && document.querySelector("#flight-list").textContent!=='+JSON.stringify(beforeLiveMeta),15000);
 equal('Live redraws keep the typed query and search focus',{query:await value('flight-filter'),focus:(await active()).id},{query:'STH',focus:'flight-filter'});
 await c.send('Input.insertText',{text:'_'});await settle();
 equal('Typing continues at the retained live search caret',await value('flight-filter'),'STH_');
 check('Filtered rows continue updating while traffic runs',(await rowIds()).length===20&&await text('toggle-run')==='Pause traffic');
 await click('toggle-run');const liveWorld=JSON.parse(await exportWorld());
 check('Running traffic keeps the original 60-flight source sequence',JSON.stringify(liveWorld.aircraft.map(a=>a.aircraft_id))===JSON.stringify(world.aircraft.map(a=>a.aircraft_id))&&liveWorld.observed_at>world.observed_at);
 await query('STH_');await order(2);
 await c.send('Emulation.setDeviceMetricsOverride',{width:390,height:1100,deviceScaleFactor:1,mobile:false});await settle();
 await c.evaluate('document.querySelector("#flight-register").closest(".data-panel").scrollIntoView({block:"start"})');await settle();
 const geometry=await c.evaluate('[...document.querySelectorAll("#flight-register input,#flight-register select,#flight-register button:not(:disabled),#flight-matches")].filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return {id:e.id,left:r.left,right:r.right,width:r.width};})');
 check('Register controls remain within the 390-pixel viewport',geometry.every(r=>r.left>=-0.5&&r.right<=390.5&&r.width>0),{geometry});
 await c.screenshot(join(out,'register-390-filtered.png'));
 await c.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await settle();
 await c.evaluate('document.querySelector("#flight-register").closest(".data-panel").scrollIntoView({block:"start"})');await settle();
 await c.screenshot(join(out,'register-60-altitude-order.png'));
 report.observations.push({kind:'live-world',world:liveWorld});

 report.phase='scenario replacement and held native proposal';
 const replacement={version:71,observed_at:world.observed_at+500,aircraft:[{...world.aircraft[0],aircraft_id:'FOCUS_1'}]};
 await loadWorld(replacement);
 check('Replacing the scenario removes stale rows and reports the new hidden selection',(await rowIds()).length===0&&await text('flight-hidden-selection-text')==='Selected FOCUS_1 is outside this search.'&&await text('flight-count')==='1 FLIGHTS');
 await click('flight-filter-clear');equal('Clearing after replacement shows only the new world flight',await rowIds(),['FOCUS_1']);
 await click('reset-world');await c.wait('document.querySelector("#audit-status").textContent==="0 EVENTS / VALID"');
 await click('run-planner');await c.wait('document.querySelector("#run-planner").disabled && document.querySelector("#python-status").textContent.includes("Loading")');
 await query('TWR');
 check('Search remains available while native planning disables flight selection',await c.evaluate('!document.querySelector("#flight-filter").disabled && [...document.querySelectorAll("#flight-list button")].every(e=>e.disabled)'));
 await c.wait('document.querySelector("#proposal-state").textContent==="PROPOSAL READY" && !document.querySelector("#approve").disabled',90000);
 report.native_plan=await native('plan');assert.ok(report.native_plan?.response?.result?.advisory);
 await click('approve');const approvedWorld=await exportWorld();
 await open('.control-card');await click('edit-selected-track');const oldX=Number(await value('flight-x'));await c.fill('#flight-x',String(oldX+0.5));
 const rawDraft='{\n  "version": 99,\n  "unfinished": "<keep this draft>"\n';
 await c.fill('#world-json',rawDraft);await settle();
 const approved=await snapshot();report.approved_edit_held=approved;
 assert.ok(approved.gates.find(g=>g.id==='gate-approval').text.includes('APPROVED'));
 assert.equal(approved.builder,'EDIT TWR419');
 await query('TWR642');await order(3);await click('flight-filter-clear');await query('TWR');
 check('Every flight selection remains disabled during the unfinished track edit',await c.evaluate('[...document.querySelectorAll("#flight-list button")].every(e=>e.disabled)'));
 await c.click('#flight-list .flight-row:nth-child(2) button');await settle();
 await preserve('Search, order, clear and a disabled row click preserve the complete approved edit',approved);
 equal('Protected raw JSON and unfinished track field remain byte-for-byte',{raw:await value('world-json'),x:await value('flight-x')},{raw:rawDraft,x:String(oldX+0.5)});
 await click('cancel-track-edit');
 equal('Cancel after register use retains the exact approved live world',await exportWorld(),approvedWorld);
 await click('readback');await c.wait('document.querySelector("#audit-status").textContent==="4 EVENTS / VALID" && document.querySelector("#gate-ack i").textContent==="ACCEPTED"',90000);
 report.native_apply=await native('apply');assert.ok(report.native_apply?.response?.result?.valid);
 check('The preserved proposal remains applicable through the original native readback gate',report.native_apply.response.result.events.length===4&&!report.native_apply.response.result.error);
 const applied=await snapshot();report.applied_audit_held=applied;
 await query('NO_MATCH');await order(1);await click('flight-filter-clear');
 await preserve('Register actions also preserve the resulting nonempty four-event audit exactly',applied);
 check('Candidate emits no page errors or external requests',browser.errors.length===0&&browser.blocked.length===0,{pageErrors:browser.errors,externalRequests:browser.blocked});
}catch(e){report.failure={name:e.name,message:e.message,stack:e.stack};}
finally{
 report.source_changed=await pinSource();report.borrowed_changed=[];
 for(const [p,h] of Object.entries(config.borrowed_files))if(sha(await readFile(p))!==h)report.borrowed_changed.push(p);
 if(browser){report.page_errors=browser.errors;report.external_requests=browser.blocked;await browser.close();}
 if(server)await server.close();
 report.completed_at=new Date().toISOString();report.passed=report.checks.filter(x=>x.passed).length;report.failed=report.checks.filter(x=>!x.passed).length;
 report.status=!report.failure&&!report.source_changed.length&&!report.borrowed_changed.length?'passed':'failed';
 await writeFile(join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,passed:report.passed,failed:report.failed,phase:report.phase,source_changed:report.source_changed,borrowed_changed:report.borrowed_changed,failure:report.failure,receipt:join(out,'receipt.json')},null,2));
 if(report.status!=='passed')process.exitCode=1;
}
