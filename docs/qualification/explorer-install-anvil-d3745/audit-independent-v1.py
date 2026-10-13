"""Independent read-only audit of Loom's single installed-use course; no product replay."""
import datetime,hashlib,json,stat
from pathlib import Path
ROOT=Path('/home/jacob/hamon/receiving/anvil-d3745-towerops-install')
PEER=Path('/home/jacob/hamon/receiving/loom-d3745-towerops-install')
def need(ok,message):
 if not ok:raise RuntimeError(message)
def sha(b):return hashlib.sha256(b).hexdigest()
def ident(path):
 p=Path(path);s=p.lstat();need(stat.S_ISREG(s.st_mode),'regular '+str(p));b=p.read_bytes()
 return dict(path=str(p),bytes=len(b),sha256=sha(b),mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,inode=s.st_ino,mtime_ns=s.st_mtime_ns)
def pinned(path,size,digest):
 b=Path(path).read_bytes();need(len(b)==size and sha(b)==digest,'pin '+str(path));return b
receipt_path=PEER/'course-v3/receipt.json'
raw=pinned(receipt_path,128367,'128b03c2159099a7928289f85b07adfd4c247ffcc5fcee4cb40e24cc677ab928')
r=json.loads(raw)
c=json.loads(pinned(PEER/'criteria-v1.json',23882,'5c3835e230b9a8acc36653b5ba17b8e5bbee07b833032541e1f28229c3b5c26c'))
pinned(PEER/'receive-install-v3.py',17262,'5dc6ce13f7a58e04b098e4c43db9cbdf63081e454be715e5152d28e5f40a3d77')
need(r['accepted'] is True and r['errors']==[],'accepted clean receipt')
need(len(r['checks'])==119 and len({q['name'] for q in r['checks']})==119,'exact unique checks')
for q in r['checks']:need(q['pass'] is True and q['actual']==q['expected'],'actual/expected '+q['name'])
need(len(r['inputs_before'])==25 and r['inputs_before']==r['inputs_after'],'all recorded input identities')
for row in r['inputs_before']:need(ident(row['path'])==row,'full native input identity '+row['path'])
need([q['exit_code'] for q in r['commands']]==[0,2],'first/repeat exits')
need([q['pid'] for q in r['commands']]==[106601,106614],'original command PIDs')
need(r['server']['argv']==['towerops-explorer','--port','0'] and r['server']['exit_code']==0,'PATH server close')
need(r['server']['pid']==106602 and r['server']['port']==37529,'server identity')
need(r['installed_before_use']==r['installed_after_repeat'],'all recorded installed entries/selector')
need(r['final_namespace']==r['installed_before_use']['namespace'],'recorded final namespace')
need(r['transport_home_observation']['passwd_home']=='/home/jacob' and r['transport_home_observation']['environment_changed'] is False,'home clarification')
streams=[]
for q in r['commands']+[r['server']]:
 for k in ('stdout','stderr'):
  row=q[k];need(ident(row['path'])==row,'raw process stream '+row['path']);streams.append(row)
need(len(r['http'])==6,'six HTTP requests')
for i,row in enumerate(r['http']):
 for k in ('request_body','response_body'):
  need(ident(row[k]['path'])==row[k],'raw HTTP body '+row[k]['path']);streams.append(row[k])
 body=Path(row['response_body']['path']).read_bytes()
 req=Path(row['request_body']['path']).read_bytes()
 if i<3:
  leaf=['web/index.html','web/app.js','web/style.css'][i]
  need(row['method']=='GET' and row['path']==['/','/app.js','/style.css'][i] and row['status']==200,'static request')
  need(req==b'' and body==(PEER/'source'/leaf).read_bytes(),'exact static bytes')
 else:
  oracle=c['original_oracles']['http'][i-3]
  need((row['method'],row['path'],row['status'])==(oracle['method'],oracle['path'],oracle['expected_status']),'prior oracle HTTP metadata')
  need(req==oracle['request_body'].encode() and body==oracle['expected_body'].encode(),'full prior API oracle bytes')
