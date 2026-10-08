import '../style.css';
import { createEncounterExplorer } from './encounter-view';
import reference from '../tests/python-reference.json';
import { Aircraft,DEFAULT_POLICY,SafetyPolicy,WorldState,conflictPairs,projected } from './core';
import { createAircraft,conflictWindows,parseWorldState } from './world-tools';
import { TrackEditInput,TrackEditPreview,TrackEditSession,applyTrackEdit,beginTrackEdit,previewTrackEdit } from './track-edit';
import { Advisory } from './planner';
import { towerPython } from './python';
import { AuditLog } from './audit';
import { Ack,Approval,GateRejected } from './gate';
import { AuditEvent } from './audit';
import { drawAirspace,viewRange } from './draw';
import { DecisionTraceReport,initializeDecisionTrace } from './decision-trace';
type Scenario={name:string;state:WorldState;now:number};
const fixture=(reference as unknown as {scenarios:Scenario[]}).scenarios[0]!;
const $=<T extends HTMLElement>(id:string)=>document.getElementById(id) as T;
const copy=(s:WorldState):WorldState=>JSON.parse(JSON.stringify(s)) as WorldState;
const encounterExplorer=createEncounterExplorer($('encounter-explorer'));
let policy:SafetyPolicy={...DEFAULT_POLICY};
let state=copy(fixture.state),now=fixture.now,selected='TWR419',running=false,pending:Advisory|null=null,approval:Approval|null=null,audit=new AuditLog();
let rate=1,lastFrame=0,trafficSeq=0,busy=false,pythonAudit='[]';
let trackEdit:TrackEditSession|null=null,trackPreview:TrackEditPreview|null=null,injectDraft:Record<string,string>|null=null;
const decisionTrace=initializeDecisionTrace({getCurrentTrace:()=>pythonAudit,reviewTrace:reviewDecisionTrace});
const flightFields=['flight-id','flight-x','flight-y','flight-level','flight-bearing','flight-speed','flight-climb'];
type GateState='wait'|'done'|'fail'; let gateScreen:GateState='wait',gateApproval:GateState='wait',gateAck:GateState='wait';
function setText(id:string,value:string){$(id).textContent=value;}
function gate(id:string,status:'wait'|'done'|'fail',label:string){const node=$(id);node.className=`gate-step ${status}`;const i=node.querySelector('i');if(i)i.textContent=label;}
function drawLists(pairs:Array<[string,string]>){
 const flights=$('flight-list');flights.replaceChildren();
 for(const a of state.aircraft){const row=document.createElement('div');row.className=`flight-row ${selected===a.aircraft_id?'selected':''}`;const b=document.createElement('button');b.textContent=a.aircraft_id;b.disabled=busy||!!trackEdit;b.onclick=()=>{selected=a.aircraft_id;render();};const meta=document.createElement('span');meta.className='flight-meta';meta.textContent=`${Math.round(a.altitude_ft/100)} FL / ${a.vx_nm_min.toFixed(1)}, ${a.vy_nm_min.toFixed(1)} NM/M`;row.append(b,meta);flights.append(row);}
 const watch=$('conflict-list');watch.replaceChildren();
 for(const [a,b] of pairs){const row=document.createElement('div');row.className='conflict-row';const label=document.createElement('span');label.textContent=`${a} / ${b}`;const meta=document.createElement('span');meta.className='conflict-meta';meta.textContent='HORIZONTAL + VERTICAL';row.append(label,meta);watch.append(row);}
 if(!pairs.length){const p=document.createElement('p');p.className='fine-print';p.textContent='No pair enters both unsafe intervals inside the policy horizon.';watch.append(p);}
 setText('flight-count',`${state.aircraft.length} FLIGHTS`);
}
let proposalMessage='No proposal yet. The planner only returns a setpoint if it clears the separation policy.';
async function render():Promise<void>{
 decisionTrace.setBusy(busy);
 const pairs=conflictPairs(state,policy);drawAirspace($<HTMLCanvasElement>('airspace'),state,selected,policy);drawLists(pairs);
 encounterExplorer.update(state,policy,running);
 const badge=$('world-badge');badge.className=`badge ${pairs.length?'alert':'safe'}`;badge.textContent=pairs.length?'ACTION':'CLEAR';
 setText('world-title',pairs.length?`${pairs.length} conflict pair${pairs.length===1?'':'s'} inside policy envelope`:'No projected conflict');
 setText('world-note',pairs.length?'Horizontal and vertical unsafe-time intervals overlap inside the active policy horizon.':'No simultaneous horizontal and vertical intrusion inside the active policy horizon.');
 setText('pair-count',String(pairs.length));setText('policy-window',`${policy.horizon_min.toFixed(1)} MIN`);setText('range-label',`RANGE +/- ${viewRange(state,policy)} NM`);setText('projection-label',`${policy.horizon_min.toFixed(1)} MIN PROJECTION`);const first=conflictWindows(state,policy)[0];setText('conflict-time',first?`T+${(first.start_min*60).toFixed(0)} SEC`:'CLEAR');setText('conflict-detail',first?`${first.aircraft_a} / ${first.aircraft_b} share ${first.start_min.toFixed(2)} to ${first.end_min.toFixed(2)} min. Midpoint: ${first.horizontal_nm.toFixed(2)} NM / ${first.vertical_ft.toFixed(0)} FT.`:'No simultaneous loss of separation. Add traffic or tighten the envelope.');setText('policy-stat-horizontal',policy.min_horizontal_nm.toFixed(1));setText('policy-stat-vertical',policy.min_vertical_ft.toLocaleString('en-US'));setText('policy-stat-horizon',policy.horizon_min.toFixed(1));const editor=$<HTMLTextAreaElement>('world-json');if(document.activeElement!==editor)editor.value=JSON.stringify(state,null,2);setText('sim-clock',`T+${Math.max(0,Math.floor(now-fixture.now))} SEC`);setText('speed-value',`${rate.toFixed(1)}x`);
 setText('proposal-state',pending?'PROPOSAL READY':pairs.length?'NEEDS REVIEW':'IDLE');
 if(pending)setText('proposal-output',`${pending.aircraft_id} -> vx ${pending.set_vx_nm_min.toFixed(1)} / vy ${pending.set_vy_nm_min.toFixed(1)} NM/M / climb ${pending.set_climb_ft_min} FT/M. Bound to ${pending.world_hash.slice(0,10)}.`);else setText('proposal-output',proposalMessage);
 gate('gate-screen',gateScreen,gateScreen==='done'?'PASS':gateScreen==='fail'?'FAIL':'WAIT');gate('gate-approval',gateApproval,gateApproval==='done'?'APPROVED':gateApproval==='fail'?'REJECTED':'WAIT');gate('gate-ack',gateAck,gateAck==='done'?'ACCEPTED':gateAck==='fail'?'REJECTED':'WAIT');
 $('run-planner').toggleAttribute('disabled',busy||!!trackEdit||!pairs.length||!!pending);$('approve').toggleAttribute('disabled',busy||!!trackEdit||!pending||!!approval);$('readback').toggleAttribute('disabled',busy||!!trackEdit||!pending||!approval);$('toggle-run').toggleAttribute('disabled',busy||!!trackEdit||!!pending);
 for(const id of ['reset-world','add-traffic','add-custom-flight','remove-selected','perturb-track','load-world','policy-horizontal','policy-vertical','policy-horizon','edit-selected-track'])$(id).toggleAttribute('disabled',busy||!!trackEdit);
 setText('edit-selected-track',`Edit ${selected}`);setText('builder-mode',trackEdit?`EDIT ${trackEdit.aircraft_id}`:'BUILD A FLIGHT');setText('builder-target',trackEdit?'PREVIEW → APPLY ONE EDIT':'YOUR INPUT → LIVE WORLD');
 $<HTMLInputElement>('flight-id').readOnly=!!trackEdit;for(const id of ['add-custom-flight','remove-selected','edit-selected-track'])$(id).hidden=!!trackEdit;
 $('track-edit-controls').hidden=!trackEdit;$('track-edit-preview').hidden=!trackEdit;
 $('preview-track-edit').toggleAttribute('disabled',busy||!trackEdit);$('apply-track-edit').toggleAttribute('disabled',busy||!trackEdit||!trackPreview);$('cancel-track-edit').toggleAttribute('disabled',busy||!trackEdit);
 const valid=await audit.verify();setText('audit-status',`${audit.events.length} EVENT${audit.events.length===1?'':'S'} / ${valid?'VALID':'BROKEN'}`);
 const list=$('audit-events');list.replaceChildren();for(const e of audit.events){const li=document.createElement('li');li.textContent=`${String(e.seq).padStart(2,'0')}  ${e.kind}  ${JSON.stringify(e.payload).slice(0,120)}  ${e.event_hash.slice(0,12)}`;list.append(li);}
}

