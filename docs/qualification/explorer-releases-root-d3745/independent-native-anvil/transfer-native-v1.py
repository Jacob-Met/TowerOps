import pathlib,json,hashlib,stat,base64,zlib,datetime,os
root=pathlib.Path('/home/jacob/hamon/receiving/anvil-d3745-towerops-release-native')
release=pathlib.Path('/home/jacob/.local/share/towerops/explorer/releases/82d3ab784c221b9fa320edbfc0a6f725a5beb8c293d0681646fedcfb880e0216')
raw=(root/'native-v1/receipt.json').read_bytes()
assert len(raw)==87028 and hashlib.sha256(raw).hexdigest()=='e78c3c336505dab5599ea1a29a6bc09f7bf39cce95a75d8e159268175521ad5a'
r=json.loads(raw);assert r['accepted'] and len(r['checks'])==69 and all(c['passed'] for c in r['checks'])
pids=[r['pid']]+[c['pid'] for c in r['commands']]
for pid in pids:assert not pathlib.Path('/proc',str(pid)).exists(),pid
paths=[(n,root/n) for n in ['stage-admission-v1.json','stage-receipt-v1.json','native-release-v1.json','native-spec-v1.json','native-v1.stdout','native-v1.stderr']]
for p in sorted((root/'native-v1').iterdir()):
 if p.name=='foreign-cwd':assert p.is_dir() and not list(p.iterdir());continue
 paths.append(('native-v1/'+p.name,p))
paths.extend([('installed/towerops-explorer',release/'towerops-explorer'),('installed/installation.json',release/'installation.json')])
files=[]
for rel,p in paths:
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes()
 files.append({'path':rel,'source_path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':stat.S_IMODE(s.st_mode),'base64':base64.b64encode(b).decode()})
obj={'schema':'anvil.towerops-release.native-custody-transfer.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'all_course_pids_absent':pids,'files':files}
b=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
print(json.dumps({'encoding':'base64+zlib','raw_bytes':len(b),'raw_sha256':hashlib.sha256(b).hexdigest(),'file_count':len(files),'base64':base64.b64encode(zlib.compress(b,9)).decode()}))
