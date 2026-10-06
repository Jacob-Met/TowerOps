from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from towerops import (
  Ack,
  AdvisoryPlanner,
  Aircraft,
  Approval,
  ControlRoom,
  GateRejected,
  SafetyPolicy,
  WorldState,
)

CASES=[
 ('demo_crossing',WorldState(1,1000.0,(Aircraft('TWR218',-5.0,0.0,10000.0,1.0,0.0),Aircraft('TWR419',5.0,0.0,10000.0,-1.0,0.0)))),
 ('clear_same_track',WorldState(2,2000.0,(Aircraft('TWR218',-10.0,0.0,10000.0,1.0,0.0),Aircraft('TWR419',10.0,0.0,10000.0,1.0,0.0)))),
 ('vertical_separation',WorldState(3,3000.0,(Aircraft('TWR218',-5.0,0.0,10000.0,1.0,0.0),Aircraft('TWR419',5.0,0.0,12000.0,-1.0,0.0)))),
 ('three_way_traffic',WorldState(4,4000.0,(Aircraft('TWR218',-5.0,0.0,10000.0,1.0,0.0),Aircraft('TWR419',5.0,0.0,10000.0,-1.0,0.0),Aircraft('TWR820',0.0,8.0,10000.0,0.0,-1.6)))),
]
def result(name,state,policy):
 now=state.observed_at+2.0; before=state.to_dict()
 pairs=[[a.aircraft_id,b.aircraft_id] for i,a in enumerate(state.aircraft) for b in state.aircraft[i+1:] if policy._pair_conflict(a,b)]
 advisories=AdvisoryPlanner(policy).plan(state,now); advisory=asdict(advisories[0]) if advisories else None; advisory_hash=advisories[0].advisory_hash if advisories else None
 out={'name':name,'state':before,'world_hash':state.world_hash,'now':now,'before_conflict':policy.state_has_conflict(state),'conflict_pairs':pairs,'conflicting_aircraft':[a.aircraft_id for a in policy.conflicting_aircraft(state)],'advisory':advisory,'advisory_hash':advisory_hash,'after_state':None,'after_world_hash':None,'after_conflict':None,'audit_events':[],'audit_valid':True,'missing_ack':None}
 if advisory:
  a=advisories[0]; approval=Approval(a.advisory_hash,'approve',now+0.2,'synthetic-controller'); ack=Ack(a.advisory_hash,'accepted',now+0.4)
  room=ControlRoom(policy); after=room.apply(state,a,approval,ack,now+0.5)
  out.update(after_state=after.to_dict(),after_world_hash=after.world_hash,after_conflict=policy.state_has_conflict(after),audit_events=room.audit.events,audit_valid=room.audit.verify(room.audit.events))
  denied=ControlRoom(policy)
  try: denied.apply(state,a,approval,None,now+0.5)
  except GateRejected as exc: out['missing_ack']={'reason':exc.reason,'events':denied.audit.events,'state_unchanged':state.to_dict()==before}
 return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
 policy=SafetyPolicy(); data={'source':'TowerOps Python SafetyPolicy, AdvisoryPlanner, ControlRoom; generated from real runs','policy':asdict(policy),'scenarios':[result(n,s,policy) for n,s in CASES]}
 path=ROOT/'web/airspace/tests/python-reference.json'; payload=json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+chr(10)
 if args.check:
  if not path.exists() or path.read_text(encoding='utf-8')!=payload: raise SystemExit('Python reference fixture differs; regenerate from TowerOps source')
  print('Python reference OK:',len(data['scenarios']),'real-source scenarios')
 else:
  path.parent.mkdir(parents=True,exist_ok=True); path.write_text(payload,encoding='utf-8'); print('Wrote',path.relative_to(ROOT),'from TowerOps Python')
if __name__=='__main__': main()
