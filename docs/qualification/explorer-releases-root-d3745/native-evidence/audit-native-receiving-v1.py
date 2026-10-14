from pathlib import Path
import json,hashlib,base64,stat,datetime,shlex,re
B=Path('/workspace/scratch/d3745ea0f44f');P=B/'anvil/towerops-release-native';M=P/'native-mirror';N='/home/jacob/hamon/receiving/anvil-d3745-towerops-release-native/';DIG='82d3ab784c221b9fa320edbfc0a6f725a5beb8c293d0681646fedcfb880e0216';REL='/home/jacob/.local/share/towerops/explorer/releases/'+DIG
load=lambda p:json.loads(p.read_bytes())
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def eq(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))
def bind(b,row):assert all(ident(b)[k]==row[k] for k in ['bytes','sha256','git_blob'])
r=load(M/'native-v1/receipt.json');assert ident((M/'native-v1/receipt.json').read_bytes())['sha256']=='e78c3c336505dab5599ea1a29a6bc09f7bf39cce95a75d8e159268175521ad5a'
assert r['accepted'] is True and len(r['checks'])==69 and all(x['passed'] is True for x in r['checks']);assert not any(k in r for k in ['error','preservation_error','failure_cleanup','cleanup_error'])
assert eq(r['before'],r['after']) and eq(r['neighbors_before'],r['neighbors_after']) and eq(r['installed_before_commands'],r['installed_after_commands'])
assert len(r['neighbors_before'])==10 and r['identity']['uid']==1000 and r['identity']['user']=='jacob' and r['identity']['passwd_home']=='/home/jacob'
transfer=load(P/'transfer-custody-v1.json');assert len(transfer['files'])==19
for row in transfer['files']:
 p=M/row['path'];bind(p.read_bytes(),row);assert stat.S_IMODE(p.stat().st_mode)==row['mode']
packet=load(P/'staging-packet-v1.json');captured={}
for row in packet['files']:
 b=base64.b64decode(row['base64'],validate=True);bind(b,row);captured[row['path']]=b
 for k,v in ident(b).items():assert r['before'][N+row['path']][k]==v
 assert r['before'][N+row['path']]['mode']==row['mode']
assert len(captured)==19
for rel in ['native-release-v1.json','native-spec-v1.json']:bind((M/rel).read_bytes(),r['before'][N+rel])
f=load(P/'freeze-v1.json')
for path,row in f['files'].items():
 b=(P/path).read_bytes();assert b==captured[path] and len(b)==row['bytes'] and ident(b)['sha256']==row['sha256']
assert r['spec']['tool_commit']=='8b99316b2537a383c40e8a92e924ce4f7e597cc1' and r['spec']['feature_commit']=='c68d148b7941e40f16af2230c46391f4ec3dbdc0'
release=load(M/'native-release-v1.json');assert release['authorized'] is True and release['controller_sha256']==ident(captured['receive-native-v1.py'])['sha256'] and ident((M/'native-release-v1.json').read_bytes())['sha256']==r['spec']['root_release']['sha256']
content=load(P/'expected-content-v1.json');assert ident((P/'expected-content-v1.json').read_bytes())['sha256']==DIG
remote=load(B/'forge/reviews/towerops-settings-kit-source-bindings-v1.json');rem={x['path']:x for x in remote['files']}
for row in content['files']:
 b=captured['source/'+row['path']];assert (len(b),ident(b)['sha256'])==(row['bytes'],row['sha256']);rt=rem[row['path']];assert (rt['sha'],rt['size'],int(rt['mode'],8)&0o777)==(ident(b)['git_blob'],len(b),row['mode'])
 for k,v in ident(b).items():assert r['installed_before_commands'][row['path']][k]==v
 assert r['installed_before_commands'][row['path']]['mode']==row['mode']
assert len(r['commands'])==3 and [x['name'] for x in r['commands']]==['install','help','server']
for row in r['commands']:
 for stream in ['stdout','stderr']:bind((M/'native-v1'/(row['name']+'.'+stream)).read_bytes(),row[stream])
 if row['name']!='server':assert row['exit']==0 and row['group_absent'] is True
 else:assert eq(row['closure'],{'exit':0,'actions':['SIGINT'],'group_absent':True})
assert transfer['all_course_pids_absent']==[r['pid']]+[x['pid'] for x in r['commands']]
assert r['commands'][1]['argv']==['towerops-explorer-82d3ab784c22','--help'] and r['commands'][2]['argv']==['towerops-explorer-82d3ab784c22','--port','0']
assert (M/'native-v1/install.stderr').read_bytes()==b'' and (M/'native-v1/help.stderr').read_bytes()==b''
assert b'usage: explorer.py serve' in (M/'native-v1/help.stdout').read_bytes()
assert ('http://127.0.0.1:'+str(r['port'])).encode() in (M/'native-v1/server.stdout').read_bytes()
assert len(r['http'])==3 and [x['path'] for x in r['http']]==['/','/app.js','/style.css']
for row,path in zip(r['http'],['web/index.html','web/app.js','web/style.css']):
 b=(M/'native-v1'/Path(row['body']).name).read_bytes();bind(b,row['identity']);assert b==captured['source/'+path] and row['method']=='GET' and row['status']==200 and row['headers']['Cache-Control']=='no-store'
