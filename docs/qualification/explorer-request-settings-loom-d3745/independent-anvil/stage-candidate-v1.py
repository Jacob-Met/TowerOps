import base64, datetime, hashlib, json, os, pathlib, pwd, socket, stat

root = pathlib.Path('/home/jacob/hamon/receiving/anvil-d3745-towerops-settings')
def identity(p):
    b = p.read_bytes()
    assert p.is_file() and not p.is_symlink()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
            'mode':stat.S_IMODE(p.stat().st_mode)}
assert os.getuid() == 1000 and pwd.getpwuid(os.getuid()).pw_dir == '/home/jacob'
assert socket.gethostname() == 'hamon-thinkpad'
incoming = root/'incoming-candidate-v1.json'
assert identity(incoming)['sha256'] == '8b4a6987e23019f0c80233d4f15c46a078a46c7ad58d5f9b3a3d72498380c8c6'
packet = json.loads(incoming.read_bytes())
offer_raw = base64.b64decode(packet['offer_base64'], validate=True)
assert hashlib.sha256(offer_raw).hexdigest() == '80710c05cf9dd536b159e35233c55c593e8cb71311645920e09ebe65ca140462'
offer = json.loads(offer_raw)
assert [{k:v for k,v in r.items() if k!='base64'} for r in packet['files']] == offer['files']
allowed = {'EXPLORER.md','explorer.py','replay_explain.py','scenarios.py','towerops.py','web/app.js','web/index.html','web/style.css'}
assert len(packet['files']) == 8 and {r['path'] for r in packet['files']} == allowed
original = [identity(root/'original-browser-v2/receipt.json'), identity(root/'original-fixtures/receipt.json')]
assert original[0]['sha256'] == 'b31cddb0a289fd49f7d0344818ea53ce9ac8d0197deb29f75ae69d173eaeb8bd'
assert original[1]['sha256'] == '1d17edb8f04daf6cdb428e199789c7a61dec72a3e27d92667f0090519699f031'
assert identity(root/'receive-settings-v2.cjs')['sha256'] == 'dd5dfbf9667cbe2ce788eaf022dd7cf9874cd74fc04d25b163e94a704db30aee'
for name in ['candidate','candidate-spec-v1.json','candidate-browser-v2','candidate-stage-receipt-v1.json']:
    assert not (root/name).exists(), name
captured = []
for r in packet['files']:
    b = base64.b64decode(r['base64'], validate=True)
    assert len(b) == r['bytes'] and hashlib.sha256(b).hexdigest() == r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest() == r['git_blob']
    assert r['mode'] in (420,493)
    captured.append((r,b))
dest = root/'candidate'
dest.mkdir()
(dest/'web').mkdir()
for r,b in captured:
    p = dest/r['path']
    with p.open('xb') as f: f.write(b)
    p.chmod(r['mode'])
    got=identity(p)
    assert all(got[k] == r[k] for k in ('bytes','sha256','git_blob','mode'))
spec = {'schema':'anvil.towerops-settings.source-spec.v1','variant':'candidate',
        'source_commit':None,'source_tree':None,'base_commit':offer['base_commit'],
        'publication_state_at_receiving':offer['state'], 'original_offer_sha256':packet['offer_sha256'],
        'source_root':str(dest),'source_files':[{k:r[k] for k in ('path','bytes','sha256','git_blob','mode')} for r in offer['files']],
        'fixture_receipt':{'path':original[1]['path'],'sha256':original[1]['sha256']},
        'python':'/usr/bin/python3','browser_module':'/home/jacob/.local/lib/node_modules/@wonderwhy-er/desktop-commander/node_modules/puppeteer',
        'browser_executable':'/usr/bin/firefox','candidate_exposure':True,
        'exposure_scope':'Exact source bodies first received after original accepted course and root source release; frozen V2 controller unchanged.'}
with (root/'candidate-spec-v1.json').open('x') as f: f.write(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
assert [identity(pathlib.Path(r['path'])) for r in original] == original
receipt = {'schema':'anvil.towerops-settings.candidate-admission.v1','accepted':True,
           'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),
           'incoming':identity(incoming),'offered':offer,'copied':[identity(dest/r['path']) for r in offer['files']],
           'spec':identity(root/'candidate-spec-v1.json'),'original_receipts_preserved':original,
           'product_execution':False}
with (root/'candidate-stage-receipt-v1.json').open('x') as f:f.write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'accepted':True,'files':len(captured),'spec':identity(root/'candidate-spec-v1.json'),'receipt':identity(root/'candidate-stage-receipt-v1.json')}))
