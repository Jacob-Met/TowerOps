// Lazy, off-main-thread CPython. All solver/gate decisions come from towerops.py.
let runtime:Promise<any>|null=null;
let alternativesModule:Promise<void>|null=null;
async function loadAlternatives(py:any,base:string):Promise<void>{
 if(!alternativesModule)alternativesModule=(async()=>{
  const response=await fetch(base+'python/advisory_options.py');
  if(!response.ok)throw new Error('TowerOps alternatives source could not load');
  py.FS.writeFile('advisory_options.py',await response.text());
  await py.runPythonAsync('import advisory_options');
 })().catch(e=>{alternativesModule=null;throw e;});
 return alternativesModule;
}
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
from towerops import Aircraft, WorldState, SafetyPolicy, AdvisoryPlanner, Advisory, Approval, Ack, ControlRoom, GateRejected, canonical_bytes

def browser_audit(room):
    return {
        'events': room.audit.events,
        'audit_canonical': [canonical_bytes({k: v for k, v in event.items() if k != 'event_hash'}).decode('utf-8') for event in room.audit.events],
        'audit_json': json.dumps(room.audit.events),
    }

def browser_request(raw):
    q = json.loads(raw)
    if q.get('op') == 'review_trace':
        from decision_trace import review_trace
        try:
            return json.dumps(review_trace(q.get('trace_json')), allow_nan=False)
        except (TypeError, ValueError) as error:
            return json.dumps({'error': str(error)})
    s = q['state']
    state = WorldState(s['version'], float(s['observed_at']), tuple(Aircraft(**{k: (v if k == 'aircraft_id' else float(v)) for k,v in a.items()}) for a in s['aircraft']))
    policy = SafetyPolicy(**{k: float(v) for k,v in q['policy'].items()})
    if q['op'] == 'options':
        from advisory_options import review_advisory_options
        review = review_advisory_options(state, float(q['now']), policy)
        return json.dumps({
            'world_hash': review.world_hash,
            'reviewed_at': review.reviewed_at,
            'candidate_count': review.candidate_count,
            'advisories': [dict(asdict(a), advisory_hash=a.advisory_hash) for a in review.advisories],
        })
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
        return json.dumps({'state': after.to_dict(), 'valid': room.audit.verify(room.audit.events), **browser_audit(room)})
    except GateRejected as e:
        return json.dumps({'error': e.reason, **browser_audit(room)})
`);
  return py;
 })().catch(e=>{runtime=null;throw e;});
 return runtime;
}
// Replay is an optional, read-only consumer. A missing replay module must not
// prevent the existing planner/apply path from starting or being retried.
let replaySources:Promise<void>|null=null;
async function loadReplaySources(py:any,base:string):Promise<void>{
 if(!replaySources)replaySources=(async()=>{
  for(const name of ['audit_replay.py','decision_trace.py']){
   const response=await fetch(base+'python/'+name);
   if(!response.ok)throw new Error('Decision replay Python source could not load');
   py.FS.writeFile(name,await response.text());
  }
 })().catch(e=>{replaySources=null;throw e;});
 return replaySources;
}
self.onmessage=async(event)=>{
 const {id,base,request}=event.data;
 try{const py=await python(base);if(request?.op==='review_trace')await loadReplaySources(py,base);if(request.op==='options')await loadAlternatives(py,base);py.globals.set('browser_payload',JSON.stringify(request));const result=JSON.parse(await py.runPythonAsync('browser_request(browser_payload)'));self.postMessage({id,result});}
 catch(e){self.postMessage({id,error:String(e)});}
};
