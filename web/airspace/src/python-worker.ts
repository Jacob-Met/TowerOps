// Lazy, off-main-thread CPython. All solver/gate decisions come from towerops.py.
let runtime:Promise<any>|null=null;
async function python(base:string){
 if(!runtime)runtime=(async()=>{
  const url=base+'python/pyodide.mjs';
  const {loadPyodide}=await import(/* @vite-ignore */ url);
  const py=await loadPyodide({indexURL:base+'python/'});
  const response=await fetch(base+'python/towerops.py');
  if(!response.ok)throw new Error('TowerOps Python source could not load');
  py.FS.writeFile('towerops.py',await response.text());
  await py.runPythonAsync(`
import json
from dataclasses import asdict
from towerops import Aircraft, WorldState, SafetyPolicy, AdvisoryPlanner, Advisory, Approval, Ack, ControlRoom, GateRejected

def browser_request(raw):
    q = json.loads(raw)
    s = q['state']
    state = WorldState(s['version'], float(s['observed_at']), tuple(Aircraft(**{k: (v if k == 'aircraft_id' else float(v)) for k,v in a.items()}) for a in s['aircraft']))
    policy = SafetyPolicy(**{k: float(v) for k,v in q['policy'].items()})
    if q['op'] == 'plan':
        plans = AdvisoryPlanner(policy).plan(state, float(q['now']))
        a = plans[0] if plans else None
        return json.dumps({'advisory': dict(asdict(a), advisory_hash=a.advisory_hash) if a else None})
    body = dict(q['advisory'])
    body.pop('advisory_hash', None)
    a = Advisory(**{k: (v if k in ('aircraft_id', 'world_hash', 'rationale') else float(v)) for k,v in body.items()})
    room = ControlRoom(policy)
    room.audit.events = json.loads(q.get('audit_json', '[]'))
    # JSON.stringify drops .0 from whole-number timestamps. Preserve the
    # declared float fields before Python hashes the approval/readback event,
    # just as the state and advisory fields above already do. Otherwise a
    # valid chain can hash 1 here and 1.0 in the browser's canonical verifier.
    # Only restore JSON integer numbers; booleans/strings/null retain their
    # original types so the native gate can reject invalid timestamps.
    approval = Approval(**{k: (float(v) if k == 'approved_at' and type(v) is int else v) for k,v in q['approval'].items()}) if q.get('approval') else None
    ack = Ack(**{k: (float(v) if k == 'acknowledged_at' and type(v) is int else v) for k,v in q['ack'].items()}) if q.get('ack') else None
    try:
        after = room.apply(state, a, approval, ack, float(q['now']))
        return json.dumps({'state': after.to_dict(), 'events': room.audit.events, 'valid': room.audit.verify(room.audit.events), 'audit_json': json.dumps(room.audit.events)})
    except GateRejected as e:
        return json.dumps({'error': e.reason, 'events': room.audit.events, 'audit_json': json.dumps(room.audit.events)})
`);
  return py;
 })().catch(e=>{runtime=null;throw e;});
 return runtime;
}
self.onmessage=async(event)=>{
 const {id,base,request}=event.data;
 try{const py=await python(base);py.globals.set('browser_payload',JSON.stringify(request));const result=JSON.parse(await py.runPythonAsync('browser_request(browser_payload)'));self.postMessage({id,result});}
 catch(e){self.postMessage({id,error:String(e)});}
};
