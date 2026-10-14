import pathlib,json,hashlib,stat,datetime
root=pathlib.Path(__file__).resolve().parent
prefix='docs/qualification/explorer-request-settings-loom-d3745/independent-anvil/'
aliases={
 'original-browser-v2/downloads/towerops-approved(1).json':'original-browser-v2/downloads/towerops-approved-after-replay.json',
 'candidate-browser-v2/downloads/towerops-approved(1).json':'candidate-browser-v2/downloads/towerops-approved-after-settings.json',
}
rows=[]
def add(rel,p,authority=None,native=None):
    b=p.read_bytes();s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    m=stat.S_IMODE(s.st_mode)
    got={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
    if authority:
        assert all(got[k]==authority[k] for k in got),rel
        assert m==authority['mode'],rel
    dest=aliases.get(rel,rel)
    assert not pathlib.PurePosixPath(dest).is_absolute() and '..' not in pathlib.PurePosixPath(dest).parts
    assert all(x['path'] != dest for x in rows),dest
    row={'path':dest,'source_path':str(p),**got,'mode':'100755' if m&0o111 else '100644','native_mode':m}
    if native:row['original_native_source_path']=native
    if dest!=rel:row['original_relative_path']=rel
    rows.append(row)
for kind in ['original','candidate']:
    custody=json.loads((root/(kind+'-transfer-custody-v1.json')).read_bytes())
    for item in custody['files']:
        add(item['path'],root/(kind+'-native-mirror')/item['path'],item,item['source_path'])
original=json.loads((root/'original-source-tree-v1.json').read_bytes())
for item in original['rows']:
    add('original/'+item['path'],root/'original'/item['path'])
freeze=json.loads((root/'receiver-freeze-v2.json').read_bytes())
for item in freeze['controls']:
    p=root/item['path'];b=p.read_bytes();assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256']
    add(item['path'],p)
for rel in ['receiver-freeze-v2.json','candidate-offer-v1.json','original-course-review-v1.json',
            'original-transfer-custody-v1.json','candidate-transfer-custody-v1.json','transfer-candidate-v1.py',
            'audit-courses-v1.py','saved-course-audit-v1.json','visual-review-v1.json','README.md',
            'seal-publication-inputs-v1.py']:
    add(rel,root/rel)
rows.sort(key=lambda x:x['path'])
out={'schema':'anvil.towerops-settings.publication-inputs.v1','prefix':prefix,
     'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':rows,
     'notes':['Original 24/24 absence control and candidate 78/78 behavior remain distinct.',
              'source_path names exact cloud retained bodies; original_native_source_path preserves native provenance. Raw receipts are unchanged.',
              'Two explicitly mapped Firefox collision filenames use portable publication aliases only; no renamed-copy execution claim.',
              'Native regular non-executable modes 0644 or 0664 map to Git 100644; executable explorer.py remains 100755.',
              'No browser profiles, cache, tmp, compressed private transfer envelope, product rerun or source mutation. Peer source/controller reviews are separate publisher support.']}
b=(json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode()
with (root/'publication-inputs-v1.json').open('xb') as f:f.write(b)
print(json.dumps({'rows':len(rows),'payload_bytes':sum(x['bytes'] for x in rows),'descriptor_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}))
