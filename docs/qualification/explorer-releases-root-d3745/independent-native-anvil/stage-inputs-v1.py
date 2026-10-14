import pathlib,json,base64,zlib,hashlib,stat,datetime,os
root=pathlib.Path('/home/jacob/hamon/receiving/anvil-d3745-towerops-release-native')
raw=zlib.decompress(base64.b64decode((root/'incoming-packet-v1.base64zlib').read_bytes().strip(),validate=True))
assert len(raw)==180593 and hashlib.sha256(raw).hexdigest()=='4b1a6b138d1656ad24476e08d99d8bbf50e6de9c04b999a3b83911aa39edf89b'
packet=json.loads(raw);assert len(packet['files'])==19
assert len({r['path'] for r in packet['files']})==19
captured=[]
for r in packet['files']:
 p=pathlib.PurePosixPath(r['path']);assert not p.is_absolute() and '..' not in p.parts
 assert not os.path.lexists(root/p)
 b=base64.b64decode(r['base64'],validate=True)
 assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
 assert r['mode'] in (420,493)
 captured.append((r,b))
with (root/'incoming-packet-v1.json').open('xb') as f:f.write(raw)
copied=[]
for r,b in captured:
 p=root/r['path'];p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
 p.chmod(r['mode']);assert p.read_bytes()==b and stat.S_IMODE(p.stat().st_mode)==r['mode']
 copied.append({k:v for k,v in r.items() if k!='base64'})
receipt={'schema':'anvil.towerops-release.native-staging.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'accepted':True,'files':copied,'state':packet['state'],'product_execution':False,'installation':False,'orchestration_history':'One local packet-read orchestration failed at undefined JavaScript require before any native transfer or staging. Corrected transfer only; no product process.'}
b=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode()
with (root/'stage-receipt-v1.json').open('xb') as f:f.write(b)
print(json.dumps({'accepted':True,'files':19,'receipt_bytes':len(b),'receipt_sha256':hashlib.sha256(b).hexdigest(),'installation':False}))
