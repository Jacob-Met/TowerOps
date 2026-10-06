import '../style.css';
import reference from '../tests/python-reference.json';
import { Aircraft,DEFAULT_POLICY,WorldState,conflictPairs,projected } from './core';
import { Advisory,planAdvisory } from './planner';
import { AuditLog } from './audit';
import { Ack,Approval,GateRejected } from './gate';
import { applyAdvisory } from './actuation';
import { drawAirspace } from './draw';
type Scenario={name:string;state:WorldState;now:number};
const fixture=(reference as unknown as {scenarios:Scenario[]}).scenarios[0]!;
const $=<T extends HTMLElement>(id:string)=>document.getElementById(id) as T;
const copy=(s:WorldState):WorldState=>JSON.parse(JSON.stringify(s)) as WorldState;
let state=copy(fixture.state),now=fixture.now,selected='TWR419',running=false,pending:Advisory|null=null,approval:Approval|null=null,audit=new AuditLog();
let rate=1,lastFrame=0,trafficSeq=0;
type GateState='wait'|'done'|'fail'; let gateScreen:GateState='wait',gateApproval:GateState='wait',gateAck:GateState='wait';
function setText(id:string,value:string){$(id).textContent=value;}
function gate(id:string,status:'wait'|'done'|'fail',label:string){const node=$(id);node.className=`gate-step ${status}`;const i=node.querySelector('i');if(i)i.textContent=label;}
function drawLists(pairs:Array<[string,string]>){
 const flights=$('flight-list');flights.replaceChildren();
 for(const a of state.aircraft){const row=document.createElement('div');row.className=`flight-row ${selected===a.aircraft_id?'selected':''}`;const b=document.createElement('button');b.textContent=a.aircraft_id;b.onclick=()=>{selected=a.aircraft_id;render();};const meta=document.createElement('span');meta.className='flight-meta';meta.textContent=`${Math.round(a.altitude_ft/100)} FL / ${a.vx_nm_min.toFixed(1)}, ${a.vy_nm_min.toFixed(1)} NM/M`;row.append(b,meta);flights.append(row);}
 const watch=$('conflict-list');watch.replaceChildren();
 for(const [a,b] of pairs){const row=document.createElement('div');row.className='conflict-row';const label=document.createElement('span');label.textContent=`${a} / ${b}`;const meta=document.createElement('span');meta.className='conflict-meta';meta.textContent='HORIZONTAL + VERTICAL';row.append(label,meta);watch.append(row);}
 if(!pairs.length){const p=document.createElement('p');p.className='fine-print';p.textContent='No pair enters both unsafe intervals inside the policy horizon.';watch.append(p);}
 setText('flight-count',`${state.aircraft.length} FLIGHTS`);
}
let proposalMessage='No proposal yet. The planner only returns a setpoint if it clears the separation policy.';
async function render():Promise<void>{
 const pairs=conflictPairs(state,DEFAULT_POLICY);drawAirspace($<HTMLCanvasElement>('airspace'),state,selected,DEFAULT_POLICY);drawLists(pairs);
 const badge=$('world-badge');badge.className=`badge ${pairs.length?'alert':'safe'}`;badge.textContent=pairs.length?'ACTION':'CLEAR';
 setText('world-title',pairs.length?`${pairs.length} conflict pair${pairs.length===1?'':'s'} inside policy envelope`:'No projected conflict');
 setText('world-note',pairs.length?'Horizontal and vertical unsafe-time intervals overlap inside the five-minute horizon.':'No simultaneous horizontal and vertical intrusion inside the five-minute horizon.');
 setText('pair-count',String(pairs.length));setText('sim-clock',`T+${Math.max(0,Math.floor(now-fixture.now))} SEC`);setText('speed-value',`${rate.toFixed(1)}x`);
 setText('proposal-state',pending?'PROPOSAL READY':pairs.length?'NEEDS REVIEW':'IDLE');
 if(pending)setText('proposal-output',`${pending.aircraft_id} -> vx ${pending.set_vx_nm_min.toFixed(1)} / vy ${pending.set_vy_nm_min.toFixed(1)} NM/M / climb ${pending.set_climb_ft_min} FT/M. Bound to ${pending.world_hash.slice(0,10)}.`);else setText('proposal-output',proposalMessage);
 gate('gate-screen',gateScreen,gateScreen==='done'?'PASS':gateScreen==='fail'?'FAIL':'WAIT');gate('gate-approval',gateApproval,gateApproval==='done'?'APPROVED':gateApproval==='fail'?'REJECTED':'WAIT');gate('gate-ack',gateAck,gateAck==='done'?'ACCEPTED':gateAck==='fail'?'REJECTED':'WAIT');
 $('run-planner').toggleAttribute('disabled',!pairs.length||!!pending);$('approve').toggleAttribute('disabled',!pending||!!approval);$('readback').toggleAttribute('disabled',!pending||!approval);$('toggle-run').toggleAttribute('disabled',!!pending);
 const valid=await audit.verify();setText('audit-status',`${audit.events.length} EVENT${audit.events.length===1?'':'S'} / ${valid?'VALID':'BROKEN'}`);
 const list=$('audit-events');list.replaceChildren();for(const e of audit.events){const li=document.createElement('li');li.textContent=`${String(e.seq).padStart(2,'0')}  ${e.kind}  ${e.event_hash.slice(0,12)}`;list.append(li);}
}

