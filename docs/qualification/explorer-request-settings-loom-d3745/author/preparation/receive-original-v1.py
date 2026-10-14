import datetime,hashlib,json,pathlib,stat,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'original-observation-v1';OUT.mkdir()
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':stat.S_IMODE(p.stat().st_mode)}
files=[p for p in (ROOT/'original').rglob('*') if p.is_file()]
before={str(p.relative_to(ROOT/'original')):identity(p) for p in files}
commands=[]
def run(label,args,cwd):
 with (OUT/(label+'.stdout')).open('xb') as o,(OUT/(label+'.stderr')).open('xb') as e:
  p=subprocess.run(args,cwd=cwd,stdout=o,stderr=e,timeout=30)
 row={'label':label,'argv':args,'cwd':str(cwd),'exit_code':p.returncode,'stdout':identity(OUT/(label+'.stdout')),'stderr':identity(OUT/(label+'.stderr'))};commands.append(row)
 if p.returncode:raise RuntimeError(label+' exited '+str(p.returncode))
 return OUT/(label+'.stdout')
accepted=False;error=None
try:
 fixture=run('original-export',[sys.executable,'-B','explorer.py','run','missing_ack'],ROOT/'original')
 reply=run('original-replay',[sys.executable,'-B','explorer.py','replay',str(fixture)],ROOT/'original')
 result=run('original-ui',['node',str(ROOT/'preparation/observe-original-v1.cjs'),str(ROOT/'original'),str(fixture),str(reply)],ROOT)
 actual=json.loads(result.read_text());assert actual['accepted'] and len(actual['checks'])==7
 after={str(p.relative_to(ROOT/'original')):identity(p) for p in (ROOT/'original').rglob('*') if p.is_file()};assert after==before
 accepted=True
except Exception as e:error=str(e)
receipt={'schema':'hamon.loom.towerops-settings.original-course.v1','finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_implemented':False,'accepted':accepted,'error':error,'source_commit':'202782f29f3a0ed1411e67a7744f9e63f26926f1','commands':commands,'source_before':before,'source_after':{str(p.relative_to(ROOT/'original')):identity(p) for p in (ROOT/'original').rglob('*') if p.is_file()},'scope':'Original native fixed-fixture export/replay and controlled browser-script missing-action witness; no actual browser or network.'}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'accepted':accepted,'commands':len(commands),'error':error,'receipt':str(OUT/'receipt.json')}))
raise SystemExit(0 if accepted else 1)
