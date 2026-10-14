#!/usr/bin/env python3
"""Correct one opening link before Git mutation; preserve the initial plan."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

P=Path(__file__).resolve().parent
Q='docs/qualification/explorer-releases-root-d3745/'
def enc(x):return (json.dumps(x,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode()
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def save(name,b):
    p=P/name
    with p.open('xb') as f:f.write(b)
    return p
old=(P/'README.md').read_bytes();needle=b'(../../../EXPLORER_RELEASES.md)'
assert old.count(needle)==1
new=old.replace(needle,b'(../../EXPLORER_RELEASES.md)')
new_path=save('README-corrected-v2.md',new)
record={'schema':'forge.towerops-release-opening-correction.v2','old':ident(old),'new':ident(new),
        'old_path':str(P/'README.md'),'new_path':str(new_path),
        'change':'One relative guide link ascends two directories to docs/ rather than three to repository root.',
        'timing':'After initial local selected-layout preflight; before any Git object/tree/ref mutation.',
        'preservation':'Original README,85-entry packet/plan/policy/receipt remain untouched. Product3, originalroot19 and originalForge58 remain byte-exact.',
        'no_product_execution':True}
record_path=save('opening-correction-v2.json',enc(record))
packet=json.loads((P/'selected.packet.json').read_bytes())
policy=json.loads((P/'layout-policy.json').read_bytes())
authority=json.loads((P/'selection-authority.json').read_bytes())
for row in packet['files']:
    if row['path']==Q+'README.md':
        assert base64.b64decode(row['content'])==old
        row.update(sha=ident(new)['git_blob'],content=base64.b64encode(new).decode())
for records in (policy['support_files'],authority['files']):
    for row in records:
        if row['path']==Q+'README.md':row.update(**ident(new),source_path=str(new_path))
for name,path in [('correct-opening-v2.py',Path(__file__)),('opening-correction-v2.json',record_path)]:
    b=path.read_bytes();i=ident(b);dest=Q+name
    packet['files'].append({'path':dest,'mode':'100644','sha':i['git_blob'],'encoding':'base64','content':base64.b64encode(b).decode()})
    row={'path':dest,'mode':'100644',**i,'source_path':str(path),'role':'support','authority':'explicit prepublication guide-only correction'}
    policy['support_files'].append(row);authority['files'].append(row)
packet['files'].sort(key=lambda r:r['path']);authority.update(support=26,total=87)
save('selected.packet-v2.json',enc(packet));save('layout-policy-v2.json',enc(policy));save('selection-authority-v2.json',enc(authority))
steps=[]
for label,tool,args in [
 ('prepare-v2','prepare_git_objects.py',[str(P/'selected.packet-v2.json'),'--sha256',ident((P/'selected.packet-v2.json').read_bytes())['sha256'],'--out',str(P/'selected.objects-v2.json')]),
 ('layout-v2','validate_publication_layout.py',[str(P/'selected.objects-v2.json'),'--sha256','PLAN','--policy',str(P/'layout-policy-v2.json'),'--policy-sha256',ident((P/'layout-policy-v2.json').read_bytes())['sha256'],'--descriptor',str(P.parent/'publication-inputs-v1.json'),'--descriptor-sha256','aea8a21cde0119559604042bd6f3cff585f049c125b64b5a4e5daf98d182b0b6'])]:
    args=[ident((P/'selected.objects-v2.json').read_bytes())['sha256'] if a=='PLAN' else a for a in args]
    argv=['/usr/bin/python3','-B',str(P/'tools'/tool),*args]
    c=subprocess.run(argv,capture_output=True,timeout=45)
    save(label+'.stdout',c.stdout);save(label+'.stderr',c.stderr)
    steps.append({'label':label,'argv':argv,'exit_code':c.returncode,'stdout':ident(c.stdout),'stderr':ident(c.stderr)})
    if c.returncode:save('preflight-receipt-v2.json',enc({'accepted':False,'steps':steps}));raise SystemExit(c.returncode)
save('preflight-receipt-v2.json',enc({'schema':'forge.towerops-release-preflight.v2','accepted':True,'steps':steps,'selected':87,'source':3,'support':26,'evidence':58,'plan':ident((P/'selected.objects-v2.json').read_bytes()),'product_executed':False}))
print(json.dumps({'accepted':True,'selected':87,'plan':ident((P/'selected.objects-v2.json').read_bytes())}))
