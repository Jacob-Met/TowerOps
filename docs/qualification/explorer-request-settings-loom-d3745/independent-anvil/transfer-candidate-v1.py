import pathlib,json,hashlib,base64,zlib,stat,datetime,os
root=pathlib.Path('/home/jacob/hamon/receiving/anvil-d3745-towerops-settings')
raw=(root/'candidate-browser-v2/receipt.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='3b2a6247ab691eb28d9b77233ceb5bd88112048c8865e58078770894c2bc4ceb'
r=json.loads(raw)
assert r['accepted'] and len(r['checks'])==78 and all(x['pass'] for x in r['checks'])
for pid in [r['pid'],r['backend_pid'],r['browser_pid']]:assert not pathlib.Path('/proc',str(pid)).exists(),pid
assert hashlib.sha256((root/'original-browser-v2/receipt.json').read_bytes()).hexdigest()=='b31cddb0a289fd49f7d0344818ea53ce9ac8d0197deb29f75ae69d173eaeb8bd'
paths=['candidate-spec-v1.json','candidate-stage-receipt-v1.json','stage-candidate-v1.py','candidate-browser-v2.stdout','candidate-browser-v2.stderr','candidate-browser-v2/receipt.json']
paths+=['candidate/'+x['path'] for x in r['source_spec']['source_files']]
paths += sorted(str(p.relative_to(root)) for folder in ['candidate-browser-v2/streams','candidate-browser-v2/downloads'] for p in (root/folder).iterdir())
paths += sorted(str(p.relative_to(root)) for p in (root/'candidate-browser-v2').glob('*.png'))
assert len(paths)==len(set(paths))
files=[]
for rel in paths:
 p=root/rel;s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes()
 files.append({'path':rel,'source_path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':stat.S_IMODE(s.st_mode),'base64':base64.b64encode(b).decode()})
obj={'schema':'anvil.towerops-settings.candidate-transfer-custody.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'original_receipt_preserved':True,'runtime_pids_absent':[r['pid'],r['backend_pid'],r['browser_pid']],'files':files}
b=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
print(json.dumps({'encoding':'base64+zlib','raw_bytes':len(b),'raw_sha256':hashlib.sha256(b).hexdigest(),'file_count':len(files),'base64':base64.b64encode(zlib.compress(b,9)).decode()}))