function pauseTraffic(){running=false;setText('toggle-run','Run traffic');encounterExplorer.update(state,policy,false);}
function clearPending(message:string){pending=null;approval=null;proposalMessage=message;gateScreen='wait';gateApproval='wait';gateAck='wait';}
function readTrackFields():TrackEditInput {
 const num=(id:string)=>$<HTMLInputElement>(id).valueAsNumber;
 return {x_nm:num('flight-x'),y_nm:num('flight-y'),flight_level:num('flight-level'),bearing_deg:num('flight-bearing'),speed_kt:num('flight-speed'),climb_ft_min:num('flight-climb')};
}
function startTrackEdit(){
 if(busy||trackEdit)return;
 try{
  const session=beginTrackEdit(state,selected,policy,now);
  injectDraft=Object.fromEntries(flightFields.map(id=>[id,$<HTMLInputElement>(id).value]));
  trackEdit=session;trackPreview=null;running=false;$('toggle-run').textContent='Run traffic';
  const values:Record<string,string|number>={'flight-id':session.aircraft_id,'flight-x':session.input.x_nm,'flight-y':session.input.y_nm,'flight-level':session.input.flight_level,'flight-bearing':session.input.bearing_deg,'flight-speed':session.input.speed_kt,'flight-climb':session.input.climb_ft_min};
  for(const [id,value] of Object.entries(values))$<HTMLInputElement>(id).value=String(value);
  setText('track-edit-preview','Change the fields, then preview the conflict intervals. The live world stays paused and unchanged until Apply.');
  setText('builder-feedback',`Editing ${session.aircraft_id}. Its callsign stays fixed. Cancel keeps the world and any pending proposal.`);
  void render();$<HTMLInputElement>('flight-x').focus();
 }catch(err){setText('builder-feedback',`NOT EDITING: ${err instanceof Error?err.message:String(err)}`);}
}
function showTrackPreview(preview:TrackEditPreview){
 const node=$('track-edit-preview');node.replaceChildren();
 const title=document.createElement('p');title.textContent=`${preview.before.length} current → ${preview.after.length} edited conflict pair${preview.after.length===1?'':'s'} inside ${policy.horizon_min.toFixed(1)} min.`;node.append(title);
 const target=preview.world.aircraft.find(a=>a.aircraft_id===trackEdit!.aircraft_id)!;
 const fields=document.createElement('p');fields.textContent=`${target.aircraft_id}: east ${target.x_nm} NM, north ${target.y_nm} NM, ${target.altitude_ft} FT; vector ${target.vx_nm_min.toFixed(6)} / ${target.vy_nm_min.toFixed(6)} NM/M, climb ${target.climb_ft_min} FT/M.`;node.append(fields);
 const key=(w:TrackEditPreview['before'][number])=>`${w.aircraft_a} / ${w.aircraft_b}`;
 const before=new Map(preview.before.map(w=>[key(w),w])),after=new Map(preview.after.map(w=>[key(w),w]));
 const pairs=[...new Set([...before.keys(),...after.keys()])].sort();
 if(pairs.length){
  const table=document.createElement('table'),caption=document.createElement('caption');caption.textContent='Projected conflict intervals';table.append(caption);
  const head=table.createTHead().insertRow();for(const label of ['Pair','Current interval','Edited interval']){const th=document.createElement('th');th.scope='col';th.textContent=label;head.append(th);}
  const body=table.createTBody();
  const interval=(w:TrackEditPreview['before'][number]|undefined)=>w?`T+${w.start_min.toFixed(2)}–${w.end_min.toFixed(2)} min`:'None';
  for(const pair of pairs){const row=body.insertRow();const th=document.createElement('th');th.scope='row';th.textContent=pair;row.append(th);row.insertCell().textContent=interval(before.get(pair));row.insertCell().textContent=interval(after.get(pair));}
  node.append(table);
 }else{const p=document.createElement('p');p.textContent='No projected conflict in either world inside this policy window.';node.append(p);}
 const note=document.createElement('p');note.textContent='Apply changes this synthetic scenario. Run the planner afterward to evaluate its new world.';node.append(note);
}
function previewSelectedTrack(){
 if(busy||!trackEdit)return;
 try{trackPreview=previewTrackEdit(trackEdit,readTrackFields(),state,policy,now);showTrackPreview(trackPreview);setText('builder-feedback',`Preview ready for ${trackEdit.aircraft_id}. Review the intervals, then Apply or Cancel.`);}
 catch(err){trackPreview=null;setText('track-edit-preview','No current preview. Correct the fields and preview again.');setText('builder-feedback',`NOT PREVIEWED: ${err instanceof Error?err.message:String(err)}`);}
 void render();
}
function finishTrackEdit(){
 if(injectDraft)for(const id of flightFields)$<HTMLInputElement>(id).value=injectDraft[id]!;
 trackEdit=null;trackPreview=null;injectDraft=null;$('track-edit-preview').replaceChildren();
}
function applySelectedTrack(){
 if(busy||!trackEdit||!trackPreview)return;
 try{
  const next=applyTrackEdit(trackEdit,trackPreview,readTrackFields(),state,policy,now),id=trackEdit.aircraft_id;
  state=next;selected=id;clearPending('Track edited. Run the planner on the changed world before approval and readback.');finishTrackEdit();
  setText('builder-feedback',`${id} edited at world version ${state.version}. Existing decision trace retained; previous proposals cleared.`);
  announce(`${id} edited. Run the planner again.`);void render();$('edit-selected-track').focus();
 }catch(err){trackPreview=null;setText('track-edit-preview','The previous preview cannot be applied. Review the error before continuing.');setText('builder-feedback',`NOT APPLIED: ${err instanceof Error?err.message:String(err)}`);void render();}
}
function cancelSelectedTrack(){
 if(busy||!trackEdit)return;const id=trackEdit.aircraft_id;finishTrackEdit();
 setText('builder-feedback',`Edit to ${id} canceled. World and proposal retained; traffic remains paused.`);void render();$('edit-selected-track').focus();
}
function invalidateTrackPreview(){
 if(!trackEdit)return;trackPreview=null;setText('track-edit-preview','Fields changed. Preview again before Apply.');void render();
}
function addTraffic(){pauseTraffic();clearPending('Traffic added. The planner will evaluate the changed world, not an animation script.');let id:string;do{id=`TWR${820+trafficSeq}`;trafficSeq++;}while(state.aircraft.some(a=>a.aircraft_id===id));state={version:state.version+1,observed_at:now,aircraft:[...state.aircraft,{aircraft_id:id,x_nm:0,y_nm:-5,altitude_ft:10000,vx_nm_min:0,vy_nm_min:1,climb_ft_min:0}]};selected=id;void render();}
function addCustomFlight(){pauseTraffic();try{const num=(id:string)=>$<HTMLInputElement>(id).valueAsNumber;const flight=createAircraft({aircraft_id:$<HTMLInputElement>('flight-id').value,x_nm:num('flight-x'),y_nm:num('flight-y'),altitude_ft:num('flight-level')*100,heading_deg:num('flight-bearing'),speed_kt:num('flight-speed'),climb_ft_min:num('flight-climb')});if(state.aircraft.some(a=>a.aircraft_id===flight.aircraft_id))throw new Error(`Callsign ${flight.aircraft_id} already exists.`);state={version:state.version+1,observed_at:now,aircraft:[...state.aircraft,flight]};selected=flight.aircraft_id;clearPending('Visitor-supplied flight added; the solver now evaluates this world.');setText('builder-feedback',`${flight.aircraft_id} injected. Run traffic or ask the planner to solve.`);void render();}catch(err){setText('builder-feedback',`NOT ADDED: ${err instanceof Error?err.message:String(err)}`);}}
function removeSelected(){pauseTraffic();if(state.aircraft.length<=1){setText('builder-feedback','Keep at least one aircraft in the world.');return;}state={version:state.version+1,observed_at:now,aircraft:state.aircraft.filter(a=>a.aircraft_id!==selected)};selected=state.aircraft[0]!.aircraft_id;clearPending('Selected flight removed. Recompute on the remaining live world.');setText('builder-feedback',`${selected} selected; ${state.aircraft.length} aircraft remain.`);void render();}function updatePolicy(){pauseTraffic();policy={...policy,min_horizontal_nm:$<HTMLInputElement>('policy-horizontal').valueAsNumber,min_vertical_ft:$<HTMLInputElement>('policy-vertical').valueAsNumber,horizon_min:$<HTMLInputElement>('policy-horizon').valueAsNumber};setText('horizontal-value',`${policy.min_horizontal_nm.toFixed(1)} NM`);setText('vertical-value',`${policy.min_vertical_ft.toLocaleString()} FT`);setText('horizon-value',`${policy.horizon_min.toFixed(1)} MIN`);clearPending('Safety envelope changed. Re-solve the live world.');void render();}
function exportWorld(){const editor=$<HTMLTextAreaElement>('world-json');editor.value=JSON.stringify(state,null,2);setText('world-json-feedback','Live world exported. Edit tracks, then load your changes.');}
function loadWorld(){try{const next=parseWorldState(JSON.parse($<HTMLTextAreaElement>('world-json').value));pauseTraffic();state=next;now=next.observed_at;selected=next.aircraft[0]!.aircraft_id;pending=null;approval=null;audit=new AuditLog();pythonAudit='[]';clearPending('Visitor WorldState loaded. The solver runs on this exact input.');setText('world-json-feedback',`Loaded ${state.aircraft.length} aircraft at version ${state.version}.`);void render();}catch(err){setText('world-json-feedback',`NOT LOADED: ${err instanceof Error?err.message:String(err)}`);}}function perturbTrack(){pauseTraffic();clearPending('Track changed. The safety policy is being recomputed from the new vector.');state={version:state.version+1,observed_at:now,aircraft:state.aircraft.map(a=>a.aircraft_id===selected?{...a,vx_nm_min:a.vx_nm_min+0.4,vy_nm_min:a.vy_nm_min+0.3}:a)};void render();}
async function runPlanner(){pauseTraffic();busy=true;setText('python-status','Loading real TowerOps Python… (first run only)');await render();try{const result=await towerPython({op:'plan',state,now,policy});const plan:Advisory|null=result.advisory;setText('python-status','Live CPython · towerops.py · AdvisoryPlanner');if(!plan){const has=conflictPairs(state,policy).length>0;clearPending(has?'No admissible maneuver in the bounded candidate set. No state changed.':'No projected conflict. No advisory needed.');if(has)gateScreen='fail';}else{pending=plan;approval=null;proposalMessage='The Python planner found a safe candidate. Review the exact world-bound setpoint, then approve and acknowledge it.';gateScreen='done';gateApproval='wait';gateAck='wait';}}catch(err){clearPending('Python unavailable. No substitute planner or state change.');setText('python-status',String(err));}finally{busy=false;await render();}}
function approvePlan(){if(!pending)return;approval={advisory_hash:pending.advisory_hash,decision:'approve',approved_at:now+0.2,approver:'synthetic-controller'};gateApproval='done';gateAck='wait';proposalMessage='Approval is bound to this advisory hash. Readback is still required before simulated actuation.';void render();}

