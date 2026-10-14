#!/usr/bin/env python3
"""Explicit original-authority union; no candidate execution or Git mutations."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess

P=Path(__file__).resolve().parent
F=P.parent
R=F.parents[1]
Q='docs/qualification/explorer-releases-root-d3745/'
def enc(x):return (json.dumps(x,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode('ascii')
def ident(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                       'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
def save(name,value):
    p=P/name
    with p.open('xb') as f:f.write(enc(value))
    return p
base=json.loads((P/'base-commit.json').read_bytes());tree=json.loads((P/'base-tree.json').read_bytes())
assert base['sha']=='f23a2538cbb26d08b7bdaef60f11bb7650d03704'
assert base['tree']['sha']==tree['sha']=='5b3b8c2bc64f9de01db58dc2e0fd47842d15be61' and tree['truncated'] is False
prior={row['path']:row for row in tree['tree']}
original_tree=json.loads((F/'original-tree-bindings.json').read_bytes())
for row in original_tree['rows']:
    assert all(prior[row['path']][k]==row[k] for k in ('mode','type','sha'))
tool_record=json.loads((P/'tools-tree-selection.json').read_bytes())
(P/'tools').mkdir()
tool_pins=[]
for row in tool_record['files']:
    src=R/'forge/seatrush-preview-install/publication-v1/tools'/row['path']
    raw=src.read_bytes();i=ident(raw);assert i['git_blob']==row['sha'] and i['bytes']==row['size']
    dst=P/'tools'/row['path']
    with dst.open('xb') as f:f.write(raw)
    dst.chmod(int(row['mode'],8)&0o777)
    tool_pins.append({'path':str(dst),**i,'mode':row['mode']})
selected=[];sources=[];support=[];paths=set();identities=[]
def add(dest,src,mode,role,expected=None,authority=None):
    src=Path(src);info=src.lstat();assert stat.S_ISREG(info.st_mode)
    raw=src.read_bytes();i=ident(raw)
    if expected:
        assert all(i[k]==expected[k] for k in ('bytes','sha256','git_blob')),(dest,'identity')
        if 'source_mode' in expected:assert stat.S_IMODE(info.st_mode)==expected['source_mode']
    assert dest not in paths and dest not in prior,dest
    paths.add(dest)
    selected.append({'path':dest,'mode':mode,'sha':i['git_blob'],'encoding':'base64','content':base64.b64encode(raw).decode('ascii')})
    row={'path':dest,'mode':mode,**i,'role':role,'source_path':str(src),'authority':authority}
    identities.append(row)
    if role=='source':sources.append(row)
    if role=='support':support.append(row)
    return row
author_path=R/'root-towerops-releases/preparation/original-author-selection-v1.json'
assert ident(author_path.read_bytes())['sha256']=='e4da2d4a0824e97bdb385b0b654048301cb3e49000f8d02f8d31b7bf3c5f8dc2'
author=json.loads(author_path.read_bytes());assert len(author['rows'])==19
for row in author['rows']:
    add(row['destination'],row['source_path'],row['mode'],'source' if row['kind']=='production' else 'support',row,'original root19 authority')
descriptor_path=F/'publication-inputs-v1.json'
assert ident(descriptor_path.read_bytes())['sha256']=='aea8a21cde0119559604042bd6f3cff585f049c125b64b5a4e5daf98d182b0b6'
descriptor=json.loads(descriptor_path.read_bytes());assert len(descriptor['files'])==58
for row in descriptor['files']:
    add(descriptor['prefix']+row['path'],row['source_path'],row['mode'],'evidence',row,'original Forge58 descriptor')
extras=[
 ('original-author-selection.json',author_path,'e4da2d4a0824e97bdb385b0b654048301cb3e49000f8d02f8d31b7bf3c5f8dc2'),
 ('independent-descriptor.json',descriptor_path,'aea8a21cde0119559604042bd6f3cff585f049c125b64b5a4e5daf98d182b0b6'),
 ('source-review-anvil.json',R/'anvil/towerops-releases-review/source-review-v1.json','2a66d94d153219cf1f08667471558b43e063e48f5d76995411500e9d6105788c'),
 ('harness-review-loom.json',R/'loom/reviews/towerops-release-receiver-review-v1.json','4deb754a06105547a2b8144c07689088db38dd159bd09027401b287d941b427c'),
 ('result-review-root.json',R/'root-towerops-releases/independent-result-review-v1.json','8cad839e6c6fed08f49452510e9a4470adc47749d747f3295fab186b1734f84f'),
]
for name,path,digest in extras:
    assert ident(path.read_bytes())['sha256']==digest
    add(Q+name,path,'100644','support',authority='explicit original review or authority; opaque bytes')
binding={'schema':'forge.towerops-release-publication-binding.v1',
         'base':{'commit':base['sha'],'tree':tree['sha']},'source_files':sources,
         'author_authority':{'path':str(author_path),**ident(author_path.read_bytes()),'rows':19,'source_rows':3},
         'independent_authority':{'path':str(descriptor_path),**ident(descriptor_path.read_bytes()),'rows':58,'prefix':descriptor['prefix']},
         'runtime_and_helper_preserved':original_tree['rows'],
         'tools_commit':tool_record['commit'],'tool_files':tool_pins,
         'scope':'Three new source paths plus exact19-author and58-independent union and explicit support. Native adoption pending.'}
add(Q+'source-binding.json',save('source-binding.json',binding),'100644','support',authority='explicit source/authority/tool binding')
add(Q+'README.md',P/'README.md','100644','support',authority='current qualification opening')
add(Q+'prepare-publication-v1.py',Path(__file__),'100644','support',authority='exact selection/preflight controller')
assert len(sources)==3 and len(support)==24 and len(selected)==85
packet={'schema':'hamon.source-packet/1','source':{'repository':'Jacob-Met/TowerOps','commit':base['sha'],'tree':tree['sha']},'files':sorted(selected,key=lambda r:r['path'])}
save('selected.packet.json',packet)
policy={'schema':'hamon.publication-layout/1','source_files':sources,'support_files':support,
        'evidence_prefix':Q,'descriptor_schema':descriptor['schema'],'descriptor_prefix':descriptor['prefix']}
save('layout-policy.json',policy)
save('selection-authority.json',{'schema':'forge.towerops-release-selected-authority.v1','files':identities,
                               'source':3,'support':24,'evidence':58,'total':85})
commands=[('prepare','prepare_git_objects.py',[str(P/'selected.packet.json'),'--sha256',ident((P/'selected.packet.json').read_bytes())['sha256'],'--out',str(P/'selected.objects.json')]),
          ('layout','validate_publication_layout.py',[str(P/'selected.objects.json'),'--sha256','PLAN','--policy',str(P/'layout-policy.json'),'--policy-sha256',ident((P/'layout-policy.json').read_bytes())['sha256'],'--descriptor',str(descriptor_path),'--descriptor-sha256',ident(descriptor_path.read_bytes())['sha256']])]
records=[]
for label,name,args in commands:
    args=[ident((P/'selected.objects.json').read_bytes())['sha256'] if a=='PLAN' else a for a in args]
    argv=['/usr/bin/python3','-B',str(P/'tools'/name),*args]
    process=subprocess.run(argv,capture_output=True,timeout=45)
    for kind,raw in [('stdout',process.stdout),('stderr',process.stderr)]:
        with (P/(label+'.'+kind)).open('xb') as f:f.write(raw)
    records.append({'label':label,'argv':argv,'exit_code':process.returncode,
                    'stdout':ident(process.stdout),'stderr':ident(process.stderr)})
    if process.returncode:
        save('preflight-receipt.json',{'accepted':False,'records':records})
        raise SystemExit(process.returncode)
save('preflight-receipt.json',{'schema':'forge.towerops-release-preflight.v1','accepted':True,
                            'records':records,'plan':ident((P/'selected.objects.json').read_bytes()),
                            'source':3,'support':24,'evidence':58,'total':85,'tool_files':tool_pins,
                            'scope':'selected-layout admission only; no Git mutation or ancestry authorization'})
print(json.dumps({'accepted':True,'selected':85,'source':3,'support':24,'evidence':58,
                  'plan':ident((P/'selected.objects.json').read_bytes())}))
