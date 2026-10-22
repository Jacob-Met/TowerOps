// SPDX-License-Identifier: MIT
// Independent receiving for radar navigation while native gate and editing state are held.
// The copied CDP primitive performs real Chromium input events; it does not replace app logic.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, lstat } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { openBrowser } from './cdp.mjs';

const here=resolve(fileURLToPath(new URL('..',import.meta.url)));
const configPath=process.argv[2]?resolve(process.argv[2]):join(here,'candidate.json');
const configRaw=await readFile(configPath);
const config=JSON.parse(configRaw.toString('utf8'));
const output=join(here,'evidence',config.run_name);
const profile='/home/jacob/towerops-radar-profiles-401c5d17da79/'+config.profile_name;
assert.match(config.run_name,/^candidate-[a-z0-9-]+$/);
assert.match(config.profile_name,/^independent-[a-z0-9-]+$/);
for(const p of [output,profile]){let existing=false;try{await lstat(p);existing=true;}catch(e){if(e.code!=='ENOENT')throw e;}assert.equal(existing,false,'receiving output/profile must be new: '+p);}
await mkdir(output,{recursive:false});
const sha=b=>createHash('sha256').update(b).digest('hex');
const receipt={schema:'towerops.radar-navigation-independent-receiving.v1',source_head:config.source_head,source_tree:config.source_tree,source_root:config.source_root,source_fence:'TowerOps #59',input_config_sha256:sha(configRaw),started_at:new Date().toISOString(),node:process.version,method_sha256:sha(await readFile(fileURLToPath(import.meta.url))),helper_sha256:sha(await readFile(new URL('./cdp.mjs',import.meta.url))),checks:[],observations:[],setup:[],phase:'source guards',source_changed:[],borrowed_changed:[],failure:null};
let server,browser;
const protectedStates=[];
const check=(name,condition,details={})=>{receipt.checks.push({name,passed:!!condition,details});if(!condition)throw new Error(name);};
const equal=(name,actual,expected)=>{let same=true;try{assert.deepEqual(actual,expected);}catch{same=false;}check(name,same,same?{}:{actual,expected});};
async function hashMap(root,expected){const values={};for(const name of Object.keys(expected))values[name]=sha(await readFile(join(root,name)));return values;}
const workerObserver="window.__towerReceiverIO={requests:[],responses:[]};const TowerReceiverWorker=window.Worker;window.Worker=class extends TowerReceiverWorker{constructor(...args){super(...args);this.addEventListener('message',e=>window.__towerReceiverIO.responses.push(structuredClone(e.data)));}postMessage(value,...args){window.__towerReceiverIO.requests.push(structuredClone(value));return super.postMessage(value,...args);}};";
try{
 receipt.source_before=await hashMap(config.source_root,config.source_files);
 assert.deepEqual(receipt.source_before,config.source_files,'all isolated candidate source bytes must match freeze');
 receipt.borrowed_before={};for(const row of config.borrowed_files)receipt.borrowed_before[row.path]=sha(await readFile(row.path));
 assert.deepEqual(receipt.borrowed_before,Object.fromEntries(config.borrowed_files.map(x=>[x.path,x.sha256])),'borrowed native assets and lock must match freeze');
 assert.equal(receipt.helper_sha256,'be20b757f9cd7b3b85bcc701b589d61ad338123be70d75acb914eda529af5639');
 const {createServer}=await import(pathToFileURL(config.vite_module).href);
 server=await createServer({root:join(config.source_root,'web/airspace'),publicDir:config.public_dir,configFile:false,base:'./',cacheDir:join(here,'cache',config.run_name),server:{host:'127.0.0.1',port:0,fs:{allow:config.allowed_roots}}});
 await server.listen();
 browser=await openBrowser({profile,evidence:output,width:1440,height:1100});
 const cdp=browser.cdp;
 await cdp.send('Page.addScriptToEvaluateOnNewDocument',{source:workerObserver});
 const origin='http://127.0.0.1:'+server.httpServer.address().port;
 receipt.origin=origin;receipt.browser=browser.version;
 await cdp.send('Page.navigate',{url:origin+'/'});
 await cdp.wait('document.querySelector("#world-json")?.value?.includes("aircraft") && !!document.querySelector("#radar-zoom-in")');
 async function settle(){await cdp.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');}
 async function text(id){return cdp.evaluate('document.getElementById('+JSON.stringify(id)+').textContent');}
 async function value(id){return cdp.evaluate('document.getElementById('+JSON.stringify(id)+').value');}
 async function active(){return cdp.evaluate('document.activeElement?.id??""');}
 async function click(id){await cdp.click('#'+id);await settle();}
 async function openDetails(selector){if(!await cdp.evaluate('document.querySelector('+JSON.stringify(selector)+').open')){await cdp.click(selector+' > summary');await settle();}}
 async function key(name,code,keyCode,modifiers=0){for(const type of ['keyDown','keyUp']){const params={type,key:name,code,windowsVirtualKeyCode:keyCode,nativeVirtualKeyCode:keyCode,modifiers};const typed=name==='Enter'?'\r':name.length===1?name:'';if(type==='keyDown'&&!modifiers&&typed){params.text=typed;params.unmodifiedText=typed;}await cdp.send('Input.dispatchKeyEvent',params);}await settle();}
 async function native(operation){return cdp.evaluate('(()=>{const q=[...window.__towerReceiverIO.requests].reverse().find(x=>x.request.op==='+JSON.stringify(operation)+');return q?{request:q,response:window.__towerReceiverIO.responses.find(x=>x.id===q.id)}:null;})()');}
 async function plan(){await click('run-planner');await cdp.wait('document.querySelector("#proposal-state").textContent==="PROPOSAL READY" && !document.querySelector("#approve").disabled',90000);const x=await native('plan');assert.ok(x?.response?.result?.advisory,'real native planner must return an advisory for setup');return x;}
 async function approveAndApply(){await click('approve');await click('readback');await cdp.wait('document.querySelector("#gate-ack i").textContent==="ACCEPTED" && document.querySelector("#audit-status").textContent==="4 EVENTS / VALID"',90000);const x=await native('apply');assert.ok(x?.response?.result?.valid&&!x.response.result.error,'native setup apply must be accepted');return x;}
 async function chooseFlight(id){
  await openDetails('.telemetry-wrap');
  const index=await cdp.evaluate('[...document.querySelectorAll("#flight-list button")].findIndex(x=>x.textContent==='+JSON.stringify(id)+')');
  assert.ok(index>=0,'existing flight selection');await cdp.click('#flight-list .flight-row:nth-child('+(index+1)+') button');await settle();
  assert.equal(await cdp.evaluate('document.querySelector("#flight-list .selected button")?.textContent'),id);
 }
 async function exportWorld(){await openDetails('.state-workbench');await click('export-world');return value('world-json');}
 async function camera(){return cdp.evaluate('(()=>{const canvas=document.querySelector("#airspace"),r=canvas.getBoundingClientRect();return {range:document.querySelector("#range-label").textContent,center:document.querySelector("#radar-center-label").textContent,auto:document.querySelector("#radar-fit").getAttribute("aria-pressed"),status:document.getElementById('+JSON.stringify(config.status_id)+').textContent,active:document.activeElement?.id,canvas:{width:r.width,height:r.height},labels:canvas.getContext("2d").__radarText??[]};})()');}
 async function protectedSnapshot(){return cdp.evaluate('(()=>{const txt=id=>document.getElementById(id).textContent;const field=id=>{const e=document.getElementById(id);return {value:e.value,disabled:e.disabled,readOnly:e.readOnly,hidden:e.hidden};};const control=id=>{const e=document.getElementById(id);return {text:e.textContent,disabled:e.disabled,hidden:e.hidden};};return {clock:txt("sim-clock"),speed:field("speed-range"),speedText:txt("speed-value"),runningControl:control("toggle-run"),selected:document.querySelector("#flight-list .selected button")?.textContent,flights:[...document.querySelectorAll("#flight-list .flight-row")].map(e=>({text:e.textContent,className:e.className,disabled:e.querySelector("button").disabled})),proposal:txt("proposal-output"),proposalState:txt("proposal-state"),gates:["gate-screen","gate-approval","gate-ack"].map(id=>({id,text:txt(id),className:document.getElementById(id).className})),plannerControls:["run-planner","approve","readback"].map(control),auditStatus:txt("audit-status"),auditRows:[...document.querySelectorAll("#audit-events li")].map(e=>e.textContent),worldDraft:field("world-json"),worldDraftFeedback:txt("world-json-feedback"),builderMode:txt("builder-mode"),builderTarget:txt("builder-target"),builderFeedback:txt("builder-feedback"),trackPreview:document.getElementById("track-edit-preview").innerHTML,trackFields:["flight-id","flight-x","flight-y","flight-level","flight-bearing","flight-speed","flight-climb"].map(field),trackControls:["preview-track-edit","apply-track-edit","cancel-track-edit"].map(control),policy:["policy-horizontal","policy-vertical","policy-horizon"].map(field),pythonStatus:txt("python-status"),workerRequests:window.__towerReceiverIO.requests,workerResponses:window.__towerReceiverIO.responses};})()');}
 async function preserve(label,expected){const actual=await protectedSnapshot();protectedStates.push({label,sha256:sha(JSON.stringify(actual))});equal(label,actual,expected);}
 receipt.phase='native setup';
 const fixture=JSON.parse(await readFile(join(config.source_root,'web/airspace/tests/python-reference.json'),'utf8')).scenarios[0];
 assert.equal(await text('toggle-run'),'Run traffic','real fixture starts paused');
 const initialPlan=await plan(),initialApply=await approveAndApply();
 assert.equal(initialApply.response.result.events.length,4,'setup requires a nonempty native audit');
 receipt.setup.push({action:'Initial explicit native plan, approval and readback',plan:initialPlan,apply:initialApply});
 const restoredId=initialPlan.response.result.advisory.aircraft_id;
 const original=fixture.state.aircraft.find(x=>x.aircraft_id===restoredId);
 assert.ok(original);
 await chooseFlight(restoredId);await openDetails('.control-card');await click('edit-selected-track');
 const bearing=((Math.atan2(original.vx_nm_min,original.vy_nm_min)*180/Math.PI)%360+360)%360;
 await cdp.fill('#flight-bearing',String(bearing));await cdp.fill('#flight-speed',String(Math.hypot(original.vx_nm_min,original.vy_nm_min)*60));await cdp.fill('#flight-climb',String(original.climb_ft_min));await settle();
 await click('preview-track-edit');await cdp.wait('!document.querySelector("#apply-track-edit").disabled');await click('apply-track-edit');
 assert.equal(await text('audit-status'),'4 EVENTS / VALID','explicit scenario edit retains the prepared audit');
 const secondPlan=await plan();await click('approve');
 const beforeWorldRaw=await exportWorld(),beforeWorld=JSON.parse(beforeWorldRaw);
 const selected=beforeWorld.aircraft.find(x=>x.aircraft_id!==secondPlan.response.result.advisory.aircraft_id);
 assert.ok(selected,'focus challenge needs a different chosen flight from the pending advisory target');
 await chooseFlight(selected.aircraft_id);
 const injectionDraft=await cdp.evaluate('Object.fromEntries(["flight-id","flight-x","flight-y","flight-level","flight-bearing","flight-speed","flight-climb"].map(id=>[id,document.getElementById(id).value]))');
 await click('edit-selected-track');await cdp.fill('#flight-x',String(selected.x_nm+0.5));await settle();
 const rawDraft='{\n  "version": 71,\n  "note": "unfinished receiving draft <keep literal>"\n';
 await cdp.fill('#world-json',rawDraft);await settle();
 const held=await protectedSnapshot();
 assert.equal(held.auditStatus,'4 EVENTS / VALID');
 assert.equal(held.selected,selected.aircraft_id);
 assert.equal(held.builderMode,'EDIT '+selected.aircraft_id);
 assert.equal(held.worldDraft.value,rawDraft);
 assert.ok(held.gates.find(x=>x.id==='gate-approval').text.includes('APPROVED'));
 assert.equal(held.trackControls[1].disabled,true,'unfinished edit is not silently previewed');
 receipt.held_state=held;receipt.world_before=beforeWorld;receipt.world_before_raw=beforeWorldRaw;receipt.second_native_plan=secondPlan;
 receipt.phase='camera receiving';
 const editorCamera=await camera();
 const caretBefore=await cdp.evaluate('document.querySelector("#world-json").selectionStart');
 await key('ArrowLeft','ArrowLeft',37);
 const caretAfter=await cdp.evaluate('document.querySelector("#world-json").selectionStart');
 check('ArrowLeft remains a real text-editor operation',await active()==='world-json'&&caretAfter===Math.max(0,caretBefore-1),{caretBefore,caretAfter});
 const afterEditorCamera=await camera();
 equal('Editing arrow key leaves the radar range and status unchanged',{range:afterEditorCamera.range,center:afterEditorCamera.center,status:afterEditorCamera.status,auto:afterEditorCamera.auto},{range:editorCamera.range,center:editorCamera.center,status:editorCamera.status,auto:editorCamera.auto});
 await preserve('Raw-editor keyboard focus preserves the complete held state',held);
 await click('radar-zoom-in');
 const firstZoom=await camera();check('Native click enters a changed manual radar view',firstZoom.range.startsWith('MANUAL')&&firstZoom.range!==editorCamera.range,{range:firstZoom.range});
 await preserve('Zoom click preserves proposal, approval, audit, drafts and simulation',held);
 await key('Enter','Enter',13);const keyboardZoom=await camera();
 check('Enter activates the focused zoom button and keeps its focus',keyboardZoom.active==='radar-zoom-in'&&keyboardZoom.range!==firstZoom.range,{before:firstZoom.range,after:keyboardZoom.range,active:keyboardZoom.active});
 await preserve('Keyboard zoom preserves the complete held state',held);
 await key('Tab','Tab',9);equal('Tab reaches the adjacent zoom-out button',await active(),'radar-zoom-out');
 await key(' ','Space',32);const zoomOut=await camera();
 check('Space activates zoom-out without losing keyboard focus',zoomOut.active==='radar-zoom-out'&&zoomOut.range!==keyboardZoom.range,{range:zoomOut.range,active:zoomOut.active});
 await preserve('Keyboard zoom-out preserves the complete held state',held);
 // Canvas shortcuts are scoped to the focused radar; they must not touch held operational state.
 await cdp.click('#airspace');await settle();
 equal('The real canvas receives keyboard focus',await active(),'airspace');
 const beforeCanvasPan=await camera();
 await key('ArrowRight','ArrowRight',39);const canvasPan=await camera();
 check('Focused-canvas ArrowRight pans the view while retaining canvas focus',canvasPan.active==='airspace'&&canvasPan.center!==beforeCanvasPan.center&&canvasPan.auto==='false',{before:beforeCanvasPan.center,after:canvasPan.center,active:canvasPan.active});
 await preserve('Canvas arrow navigation preserves the complete held state',held);
 await key('ArrowUp','ArrowUp',38,2);const modifiedArrow=await camera();
 equal('Control-modified arrow is not consumed as radar navigation',{range:modifiedArrow.range,center:modifiedArrow.center,status:modifiedArrow.status,auto:modifiedArrow.auto},{range:canvasPan.range,center:canvasPan.center,status:canvasPan.status,auto:canvasPan.auto});
 await preserve('Ignored modified shortcut preserves the complete held state',held);
 await key('f','KeyF',70);const canvasFocus=await camera();
 const keyboardLabel=canvasFocus.labels.find(x=>x[0]===selected.aircraft_id);
 const keyboardAnchor={x:64+(canvasFocus.canvas.width-92)/2+13,y:24+(canvasFocus.canvas.height-64)/2-7};
 check('Focused-canvas F centers the chosen flight and retains canvas focus',canvasFocus.active==='airspace'&&!!keyboardLabel&&Math.abs(keyboardLabel[1]-keyboardAnchor.x)<1e-6&&Math.abs(keyboardLabel[2]-keyboardAnchor.y)<1e-6,{selected:selected.aircraft_id,advisoryTarget:secondPlan.response.result.advisory.aircraft_id,actual:keyboardLabel,expected:keyboardAnchor});
 await preserve('Canvas selected-flight focus preserves the complete held state',held);
 await key('Home','Home',36);const canvasAuto=await camera();
 check('Focused-canvas Home restores auto fit and keeps keyboard focus',canvasAuto.active==='airspace'&&canvasAuto.range.startsWith('AUTO FIT')&&canvasAuto.auto==='true',{range:canvasAuto.range,auto:canvasAuto.auto,active:canvasAuto.active});
 await preserve('Canvas Home preserves the complete held state',held);
 receipt.observations.push({kind:'focused-canvas-shortcuts',pan:canvasPan,modifiedArrow,focus:canvasFocus,auto:canvasAuto});
 const panViews=[];
 for(let i=0;i<12;i++){await click('radar-pan-west');const view=await camera();panViews.push({step:i+1,range:view.range,status:view.status});const actual=await protectedSnapshot();assert.deepEqual(actual,held,'west pan '+(i+1)+' must preserve held noncamera state');protectedStates.push({label:'west pan '+(i+1),sha256:sha(JSON.stringify(actual))});}
 const offscreen=await camera();
 check('Manual navigation exposes the recorded offscreen warning',new RegExp(config.offscreen_pattern,'i').test(offscreen.status),{status:offscreen.status,range:offscreen.range});
 equal('Manual offscreen view leaves native worker traffic unchanged',(await protectedSnapshot()).workerRequests,held.workerRequests);
 await preserve('Offscreen manual view preserves all held state',held);
 receipt.observations.push({kind:'manual-offscreen',panViews,camera:offscreen});
 await cdp.evaluate('document.querySelector(".radar-panel").scrollIntoView({block:"center"})');await settle();await cdp.screenshot(join(output,'held-approval-edit-offscreen.png'));
 await click('radar-focus');const focused=await camera();
 const selectedLabel=focused.labels.find(x=>x[0]===selected.aircraft_id);
 const expectedAnchor={x:64+(focused.canvas.width-92)/2+13,y:24+(focused.canvas.height-64)/2-7};
 check('Focus centers the chosen flight rather than the pending advisory target',!!selectedLabel&&Math.abs(selectedLabel[1]-expectedAnchor.x)<1e-6&&Math.abs(selectedLabel[2]-expectedAnchor.y)<1e-6,{selected:selected.aircraft_id,advisoryTarget:secondPlan.response.result.advisory.aircraft_id,actual:selectedLabel,expectedAnchor});
 // Centering disables an already-satisfied Focus action; no focus-retention assertion is imposed on a newly disabled button.
 await preserve('Chosen-flight focus preserves the complete held state',held);
 await click('radar-fit');const automatic=await camera();
 check('Fit traffic returns the radar to automatic framing',automatic.range.startsWith('AUTO FIT')&&automatic.auto==='true'&&automatic.active==='radar-fit',{range:automatic.range,active:automatic.active});
 await preserve('Returning to auto preserves the complete held state',held);
 receipt.camera_state_hashes=protectedStates;receipt.observations.push({kind:'chosen-flight-focus',camera:focused},{kind:'return-auto',camera:automatic});
 await cdp.evaluate('document.querySelector(".radar-panel").scrollIntoView({block:"center"})');await settle();await cdp.screenshot(join(output,'held-approval-edit-auto-restored.png'));
 receipt.phase='explicit post-camera probes';
 // Export and cancel are deliberate user actions after the draft-preservation assertions.
 const exported=await exportWorld();
 equal('Normal export proves the exact live world was unchanged by camera input',exported,beforeWorldRaw);
 await click('cancel-track-edit');
 const restoredDraft=await cdp.evaluate('Object.fromEntries(["flight-id","flight-x","flight-y","flight-level","flight-bearing","flight-speed","flight-climb"].map(id=>[id,document.getElementById(id).value]))');
 equal('Cancel restores the original injection draft after camera use',restoredDraft,injectionDraft);
 check('The preexisting approved proposal is still ready for explicit readback',!await cdp.evaluate('document.querySelector("#readback").disabled'));
 await click('readback');await cdp.wait('document.querySelector("#gate-ack i").textContent==="ACCEPTED" && document.querySelector("#audit-status").textContent==="8 EVENTS / VALID"',90000);
 const finalApply=await native('apply'),request=finalApply.request.request;
 receipt.explicit_final_apply=finalApply;
 equal('Native readback receives the exact held world',request.state,beforeWorld);
 equal('Native readback receives the exact original second proposal',request.advisory,secondPlan.response.result.advisory);
 equal('Native readback receives the unmodified approval binding',request.approval,{advisory_hash:secondPlan.response.result.advisory.advisory_hash,decision:'approve',approved_at:secondPlan.request.request.now+0.2,approver:'synthetic-controller'});
 equal('Exact paused simulation time survives the camera journey',request.now,secondPlan.request.request.now+0.5);
 equal('Native readback receives the complete preexisting audit bytes',request.audit_json,initialApply.response.result.audit_json);
 equal('Explicit apply preserves the original four-event audit prefix',finalApply.response.result.events.slice(0,4),initialApply.response.result.events);
 check('The deliberate final readback is natively accepted',finalApply.response.result.valid===true&&!finalApply.response.result.error&&finalApply.response.result.events.length===8,{events:finalApply.response.result.events.length});
 check('Real browser journey has no script exceptions or external requests',browser.errors.length===0&&browser.blocked.length===0,{errors:browser.errors,blocked:browser.blocked});
 receipt.phase='completed';
}catch(error){receipt.failure={phase:receipt.phase,message:String(error.stack??error)};}
finally{
 if(browser){try{await browser.close();}catch(e){receipt.browser_close_error=String(e);}receipt.page_errors=browser.errors;receipt.blocked_external_requests=browser.blocked;}
 if(server){try{await server.close();}catch(e){receipt.server_close_error=String(e);}}
 try{
  receipt.source_after=await hashMap(config.source_root,config.source_files);
  receipt.source_changed=Object.keys(config.source_files).filter(x=>receipt.source_after[x]!==config.source_files[x]);
  receipt.borrowed_after={};for(const row of config.borrowed_files)receipt.borrowed_after[row.path]=sha(await readFile(row.path));
  receipt.borrowed_changed=config.borrowed_files.filter(x=>receipt.borrowed_after[x.path]!==x.sha256).map(x=>x.path);
  check('Isolated source and borrowed native runtime inputs remain byte-identical',receipt.source_changed.length===0&&receipt.borrowed_changed.length===0,{source_changed:receipt.source_changed,borrowed_changed:receipt.borrowed_changed});
 }catch(e){receipt.final_source_error=String(e);}
 receipt.finished_at=new Date().toISOString();
 receipt.passed=receipt.checks.filter(x=>x.passed).length;receipt.failed=receipt.checks.filter(x=>!x.passed).length;
 receipt.status=!receipt.failure&&!receipt.failed&&!receipt.final_source_error&&!receipt.browser_close_error&&!receipt.server_close_error?'passed':'failed';
 const raw=JSON.stringify(receipt,null,2)+'\n';await writeFile(join(output,'receipt.json'),raw);
 console.log(JSON.stringify({status:receipt.status,passed:receipt.passed,failed:receipt.failed,phase:receipt.phase,failure:receipt.failure,receipt:join(output,'receipt.json'),sha256:sha(raw),source_head:receipt.source_head,source_changed:receipt.source_changed,borrowed_changed:receipt.borrowed_changed}));
 if(receipt.status!=='passed')process.exitCode=1;
}