need(len(streams)==18,'18 complete raw streams')
install=r['installer_receipt'];need(ident(install['path'])==install,'original installer receipt identity')
need(json.loads(Path(install['path']).read_bytes())==r['installer_receipt_object'],'installer receipt complete object')
need(r['installer_receipt_object']['ok'] is True,'installer acknowledged success')
stdout=Path(r['commands'][0]['stdout']['path']).read_text()
repeat=Path(r['commands'][1]['stderr']['path']).read_text()
need(json.loads(stdout)['ok'] is True,'first stdout success')
need(Path(r['commands'][0]['stderr']['path']).read_bytes()==b'' and Path(r['commands'][1]['stdout']['path']).read_bytes()==b'','first clean/repeat no success output')
need('Traceback' not in repeat,'repeat controlled refusal')
need(not (PEER/'course-v3/repeat-receipt.json').exists(),'admission repeat creates no receipt')
need(len(r['installed_before_use']['namespace']['entries'])==14,'recorded complete namespace: four dirs and ten regular files')
record={
 'schema':'hamon.anvil.explorer-install-independent-receiving-review.v1',
 'accepted':True,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'method':'Full frozen receiver/criteria/raw receipt read plus independent native read-only recomputation. No installer, server, network connection, browser or prior course replay.',
 'source_installer':{'bytes':12558,'sha256':'2177f9c8c77c54056cd6f1e0b0ff4cddd1302a694020a035bd8e6ae39d6996a7'},
 'criteria':ident(PEER/'criteria-v1.json'),'receiver':ident(PEER/'receive-install-v3.py'),
 'original_receipt':ident(receipt_path),'checks_recomputed':119,'inputs_complete_native_identities_checked':25,
 'raw_streams':streams,'raw_streams_count':len(streams),'http_requests':6,'commands':[{'label':q['label'],'pid':q['pid'],'exit_code':q['exit_code']} for q in r['commands']],
 'server':{'argv':r['server']['argv'],'pid':106602,'port':37529,'recorded_exit':0,'recorded_closed_port_check':True},
 'conclusions':[
 'One actual first installation succeeds, real PATH wrapper launches the fixed relocated runtime from an unrelated working directory, and all three served assets and three complete original HTTP body oracles are exact.',
 'Recorded installed namespace and selector identities are equal through explicit use/shutdown and repeated-install refusal. All three original Tsuka bindings remain equal in the complete checked receipt.',
 'Exact native before/after metadata and current passive input/stream readback are compared in Python; no nanosecond authority is inferred from a JavaScript projection.',
 'Original v2 HOME admission failure remains separate; v3 uses passwd home with unmodified transport environment. No product changes or automatic repeat were introduced.',
 'Complete installed-use proof remains separate from 13+13 temporary author methods and prior 85+10 browser qualification.'],
 'limits':['This is a passive audit of the one original receiving course, not a second behavioral run.','The receipt records process/port closure; this audit opens no port and does not rerun server shutdown.','No power-loss, arbitrary concurrent writer, upgrade, rollback, cross-platform or new browser claim.'],
 'audit_source':ident(Path(__file__))
}
out=ROOT/'inputs/independent-receiving-review.json'
with out.open('x') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
b=out.read_bytes();print(json.dumps({'accepted':True,'path':str(out),'bytes':len(b),'sha256':sha(b),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'checks':119,'inputs':25,'streams':18,'process_stream_text':[{'label':q['label'],'stdout':Path(q['stdout']['path']).read_text(),'stderr':Path(q['stderr']['path']).read_text()} for q in r['commands']],'server_stdout':Path(r['server']['stdout']['path']).read_text(),'server_stderr':Path(r['server']['stderr']['path']).read_text()}))
