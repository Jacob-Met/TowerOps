import pathlib,json,hashlib,stat,datetime
root=pathlib.Path(__file__).resolve().parent
prefix='docs/qualification/explorer-releases-root-d3745/independent-native-anvil/'
files=[]
def add(rel,p,native=None,wanted=None):
 b=p.read_bytes();s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 got={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
 if wanted:assert all(got[k]==wanted[k] for k in got) and stat.S_IMODE(s.st_mode)==wanted['mode']
 assert not any(x['path']==rel for x in files)
 row={'path':rel,'source_path':str(p),**got,'mode':'100755' if s.st_mode&0o111 else '100644','native_mode':stat.S_IMODE(s.st_mode)}
 if native:row['original_native_source_path']=native
 files.append(row)
custody=json.loads((root/'transfer-custody-v1.json').read_bytes())
for r in custody['files']:add(r['path'],root/'native-mirror'/r['path'],r['source_path'],r)
freeze=json.loads((root/'freeze-v1.json').read_bytes())
for name,r in freeze['files'].items():
 p=root/name;b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'] and stat.S_IMODE(p.stat().st_mode)==r['mode']
 add(name,p)
for name in ['freeze-v1.json','stage-inputs-v1.py','transfer-native-v1.py','transfer-custody-v1.json','published-tool-bodies-v1.json','README.md','seal-publication-inputs-v1.py']:
 add(name,root/name)
files.sort(key=lambda x:x['path'])
out={'schema':'anvil.towerops-release.native-publication-inputs.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prefix':prefix,'files':files,
     'notes':['Original source-exposed native course:69checks/3commands/3GET; no browser or API POST or repeat install.',
              'Exact private native19-file mirror and original controls. source_path points to retained cloud bytes; original_native_source_path retains native provenance.',
              'Native0644/0664/0600 non-executable files are published Git100644; actual native mode remains explicit. Installed wrapper retains0755/Git100755.',
              'No private compressed packet, unrelated data, live process or installed namespace mutation during sealing. Root/Forge peer reviews are separate support.']}
b=(json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode()
with (root/'publication-inputs-v1.json').open('xb') as f:f.write(b)
print(json.dumps({'rows':len(files),'payload_bytes':sum(x['bytes'] for x in files),'descriptor_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}))