assert re.findall(r'"(GET [^\"]+)" 200 -', (M/'native-v1/server.stderr').read_text())==['GET / HTTP/1.1','GET /app.js HTTP/1.1','GET /style.css HTTP/1.1']
installed=load(M/'native-v1/installation-receipt.json');assert eq(installed,r['installation_receipt']) and installed['ok'] is True and installed['phase']=='complete'
summary=load(M/'native-v1/install.stdout');assert eq(summary,{k:installed[k] for k in ['digest','ok','receipt','release','selector']})
wrapper=('#!/bin/sh\nexec /usr/bin/python3 -B '+shlex.quote(REL+'/explorer.py')+' serve "$@"\n').encode();assert wrapper==(M/'installed/towerops-explorer').read_bytes();bind(wrapper,installed['installed']['towerops-explorer'])
prov=load(M/'installed/installation.json');assert eq(prov['manifest'],content) and eq(prov['wrapper'],ident(wrapper)) and prov['digest']==DIG
for name,row in installed['inputs'].items():assert all(eq(v,r['before'][N+'source/'+name][k]) for k,v in row.items())
for name,row in installed['installed'].items():assert all(eq(v,r['installed_after_commands'][name][k]) for k,v in row.items())
assert set(installed['inputs'])=={x['path'] for x in content['files']};assert set(installed['installed'])==set(installed['inputs'])|{'towerops-explorer','installation.json'}
assert set(r['installed_after_commands'])==set(installed['installed'])|{'.','web'}
for name,row in r['namespace_before'].items():
 after=r['namespace_after'][name]
 if name=='explorer':assert all(eq(row[k],after[k]) for k in ['present','kind','device','inode','mode','uid','gid'])
 else:assert eq(row,after)
new=set(r['namespace_after'])-set(r['namespace_before']);expected={'explorer/releases','explorer/releases/'+DIG}|{'explorer/releases/'+DIG+'/'+name for name in set(installed['installed'])|{'web'}};assert new==expected
expected_created=[installed['receipt'],'/home/jacob/.local/share/towerops/explorer/releases',REL,REL+'/web']+[REL+'/'+x['path'] for x in content['files']]+[REL+'/towerops-explorer',REL+'/installation.json',installed['selector']];assert installed['created']==expected_created
outer=load(M/'native-v1.stdout');assert outer['accepted'] is True and outer['checks']==69 and outer['commands']==3 and outer['http']==3 and outer['failed']==[];assert (M/'native-v1.stderr').read_bytes()==b''
out={'schema':'hamon.forge.towerops-native-release-review.v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'accepted','scope':'Read-only full controller/receipt, raw streams, mirrored bytes, source bindings and reported installed-state review. No product/native execution or fresh process query.','receipt':{'path':str(M/'native-v1/receipt.json'),**ident((M/'native-v1/receipt.json').read_bytes()),'recorded_checks':69,'all_recorded_flags_true':True,'commands':3,'http_gets':3},'source':{'tool_commit':r['spec']['tool_commit'],'feature_commit':r['spec']['feature_commit'],'content_digest':DIG,'eight_source_bindings':'Each captured body rehashed against complete independently fetched c68 tree and installed inventory; three served bodies exact.','controls':'All eight freeze controls, nineteen staged inputs and two later release/spec inputs bind the unchanged before/after inventory.'},'custody':{'native_mirror_files':19,'native_mirror_payload_bytes':sum(x['bytes'] for x in transfer['files']),'raw_child_streams':6,'installed_files':10,'preserved_neighbor_selectors_and_targets':10,'preserved_old_namespace_entries':14,'allowed_new_namespace_entries':13,'directory_exception':'Only explorer parent retains stable ownership/inode/mode while receiving expected new child metadata; atime is excluded.'},'result':{'command':'towerops-explorer-82d3ab784c22','release':REL,'wrapper':ident(wrapper),'help_exit':0,'server_port':r['port'],'server_closure':r['commands'][2]['closure'],'recorded_course_pids_absent':transfer['all_course_pids_absent'],'absence_observer_pid':transfer['pid'],'server_stopped_command_retained':True},'limits':['All69 flags are read as recorded; substantive byte, JSON, source, namespace and stream predicates were independently recomputed. Live process/listener/initial PATH absence remains attributed to the original receiver and later native transfer observer.','No browser, API POST, scenario/replay/explain, repeat install or prior feature78/Forge160 rerun.','Original c77 default and all five neighboring commands remain distinct; this is the additional content-addressed command.']}
p=B/'forge/reviews/towerops-release-native-review-v1.json';p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'review':str(p),**ident(p.read_bytes())}))
