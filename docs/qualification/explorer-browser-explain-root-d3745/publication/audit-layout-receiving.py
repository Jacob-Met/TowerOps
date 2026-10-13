"""Read-only audit of the separate saved-C visual observation, not a replay."""
from pathlib import Path
import datetime,hashlib,json,stat
BASE=Path("/home/jacob/hamon/receiving/loom-d3745-towerops-explain")
OWN=Path(__file__).resolve().parent
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
def identity(p):
    p=Path(p);need(p.is_file() and not p.is_symlink(),"regular")
    b=p.read_bytes();return {"path":str(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"mode":oct(stat.S_IMODE(p.stat().st_mode))}
def verify(row):
    got=identity(row["path"]);need(all(got[k]==row[k] for k in ("bytes","sha256","mode")),"file identity");return got
def equal(a,b):
    if type(a)!=type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b
p=BASE/"visual-C-v2/receipt.json";rid=identity(p)
need(rid["bytes"]==37474 and rid["sha256"]=="0bc30d24398aa7a8c176203a16e16df4d38f745a765e4cd7337690bc48f34c2c","original receipt")
r=json.loads(p.read_bytes());need(r["accepted"] and len(r["checks"])==10,"outcome")
for c in r["checks"]:need(c["pass"] and equal(c["actual"],c["expected"]),"strict comparison")
need(r["inputs_before"]==r["inputs_after"] and r["inputs_preserved"],"source preservation")
inputs=[verify(x) for x in r["inputs_before"]]
images=[verify(x) for x in r["screenshots"]]
streams=[verify(r[k]) for k in ("backend.stdout","backend.stderr")]
need(r["browser_closed"] and r["browser_exit"]==0 and r["backend_closed"] and r["backend_exit"]=={"code":0,"signal":None},"closure")
need([x["path"] for x in r["requests"]]==["/api/replay","/api/replay/explain"],"two explicit posts")
need([x["status"] for x in r["responses"]]==[200,200],"real responses")
need(all(s["scrollWidth"]==s["clientWidth"] and s["whiteSpace"]=="pre-wrap" and s["overflowWrap"]=="anywhere" for row in r["dom"]["rows"] for s in row["sides"]),"six wrapping sides")
need(r["dom"]["document"]["scrollWidth"]==r["dom"]["document"]["clientWidth"],"page width")
need(r["last_row_visibility"]["visible"] and 0<=r["last_row_visibility"]["top"]<r["last_row_visibility"]["bottom"]<=1100,"scroll visibility")
prior=identity(BASE/"candidate-v2/receipt.json")
need(prior["bytes"]==689799 and prior["sha256"]=="ee3d0afd77da9bd6c6d3c37517956b4ad48ce1928c5f48774ddfcfdead584181","prior85 unchanged")
freeze=json.loads((BASE/"visual-freeze-v2.json").read_bytes())
for key in ("receiver","candidate_spec","prior_course","previous_freeze","previous_failure","patch"):
    x=freeze[key];g=identity(x["path"]);need(all(g[k]==x[k] for k in ("bytes","sha256")),"freeze chain")
report={"schema":"hamon.anvil.explorer-browser-layout-review.v1","accepted":True,"reviewed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"Read-only exact receipt/control audit and human-facing panel image inspection; no runtime replay","receipt":rid,"checks_recomputed":10,"requests":2,"source_control_inputs_exact":inputs,"screenshots_exact":images,"streams_exact":streams,"prior_85_course_unchanged":prior,"visual_observation":"Independently viewed the entire 1032px-wide details panel image. All three paths, two labeled side envelopes, explicit absent sides, boolean/number distinction, full nested literal value and closing delimiters are visible. The long description and markup-bearing string wrap inside their respective columns. No injected markup is rendered.","layout":{"viewport":r["dom"]["viewport"],"document":r["dom"]["document"],"last_row":r["last_row_visibility"],"all_six_sides_wrap_without_internal_horizontal_overflow":True},"version_history":"Visual v1 unsupported Firefox BiDi request.postData observer failure remains retained. V2 records supported request path/status and exact selected File text; prior behavioral course already retains full HTTP bodies.","limits":["One authored saved-C desktop layout at1440x1100; no mobile or arbitrary-value layout claim.","Post-exposure visual followup, distinct from frozen original15/candidate85 behavior.","Current image and DOM/identity inspection only; no extra browser campaign."],"browser_exit":0,"backend_exit":0}
out=OWN/"inputs/issue132-layout-review-v1.json";b=(json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode()
with out.open("xb") as f:f.write(b)
print(json.dumps(identity(out)))
