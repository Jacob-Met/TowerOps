"""Read-only receiving custody audit; never imports or executes TowerOps."""
from pathlib import Path
import hashlib,json,datetime,stat,os
BASE=Path('/home/jacob/hamon/receiving/loom-d3745-towerops-explain')
OUT=Path('/home/jacob/hamon/receiving/anvil-d3745-browser-explain-publication')
def sha(b):return hashlib.sha256(b).hexdigest()
def ident(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink(),p
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'mode':oct(s.st_mode&511)}
def verify(r):
 got=ident(r['path'])
 assert all(got[k]==r[k] for k in ('bytes','sha256','mode')),r['path']
 return got
def exact(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
 return a==b
results=[]
for variant,name in [('original','original-v1'),('candidate','candidate-v2')]:
 p=BASE/name/'receipt.json';raw=p.read_bytes();r=json.loads(raw);assert r['variant']==variant
 assert len(r['checks'])==(15 if variant=='original' else 85)
 assert all(x['pass'] and exact(x['actual'],x['expected']) for x in r['checks'])
 assert exact(r['source_before'],r['source_after']) and exact(r['controls_before'],r['controls_after']) and exact(r['fixtures_before'],r['fixtures_after'])
 current=[verify(x) for category in ('source_before','controls_before','fixtures_before') for x in r[category]]
 streams=[]
 for row in r['http']:
  body=Path(row['backend_stream']['path']).read_bytes();streams.append(verify(row['backend_stream']))
  assert body==row['backend_body'].encode('utf-8') and sha(body)==row['backend_sha256'] and len(body)==row['backend_bytes']
  if 'request_stream' in row:
   body=Path(row['request_stream']['path']).read_bytes();streams.append(verify(row['request_stream']))
   assert body==row['request_body'].encode('utf-8') and exact(json.loads(body),row['request_json'])
  if not row.get('authored_fault'):assert row['backend_body']==row['delivered_body'] and row['backend_status']==row['delivered_status']
 for k in ('backend_stdout','backend_stderr'):streams.append(verify(r[k]))
 shots=[verify(x) for x in r['screenshots']]
 assert len(streams)==(13 if variant=='original' else 33)
 assert r['error'] is None and r['failed_checks']==[] and r['backend_exit']=={'code':0,'signal':None} and r['browser_exit_code']==0
 assert r['browser_closed'] and r['backend_closed'] and r['relay_closed']
 if variant=='original':
  assert r['accepted'] is False and r['open_relay_sockets']==1 and sha(raw)=='c5da677c7ac6bdd91b7064265e2ecc56ce152dca355b21d079a28b0ad39e37c1'
 else:
  assert r['accepted'] is True and r['open_relay_sockets']==0
  assert sum(bool(x.get('authored_fault')) for x in r['http'])==1
  assert sum(bool(x.get('authored_delay')) for x in r['http'])==1
  assert len([x for x in r['request_finished'] if x['label']==r['held_response_label']])==1
 results.append({'variant':variant,'receipt':ident(p),'checks_recomputed':len(r['checks']),'http':len(r['http']),'posts':sum(x['method']=='POST' for x in r['http']),'exact_current_input_files':len(current),'raw_streams':streams,'screenshots':shots,'raw_accepted':r['accepted'],'open_relay_sockets':r['open_relay_sockets'],'backend_exit':r['backend_exit'],'browser_exit':r['browser_exit_code']})
pins={'prepare_git_objects.py':'fb6596df63889b6b72038e3921b9144b802cc9546f9617705cfd112b57dab676','receive_source.py':'90af676b35c39f3cb1a3295d94a31a752893265af3a73292e2b2b22fb2750f35','validate_publication_layout.py':'09e931bcdb5d1ec5e55d76c8123a973a75a2d5072c6ffb84b302ddac8f443907'}
for n,h in pins.items():assert sha((OUT/'tools'/n).read_bytes())==h
for n,h in [('issue132-source-review-v1.json','5f880d4e03ac1a30633b1a3ef8c1a10d59279378998c1112ed4bbb167810c344'),('issue132-harness-review-v1.json','feba5db505f339e30097cd4c6853554d9fe737a7d27ec049993f37b9d86947ba')]:
 assert sha((OUT/'inputs'/n).read_bytes())==h
receipt={'schema':'hamon.anvil.towerops-explain-browser-review.v1','accepted':True,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'Anvil','courses':results,'findings':['All100 original/candidate actual/expected comparisons independently recomputed;46 raw streams rehashed and backend/request bodies exactly match raw receipt UTF-8 text.','Candidate85 checks observe actual production Handler through disclosed relay: ordered one-field, typed/missing/unexpected full literal values,32-row cap notice, explicit503 recovery, selection retirement after unique held-response completion, clear, collapse/expand and unchanged displayed run.','Candidate source/control/fixture paths and all five original/candidate screenshots retain full byte/mode identities.','Visually inspected B/C screenshots: current mismatch, action, completed status and open details counts1/3 visible. Literal rows themselves are below the1100px viewport; exact full values are DOM/HTTP receipt observations.','Original raw accepted=false/socket1 remains intact; separate original-closure-audit reports subsequent process/listener closure. Candidate itself records browser/backend0 and relay socket0.'],'limits':['No product/browser re-execution or model/network provider call by reviewer.','Not a production framing, remote service or OS-wide network audit. Relay explicitly rewrites loopback Host/Origin and supplies one503 and one partial-body delay.','File selection is actual browser API selection; clear is an authored DOM change. Existing exported bytes were not redownloaded in this receiving course.','Original subsequent process/listener absence is peer-audited, not freshly probed by this reviewer.']}
b=(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n').encode();target=OUT/'inputs/issue132-browser-review-v1.json'
with target.open('xb') as f:f.write(b)
print(json.dumps({'path':str(target),'bytes':len(b),'sha256':sha(b),'courses':[{'variant':x['variant'],'checks':x['checks_recomputed'],'streams':len(x['raw_streams']),'receipt':x['receipt']} for x in results]}))
