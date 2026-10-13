import pathlib,json,hashlib,stat,base64,gzip,datetime,urllib.parse
root=pathlib.Path('/home/jacob/hamon/receiving/loom-d3745-towerops-replay-selection')
p=root/'original-v1/receipt.json';raw=p.read_bytes();v=json.loads(raw)
def ident(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':'0o'+oct(stat.S_IMODE(p.stat().st_mode))[2:]}
assert v['accepted'] is False and v['error'] is None
assert len(v['checks'])==23
for c in v['checks']:assert c['pass']==(c['actual']==c['expected'])
intended=['newer-file.final-status','cleared-file.immediate-status','cleared-file.final-status']
observed=[c['id'] for c in v['checks'] if not c['pass']]
assert sorted(observed)==sorted(intended+['newer-file.no-external-requests','cleared-file.no-external-requests'])
assert v['browser_closed'] and v['server_closed'] and v['open_socket_count']==0
assert v['browser_exit_code']==0
fonts=[];courses=[]
for c in v['courses']:
 assert len(c['external_requests'])==1 and not c['page_errors'] and not c['failed_requests']
 u=c['external_requests'][0];assert urllib.parse.urlsplit(u).scheme=='data' and u.startswith('data:font/woff2;base64,')
 font=base64.b64decode(u.split(',',1)[1],validate=True);assert font[:4]==b'wOF2'
 fonts.append({'mime':'font/woff2','url_bytes':len(u.encode()),'url_sha256':hashlib.sha256(u.encode()).hexdigest(),'decoded_bytes':len(font),'decoded_sha256':hashlib.sha256(font).hexdigest()})
 assert c['finished'].count(c['held_label'])==1
 assert c['display_before']==c['display_after']
 expected=['/api/run','/api/replay','/api/replay'] if c['name']=='newer-file' else ['/api/run','/api/replay']
 assert [r['path'] for r in c['requests']]==expected
 for r in c['requests']:assert len(r['body'].encode())==r['bytes'] and hashlib.sha256(r['body'].encode()).hexdigest()==r['sha256']
 assert c['final_status']==v['expected_original_late_status']
 courses.append({'name':c['name'],'request_paths':expected,'finished':c['finished'],'final_status':c['final_status'],'retained_inline_url':u,'remote_requests':[]})
assert fonts[0]==fonts[1]
for before,after in [('source_before','source_after'),('controls_before','controls_after'),('fixture_before','fixture_after')]:
 assert v[before]==v[after]
 for row in v[before]:assert ident(pathlib.Path(row['path']))==row
for command in v['commands']:
 for stream in ['stdout','stderr']:assert ident(pathlib.Path(command[stream]['path']))==command[stream]
assert [x['status'] for x in v['commands']]==[0,0,1]
for row in v['screenshots']:assert ident(pathlib.Path(row['path']))==row
a=pathlib.Path(v['fixture_before'][0]['path']).read_bytes();b=pathlib.Path(v['fixture_before'][1]['path']).read_bytes()
assert a==pathlib.Path(v['commands'][0]['stdout']['path']).read_bytes()
expectedB=json.loads(a);expectedB['after']['version']+=1;assert json.loads(b)==expectedB
audit={'schema':'hamon.loom.towerops-original-inline-classification-audit.v1','accepted_original_behavior':True,'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_receipt':ident(p),'raw_original_accepted':False,'observed_failed_ids':observed,'intended_behavior_failed_ids':intended,'logger_classification':'URL protocol data: is an inline nonnetwork resource; retain exact observed font URLs separately. All other URLs outside exact loopback origin remain failures in v2.','observed_fonts':fonts,'courses':courses,'checks_recomputed':23,'commands_verified':3,'streams_verified':6,'screenshots_verified':3,'source_files_verified':8,'controls_verified':4,'fixtures_verified':2,'browser_exit':v['browser_exit_code'],'closed_server_socket_count':v['open_socket_count'],'no_product_or_browser_replay':True,'limits':'Page observations do not establish an OS network audit. Clear selection is authored DOM change; HTML/browser race scope remains only two retained courses.'}
dest=root/'original-inline-classification-audit.json'
data=(json.dumps(audit,indent=2,ensure_ascii=False)+'\n').encode()
with dest.open('xb') as f:f.write(data)
print(json.dumps({'accepted_original_behavior':True,'audit':ident(dest),'original_receipt':ident(p),'fonts':fonts,'raw_receipt_gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode(),'audit_body':audit}))
