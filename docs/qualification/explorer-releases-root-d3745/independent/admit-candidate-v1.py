#!/usr/bin/env python3
"""Copy only the two offered utility files after external-control freeze."""
import datetime
import hashlib
import json
from pathlib import Path
import stat

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def pin(p):
    b=p.read_bytes()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
            'mode':stat.S_IMODE(p.lstat().st_mode)}
def encoded(x):return (json.dumps(x,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode('ascii')
manifest=ROOT/'root-towerops-releases/preparation/candidate-manifest-v1.json'
assert pin(manifest)['sha256']=='b00645b2a7481aaaa2e9d36dd231b7f509631c0eec1022808e15dc08ef766874'
assert pin(HERE/'freeze-v1.json')['sha256']=='71158e90f726121c4ad2df82bc084907c0382cc5930803357cc8c6d29fb24b8a'
records=json.loads(manifest.read_text())['files']
selected=[r for r in records if r['path'] in ('tools/stage_explorer.py','tools/install_explorer.py')]
assert len(selected)==2
target=HERE/'offered-tools-v1';target.mkdir()
before={};files={}
for row in selected:
    src=Path(row['source_path']);expected={k:row[k] for k in ('bytes','sha256','git_blob','mode')}
    before[str(src)]=pin(src);assert before[str(src)]==expected
    dst=target/src.name
    with dst.open('xb') as f:f.write(src.read_bytes())
    dst.chmod(row['mode']);assert pin(dst)==expected
    files[src.name]=expected
spec={'schema':'forge.towerops-release-offer.v1','tools_dir':str(target),'files':files,
      'publication_state':'unpublished isolated root candidate','source_baseline':'202782f29f3a0ed1411e67a7744f9e63f26926f1'}
with (HERE/'candidate-spec-v1.json').open('xb') as f:f.write(encoded(spec))
with (HERE/'candidate-manifest-offered-v1.json').open('xb') as f:f.write(manifest.read_bytes())
after={p:pin(Path(p)) for p in before};assert before==after
receipt={'schema':'forge.towerops-release-admission.v1','accepted':True,
         'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'external_freeze':pin(HERE/'freeze-v1.json'),'manifest':pin(manifest),
         'source_before':before,'source_after':after,'copied':files,
         'spec':pin(HERE/'candidate-spec-v1.json'),'product_executed':False}
with (HERE/'candidate-admission-v1.json').open('xb') as f:f.write(encoded(receipt))
print(json.dumps({'accepted':True,'files':len(files),'spec':receipt['spec']}))
