"""Admit original native authority and explicit support; no Git mutation or product execution."""
from pathlib import Path
import json,hashlib,base64,stat,subprocess,sys,collections
P=Path(__file__).resolve().parent;B=P.parents[2];OLD=B/'forge/towerops-releases-receiving/publication-v1';TOOLS=OLD/'tools'
Q='docs/qualification/explorer-releases-root-d3745/';S=Q+'native-evidence/'
def enc(x):return (json.dumps(x,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def save(n,x):
 p=P/n
 with p.open('xb') as f:f.write(enc(x))
 return p
base=json.loads((P/'base-commit.json').read_bytes());bt=json.loads((P/'base-tree.json').read_bytes())
assert base['sha']=='8c9e980ccb3469e777316af472a22a3db7c9edc6' and base['tree']['sha']==bt['sha']=='b46791df00af8878a9583c4b70f73f1a588d6e69' and bt['truncated'] is False
tr=json.loads((OLD/'tools-tree-selection.json').read_bytes());toolrows=[]
for row in tr['files']:
 p=TOOLS/row['path'];i=ident(p.read_bytes());assert i['git_blob']==row['sha'] and i['bytes']==row['size'];toolrows.append({'path':str(p),**i,'mode':stat.S_IMODE(p.stat().st_mode)})
sys.path.insert(0,str(TOOLS));from verify_tree_union import admit_snapshot,git_tree_id
prior=admit_snapshot(bt,bt['sha'],'base');assert len(prior)==1843
DP=B/'anvil/towerops-release-native/publication-inputs-v1.json';db=DP.read_bytes();assert ident(db)['sha256']=='2a9d8327bbdb841f131e18bf7f5d5759cf1640932a7dd536cdb3455f5e48ce3b'
d=json.loads(db);assert len(d['files'])==34 and d['prefix']==Q+'independent-native-anvil/'
entries=[];authority=[];seen=set()
def add(path,src,mode,role,expect=None):
 src=Path(src);assert stat.S_ISREG(src.lstat().st_mode);b=src.read_bytes();i=ident(b)
 if expect:
  assert all(i[k]==expect[k] for k in ['bytes','sha256','git_blob']);assert stat.S_IMODE(src.stat().st_mode)==expect['native_mode']
 assert path not in seen and path not in prior;seen.add(path)
 entries.append({'path':path,'mode':mode,'sha':i['git_blob'],'encoding':'base64','content':base64.b64encode(b).decode()})
 authority.append({'path':path,'mode':mode,'role':role,'source_path':str(src),**i})
for row in d['files']:add(d['prefix']+row['path'],row['source_path'],row['mode'],'evidence',row)
extras=[('native-descriptor.json',DP),('native-receiving-review-forge.json',B/'forge/reviews/towerops-release-native-review-v1.json'),('audit-native-receiving-v1.py',B/'forge/reviews/audit-towerops-release-native-v1.py'),('native-controller-review-root.json',B/'root-towerops-releases/native-controller-review-v1.json'),('source-adoption-verification-root.json',B/'root-towerops-releases/release-merge-verification-v1.json'),('README.md',P/'README.md'),('prepare-evidence-v1.py',Path(__file__))]
for name,src in extras:add(S+name,src,'100644','support')
bind={'schema':'forge.towerops-native-evidence-binding.v1','base':{'commit':base['sha'],'tree':bt['sha']},'original_descriptor':{'path':str(DP),**ident(db),'prefix':d['prefix'],'rows':34},'source_paths':[],'support_authority':[{k:v for k,v in row.items()} for row in authority if row['role']=='support'],'tools_commit':tr['commit'],'tool_files':toolrows,'source_scope':'Evidence-only addition; preserve all1843 base leaves and original source87/root19/Forge58 authority. No product execution.'}
add(S+'source-binding.json',save('source-binding.json',bind),'100644','support')
assert len(entries)==42 and sum(x['role']=='support' for x in authority)==8
packet={'schema':'hamon.source-packet/1','source':{'repository':'Jacob-Met/TowerOps','commit':base['sha'],'tree':bt['sha']},'files':sorted(entries,key=lambda x:x['path'])}
save('selected.packet.json',packet)
policy={'schema':'hamon.publication-layout/1','source_files':[],'support_files':[r for r in authority if r['role']=='support'],'evidence_prefix':Q,'descriptor_schema':d['schema'],'descriptor_prefix':d['prefix']}
save('layout-policy.json',policy);save('selection-authority.json',{'schema':'forge.towerops-native-evidence-selection.v1','source':0,'support':8,'evidence':34,'total':42,'files':authority})
records=[]
def run(label,name,args):
 argv=['/usr/bin/python3','-B',str(TOOLS/name),*args];p=subprocess.run(argv,capture_output=True,timeout=45)
 for typ,raw in [('stdout',p.stdout),('stderr',p.stderr)]:
  with (P/(label+'.'+typ)).open('xb') as f:f.write(raw)
 records.append({'label':label,'argv':argv,'exit':p.returncode,'stdout':ident(p.stdout),'stderr':ident(p.stderr)})
 assert p.returncode==0,(label,p.stderr)
run('prepare','prepare_git_objects.py',[str(P/'selected.packet.json'),'--sha256',ident((P/'selected.packet.json').read_bytes())['sha256'],'--out',str(P/'selected.objects.json')])
plan=json.loads((P/'selected.objects.json').read_bytes())
run('layout','validate_publication_layout.py',[str(P/'selected.objects.json'),'--sha256',ident((P/'selected.objects.json').read_bytes())['sha256'],'--policy',str(P/'layout-policy.json'),'--policy-sha256',ident((P/'layout-policy.json').read_bytes())['sha256'],'--descriptor',str(DP),'--descriptor-sha256',ident(db)['sha256']])
leaves=dict(prior)
for row in plan['tree_entries']:leaves[row['path']]=(row['mode'],row['type'],row['sha'])
dirs={''}
for path in leaves:
 parts=path.split('/');dirs.update('/'.join(parts[:i]) for i in range(1,len(parts)))
assert not (set(leaves)&dirs)
nodes=dict(leaves)
for path in sorted(dirs,key=lambda x:(x.count('/'),len(x)),reverse=True):
 children=[(k.rsplit('/',1)[-1],v) for k,v in nodes.items() if k.rpartition('/')[0]==path]
 sha=git_tree_id(children)
 if path:nodes[path]=('040000','tree',sha)
 else:rootsha=sha
proposed={'sha':rootsha,'truncated':False,'tree':[dict(path=k,mode=v[0],type=v[1],sha=v[2]) for k,v in sorted(nodes.items())]}
save('expected-proposed-tree.json',proposed);assert len(admit_snapshot(proposed,rootsha,'proposal'))==1885
run('tree-check','verify_publication_tree.py',[str(P/'selected.objects.json'),'--sha256',ident((P/'selected.objects.json').read_bytes())['sha256'],'--base',str(P/'base-tree.json'),bt['sha'],'--proposed',str(P/'expected-proposed-tree.json'),rootsha])
save('preflight-receipt.json',{'schema':'forge.towerops-native-evidence-preflight.v1','accepted':True,'source':0,'support':8,'evidence':34,'total':42,'unique_blobs':len(plan['blobs']),'original_descriptor':ident(db),'plan':ident((P/'selected.objects.json').read_bytes()),'base_tree':bt['sha'],'proposed_tree':rootsha,'terminal_entries':{'base':1843,'proposed':1885},'tool_files':toolrows,'records':records,'scope':'Local selected-layout and complete expected-tree conservation, no Git mutation or runtime.'})
print(json.dumps({'accepted':True,'selected':42,'unique_blobs':len(plan['blobs']),'expected_tree':rootsha,'plan':ident((P/'selected.objects.json').read_bytes())}))
