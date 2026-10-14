import pathlib,json,hashlib,stat,datetime
root=pathlib.Path(__file__).resolve().parent
native='/home/jacob/hamon/receiving/anvil-d3745-towerops-settings/'
def same(a,b):
    if isinstance(a,bool) or isinstance(b,bool):return type(a)==type(b) and a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return a==b
    if type(a)!=type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b
summaries=[]
for variant,count in [('original',24),('candidate',78)]:
    mirror=root/(variant+'-native-mirror')
    p=mirror/(variant+'-browser-v2/receipt.json');raw=p.read_bytes();r=json.loads(raw)
    assert r['accepted'] and len(r['checks'])==count
    assert all(same(c['actual'],c['expected']) and c['pass'] for c in r['checks'])
    def body(item):
        q=mirror/item['path'].removeprefix(native);b=q.read_bytes()
        assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==item['git_blob']
        assert stat.S_IMODE(q.stat().st_mode)==item['mode'];return b
    for row in r['http']:
        assert body(row['backend_stream']).decode()==row['backend_body']
        if 'request_stream' in row:assert body(row['request_stream']).decode()==row['request_body']
    for key in ['backend_stdout','backend_stderr']:body(r[key])
    for d in r['downloads']:assert hashlib.sha256(body(d['actual'])).hexdigest()==d['expected_sha256']
    for s in r['screenshots']:body(s)
    for kind in ['source','controls','fixtures']:assert r[kind+'_before']==r[kind+'_after']
    for key in ['context_closed','browser_closed','relay_closed','backend_closed','backend_listener_closed','relay_listener_closed']:assert r[key] is True
    assert r['browser_exit_code']==0 and r['backend_exit']=={'code':0,'signal':None} and r['open_relay_sockets']==0
    assert r['error'] is None and not r['page_errors'] and not r['failed_requests'] and not r['external_requests']
    summaries.append({'variant':variant,'receipt_bytes':len(raw),'receipt_sha256':hashlib.sha256(raw).hexdigest(),
                      'checks_recomputed':count,'http':len(r['http']),'posts':sum(x['method']=='POST' for x in r['http']),
                      'runs':sum(x['path']=='/api/run' for x in r['http']),'downloads':r['downloads'],
                      'raw_relay_streams_verified':sum(1+('request_stream' in x) for x in r['http'])+2,
                      'screenshots':r['screenshots'],'source_controls_fixtures_preserved':True,'closure_accepted':True})
out={'schema':'anvil.towerops-settings.saved-course-audit.v1','accepted':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'method':'Read-only complete JSON predicates, raw stream bytes and local mirrored payload identities; no product execution.',
     'courses':summaries,'total_comparisons_recomputed':102,'product_replay':False}
with (root/'saved-course-audit-v1.json').open('x') as f:f.write(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'accepted':True,'comparisons':102,'relay_streams':sum(x['raw_relay_streams_verified'] for x in summaries)}))
