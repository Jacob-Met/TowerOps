import os,pwd,socket,pathlib,json,hashlib,shutil,subprocess,sys,datetime
base=pathlib.Path('/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-explain')
rows=json.loads("[{\"path\":\"EXPLORER.md\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/EXPLORER.md\",\"bytes\":4966,\"sha256\":\"c89087497a6547f91218cf53dc783bce22bfe1f428faaa32cf40adacada930bc\",\"mode\":\"0o644\",\"git_blob\":\"00cdf262110440bc7f59eeb645835d5f269f10d8\"},{\"path\":\"explorer.py\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/explorer.py\",\"bytes\":7141,\"sha256\":\"da950f18a267a36e018649e2b29df19ae34f3679358227ea5afbc69bb7a42c75\",\"mode\":\"0o755\",\"git_blob\":\"897ddf219cb5be863ff89318d1bf8b22a08e3e2f\"},{\"path\":\"scenarios.py\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/scenarios.py\",\"bytes\":5989,\"sha256\":\"bda24452b41a9ec8b6a7a0865b2fb95217a4a304ecf17b1c5d72b2dab65f6a52\",\"mode\":\"0o644\",\"git_blob\":\"33b5703d2ce0d4177c50f05536e3f2715c8bea3b\"},{\"path\":\"test_explorer.py\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/test_explorer.py\",\"bytes\":7460,\"sha256\":\"40550e034a6d2ff9f8125feecd58b63205028c12346f1e1e68fdf16dbfc657c7\",\"mode\":\"0o644\",\"git_blob\":\"51f7de9067a733d11649684d799417d66c84c36d\"},{\"path\":\"towerops.py\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/towerops.py\",\"bytes\":19684,\"sha256\":\"b8bb4a15c70b0137e1c47aa614e6ed1b6f3cae096af9fb0c8810f3d900a48f70\",\"mode\":\"0o644\",\"git_blob\":\"0b03cee708cdff5cbacd148633def31f4e9414c5\"},{\"path\":\"web/app.js\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/web/app.js\",\"bytes\":6147,\"sha256\":\"e3ade13b07b119050d9a40b1bba4fd116a037ce0822f7c2c74030d569e7af09f\",\"mode\":\"0o644\",\"git_blob\":\"c340207635b819d0877797b2c84002b79865660d\"},{\"path\":\"web/index.html\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/web/index.html\",\"bytes\":3396,\"sha256\":\"645041b691beb175780edc52bcf78b5e99f9964ff975766433ce8967d5cd28e7\",\"mode\":\"0o644\",\"git_blob\":\"6bc1ac6ba66826037b292832feef79b3f96c349b\"},{\"path\":\"web/style.css\",\"source_path\":\"/home/jacob/hamon/receiving/anvil-d3745-towerops-replay-selection/candidate/web/style.css\",\"bytes\":2037,\"sha256\":\"af35cb1c6b2eb22bf5f792c3539cff48506fbea31fa347600873fe004459e7c4\",\"mode\":\"0o644\",\"git_blob\":\"3770b65750778fecfa1ab2adc5f3ba48bafe10fb\"}]")
def require(ok,msg):
 if not ok: raise RuntimeError(msg)
def identity(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':oct(p.stat().st_mode&0o777)}
require(socket.gethostname()=='hamon-thinkpad' and os.getuid()==1000 and pwd.getpwuid(os.getuid()).pw_name=='jacob','identity')
require(not base.exists(),'exclusive stage')
for r in rows:
 p=pathlib.Path(r['source_path']);i=identity(p)
 require(not p.is_symlink() and p.is_file() and all(i[k]==r[k] for k in ('bytes','sha256','git_blob','mode')),'source '+r['path'])
base.mkdir();(base/'baseline').mkdir();(base/'author').mkdir();(base/'original').mkdir()
(base/'author/stage-original.py').write_text(SCRIPT_TEXT)
for r in rows:
 d=base/'baseline'/r['path'];d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r['source_path'],d)
before=[identity(base/'baseline'/r['path']) for r in rows]
env={k:v for k,v in os.environ.items() if not k.startswith('PYTHON')};env['PYTHONDONTWRITEBYTECODE']='1'
runs=[]
def run(label,args,code):
 cmd=[sys.executable,'-B',str(base/'baseline/explorer.py'),*args]
 p=subprocess.run(cmd,cwd=base/'original',env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 rec={'label':label,'argv':cmd,'returncode':p.returncode}
 for name,b in [('stdout',p.stdout),('stderr',p.stderr)]:
  dest=base/'original'/(label+'.'+name);dest.write_bytes(b);rec[name]=identity(dest)
 runs.append(rec);require(p.returncode==code,label+' code');return p
producer=run('01-export',['run','approved'],0)
require(producer.stderr==b'','producer stderr')
a=base/'original/approved.json';a.write_bytes(producer.stdout)
match=run('02-match',['replay',str(a)],0)
edited=json.loads(producer.stdout);edited['after']['version']+=1
b=base/'original/changed.json';b.write_text(json.dumps(edited,indent=2)+'\n')
mismatch=run('03-mismatch',['replay',str(b)],1)
value=json.loads(mismatch.stdout)
require(value['matches'] is False and 'differences' not in value and 'difference_limit' not in value and 'differences_truncated' not in value,'baseline generic reply')
require(json.loads(match.stdout)['matches'] is True and match.stderr==b'' and mismatch.stderr==b'','match/refusal')
refusal=run('04-explain-absent',['replay',str(b),'--explain'],2)
require(refusal.stdout==b'' and b'unrecognized arguments: --explain' in refusal.stderr,'unsupported option')
after=[identity(base/'baseline'/r['path']) for r in rows]
require(before==after,'source unchanged')
for r in rows:
 i=identity(pathlib.Path(r['source_path']));require(all(i[k]==r[k] for k in ('bytes','sha256','git_blob','mode')),'donor preserved')
receipt={'schema':'hamon.anvil.explorer-replay-explain-original.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_commit':'8a87ad1331d7e7100367dde583d59560836f9eb8','identity':{'host':socket.gethostname(),'uid':os.getuid(),'user':pwd.getpwuid(os.getuid()).pw_name,'python':sys.version},'candidate_exists':False,'runs':runs,'source_before':before,'source_after':after,'source_and_donor_unchanged':True,'observations':['original generated approved export matches','changed after.version mismatches with no difference fields','--explain absent and refused before success output'],'pass':True}
(base/'original/receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'base':str(base),'receipt':identity(base/'original/receipt.json'),'commands':len(runs),'returncodes':[r['returncode'] for r in runs],'pass':True,'candidate_exists':False}))