function clearPending(message:string){pending=null;approval=null;proposalMessage=message;gateScreen='wait';gateApproval='wait';gateAck='wait';}
function addTraffic(){running=false;clearPending('Traffic added. The planner will evaluate the changed world, not an animation script.');const id=`TWR${820+trafficSeq}`;trafficSeq++;state={version:state.version+1,observed_at:now,aircraft:[...state.aircraft,{aircraft_id:id,x_nm:0,y_nm:-5,altitude_ft:10000,vx_nm_min:0,vy_nm_min:1,climb_ft_min:0}]};selected=id;void render();}
function perturbTrack(){running=false;clearPending('Track changed. The safety policy is being recomputed from the new vector.');state={version:state.version+1,observed_at:now,aircraft:state.aircraft.map(a=>a.aircraft_id===selected?{...a,vx_nm_min:a.vx_nm_min+0.4,vy_nm_min:a.vy_nm_min+0.3}:a)};void render();}
async function runPlanner(){running=false;const plan=await planAdvisory(state,now,DEFAULT_POLICY);if(!plan){const has=conflictPairs(state).length>0;clearPending(has?'No admissible maneuver in the bounded candidate set. No state changed.':'No projected conflict. No advisory needed.');if(has)gateScreen='fail';}else{pending=plan;approval=null;proposalMessage='The Python planner found a safe candidate. Review the exact world-bound setpoint, then approve and acknowledge it.';gateScreen='done';gateApproval='wait';gateAck='wait';}await render();}
function approvePlan(){if(!pending)return;approval={advisory_hash:pending.advisory_hash,decision:'approve',approved_at:now+0.2,approver:'synthetic-controller'};gateApproval='done';gateAck='wait';proposalMessage='Approval is bound to this advisory hash. Readback is still required before simulated actuation.';void render();}

async function acceptReadback(){if(!pending||!approval)return;const a=pending,applyNow=now+0.5,ack:Ack={advisory_hash:a.advisory_hash,status:'accepted',acknowledged_at:now+0.4};try{state=await applyAdvisory(state,a,approval,ack,applyNow,audit,DEFAULT_POLICY);now=applyNow;pending=null;approval=null;gateScreen='done';gateApproval='done';gateAck='done';const n=conflictPairs(state).length;proposalMessage=n?`Actuation is simulated; ${n} conflict pair(s) remain. Run another bounded pass.`:'Simulated setpoint applied. No projected conflict remains in the policy window.';}catch(err){proposalMessage=`GATE REJECTED: ${err instanceof GateRejected?err.reason:String(err)}. No state transition was applied.`;pending=null;approval=null;gateScreen='fail';gateAck='fail';}await render();}
function resetWorld(){running=false;state=copy(fixture.state);now=fixture.now;selected='TWR419';trafficSeq=0;pending=null;approval=null;audit=new AuditLog();gateScreen='wait';gateApproval='wait';gateAck='wait';proposalMessage='Reset to the crossing scenario from demo.py. Run the bounded planner to propose a safe vector.';$<HTMLInputElement>('speed-range').value='1';$('toggle-run').textContent='Run traffic';void render();}
function frame(t:number){if(!lastFrame)lastFrame=t;const elapsed=Math.min(0.08,Math.max(0,(t-lastFrame)/1000));lastFrame=t;if(running){const minutes=elapsed*rate;now+=minutes*60;state={version:state.version+1,observed_at:now,aircraft:state.aircraft.map(a=>projected(a,minutes))};drawAirspace($<HTMLCanvasElement>('airspace'),state,selected,DEFAULT_POLICY);setText('sim-clock',`T+${Math.floor(now-fixture.now)} SEC`);if(t%250<20)void render();}requestAnimationFrame(frame);}
$('toggle-run').addEventListener('click',()=>{running=!running;lastFrame=0;$('toggle-run').textContent=running?'Pause traffic':'Run traffic';if(running)announce('Traffic is moving from its displayed velocity vectors.');else announce('Traffic paused.');});
$('reset-world').addEventListener('click',resetWorld);$('add-traffic').addEventListener('click',addTraffic);$('perturb-track').addEventListener('click',perturbTrack);$('run-planner').addEventListener('click',()=>void runPlanner());$('approve').addEventListener('click',approvePlan);$('readback').addEventListener('click',()=>void acceptReadback());
$('speed-range').addEventListener('input',e=>{rate=Number((e.currentTarget as HTMLInputElement).value);setText('speed-value',`${rate.toFixed(1)}x`);});
function announce(message:string){setText('announcer',message);}
window.addEventListener('resize',()=>void render());void render();requestAnimationFrame(frame);
