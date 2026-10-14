#!/usr/bin/env python3
"""Seal an explicit independent evidence map, never classify by source substring."""
import datetime
import hashlib
import json
from pathlib import Path
import stat

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def enc(x):return (json.dumps(x,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode('ascii')
def pin(p):
    b=p.read_bytes()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
            'source_mode':stat.S_IMODE(p.lstat().st_mode)}
receipt_path=HERE/'received-v1/receipt.json'
receipt=json.loads(receipt_path.read_bytes())
assert receipt['accepted'] is True and len(receipt['commands'])==8 and len(receipt['checks'])==160
assert all(c['pass'] is True and enc(c['actual'])==enc(c['expected']) for c in receipt['checks'])
assert [c['exit_code'] for c in receipt['commands']]==[0,0,2,0,2,0,2,2]
assert all(c['group_absent'] is True for c in receipt['commands'])
streams=[]
for c in receipt['commands']:
    for kind in ('stdout','stderr'):
        p=Path(c[kind+'_path']);row=pin(p)
        assert {k:row[k] for k in ('bytes','sha256','git_blob')}=={k:c[kind][k] for k in ('bytes','sha256','git_blob')}
        assert p.read_bytes()==c[kind+'_text'].encode('utf-8')
        streams.append(p.relative_to(HERE).as_posix())
for kind in ('controls','inputs','tools','foreign'):
    assert enc(receipt[kind+'_before'])==enc(receipt[kind+'_after'])
original_authority=ROOT/'loom-towerops-request-settings/preparation/original-source-identities-v1.json'
with (HERE/'original-source-authority.json').open('xb') as f:f.write(original_authority.read_bytes())
names=[
 'README.md','criteria-v1.md','public-contract-v2.md','public-output-contract-v1.json',
 'prepare-fixtures-v1.py','fixture-receipt-v1.json','original-tree-bindings.json','original-source-authority.json',
 'expected-inspect-a.json','expected-inspect-b.json','receive-releases-v1.py','freeze-v1.json',
 'admit-candidate-v1.py','candidate-manifest-offered-v1.json','candidate-spec-v1.json','candidate-admission-v1.json',
 'run-receiving-v1.py','controller-launch-v1.json','controller-v1.stdout','controller-v1.stderr',
 'received-v1/receipt.json','received-v1/04-corrected-a-installation.json','received-v1/06-side-by-side-b-installation.json',
 'seal-publication-v1.py',
]+streams
inputs=['EXPLORER.md','explorer.py','replay_explain.py','scenarios.py','towerops.py',
        'web/app.js','web/index.html','web/style.css','ignored-extra.txt']
names += ['fixtures/source-'+tag+'/'+name for tag in ('a','b') for name in inputs]
assert len(names)==len(set(names))
rows=[]
for name in names:
    p=HERE/name;r=pin(p)
    rows.append({'path':name,'source_path':str(p),'mirror_path':str(p),
                 'mode':'100755' if r['source_mode']&0o111 else '100644',**r})
descriptor={'schema':'forge.towerops-release-receiving-publication.v1',
            'prefix':'docs/qualification/explorer-releases-root-d3745/independent/',
            'sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'files':rows,'scope':'original cloud temporary-prefix 8CLI/160checks; no native/runtime adoption',
            'exclusions':['new utility body','unchanged helper body','Loom formal review','root independent result review'],
            'total_payload_bytes':sum(r['bytes'] for r in rows)}
with (HERE/'publication-inputs-v1.json').open('xb') as f:f.write(enc(descriptor))
print(json.dumps({'rows':len(rows),'payload_bytes':descriptor['total_payload_bytes'],
                  'descriptor':pin(HERE/'publication-inputs-v1.json')}))