async function reviewDecisionTrace(raw:string):Promise<DecisionTraceReport>{
 if(busy)throw new Error('Finish the current Python request before reviewing a trace.');
 if(running)throw new Error('Pause traffic before reviewing a decision trace.');
 busy=true;
 try{
  await render();
  const result=await towerPython({op:'review_trace',trace_json:raw});
  if(result.error)throw new Error(result.error);
  return result as DecisionTraceReport;
 }
 finally{busy=false;await render();}
}

async function acceptReadback(){if(busy||!pending||!approval)return;const a=pending,applyNow=now+0.5,ack:Ack={advisory_hash:a.advisory_hash,status:'accepted',acknowledged_at:now+0.4};try{busy=true;await render();const result=await towerPython({op:'apply',state,advisory:a,approval,ack,now:applyNow,policy,audit_json:pythonAudit});pythonAudit=result.audit_json;audit.events=result.events as AuditEvent[];if(result.error)throw new GateRejected(result.error);if(!result.valid)throw new Error('Python audit chain verification failed');state=result.state;setText('python-status','Live CPython · ControlRoom.apply · audit verified');now=applyNow;pending=null;approval=null;gateScreen='done';gateApproval='done';gateAck='done';const n=conflictPairs(state,policy).length;proposalMessage=n?`Actuation is simulated; ${n} conflict pair(s) remain. Run another bounded pass.`:'Simulated setpoint applied. No projected conflict remains in the policy window.';}catch(err){proposalMessage=`GATE REJECTED: ${err instanceof GateRejected?err.reason:String(err)}. No state transition was applied.`;pending=null;approval=null;gateScreen='fail';gateAck='fail';}finally{busy=false;}await render();}
function resetWorld(){pauseTraffic();rate=1;policy={...DEFAULT_POLICY};$<HTMLInputElement>('policy-horizontal').value='5';$<HTMLInputElement>('policy-vertical').value='1000';$<HTMLInputElement>('policy-horizon').value='5';state=copy(fixture.state);now=fixture.now;selected='TWR419';trafficSeq=0;pending=null;approval=null;audit=new AuditLog();pythonAudit='[]';gateScreen='wait';gateApproval='wait';gateAck='wait';proposalMessage='Reset to the crossing scenario from demo.py. Run the bounded planner to propose a safe vector.';$<HTMLInputElement>('speed-range').value='1';void render();}
function frame(t:number){if(!lastFrame)lastFrame=t;const elapsed=Math.min(0.08,Math.max(0,(t-lastFrame)/1000));lastFrame=t;if(running){const minutes=elapsed*rate;now+=minutes*60;state={version:state.version+1,observed_at:now,aircraft:state.aircraft.map(a=>projected(a,minutes))};drawAirspace($<HTMLCanvasElement>('airspace'),state,selected,policy);setText('sim-clock',`T+${Math.floor(now-fixture.now)} SEC`);if(t%250<20)void render();}requestAnimationFrame(frame);}
$('toggle-run').addEventListener('click',()=>{running=!running;lastFrame=0;$('toggle-run').textContent=running?'Pause traffic':'Run traffic';if(running)announce('Traffic is moving from its displayed velocity vectors.');else announce('Traffic paused.');encounterExplorer.update(state,policy,running);});
$('reset-world').addEventListener('click',resetWorld);$('add-traffic').addEventListener('click',addTraffic);$('perturb-track').addEventListener('click',perturbTrack);$('run-planner').addEventListener('click',()=>void runPlanner());$('approve').addEventListener('click',approvePlan);$('readback').addEventListener('click',()=>void acceptReadback());
$('add-custom-flight').addEventListener('click',addCustomFlight);$('remove-selected').addEventListener('click',removeSelected);for(const id of ['policy-horizontal','policy-vertical','policy-horizon'])$(id).addEventListener('input',updatePolicy);$('load-world').addEventListener('click',loadWorld);$('export-world').addEventListener('click',exportWorld);$('verify-audit').addEventListener('click',()=>void audit.verify().then(ok=>setText('audit-verdict',ok?`HASH CHAIN VALID - ${audit.events.length} EVENTS`:'HASH CHAIN INVALID')));$('speed-range').addEventListener('input',e=>{rate=Number((e.currentTarget as HTMLInputElement).value);setText('speed-value',`${rate.toFixed(1)}x`);});
$('edit-selected-track').addEventListener('click',startTrackEdit);$('preview-track-edit').addEventListener('click',previewSelectedTrack);$('apply-track-edit').addEventListener('click',applySelectedTrack);$('cancel-track-edit').addEventListener('click',cancelSelectedTrack);
for(const id of flightFields.filter(id=>id!=='flight-id'))$(id).addEventListener('input',invalidateTrackPreview);
function announce(message:string){setText('announcer',message);}
window.addEventListener('resize',()=>void render());void render();requestAnimationFrame(frame);
