"""Independent actual CLI receiving for TowerOps optional replay explanations."""
import argparse, copy, hashlib, json, os, pathlib, subprocess, sys
from datetime import datetime, timezone

def identity(path):
    body=path.read_bytes()
    return {"path":str(path),"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),
            "git_blob":hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest(),
            "mode":path.stat().st_mode & 0o777}

def stable(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(",",":"),allow_nan=False)

def present(kind,value):
    return {"present":True,"type":kind,"value":value}

def difference(path,kind,expected,actual):
    return {"path":path,"kind":kind,"expected":expected,"actual":actual}

parser=argparse.ArgumentParser()
parser.add_argument("spec",type=pathlib.Path)
parser.add_argument("out",type=pathlib.Path)
parser.add_argument("variant",choices=["original","candidate"])
args=parser.parse_args()
spec=json.loads(args.spec.read_text())
source=pathlib.Path(spec["source"]).resolve()
assert args.out.is_absolute() and not args.out.exists()
assert spec["variant"]==args.variant
names=lambda:sorted(str(p.relative_to(source)) for p in source.rglob("*") if p.is_file())
before=[identity(source/x["path"]) for x in spec["files"]]
for row,expected in zip(before,spec["files"]):
    assert all(row[k]==expected[k] for k in ["bytes","sha256","git_blob","mode"])
original_names=names()
controls=[identity(pathlib.Path(__file__)),identity(args.spec)]
args.out.mkdir()
(args.out/"streams").mkdir()
(args.out/"inputs").mkdir()
receipt={"schema":"hamon.root.towerops-replay-explain-cli.v1","started_utc":datetime.now(timezone.utc).isoformat(),
         "variant":args.variant,"spec":spec,"source_before":before,"controls_before":controls,
         "commands":[],"checks":[],"error":None}
def check(label,actual,expected):
    ok=stable(actual)==stable(expected)
    receipt["checks"].append({"id":label,"actual":actual,"expected":expected,"pass":ok})
    if not ok: raise AssertionError(label)
def invoke(label,tail,exitcode,full=False):
    input_before=[identity(p) for p in sorted((args.out/"inputs").iterdir())]
    command=[sys.executable,"-B",str(source/"explorer.py"),*map(str,tail)]
    env={k:v for k,v in os.environ.items() if not k.startswith("PYTHON")}
    env["PYTHONDONTWRITEBYTECODE"]="1"
    if full:
        with open("/dev/full","wb",buffering=0) as sink:
            result=subprocess.run(command,cwd=args.out,env=env,stdout=sink,stderr=subprocess.PIPE,timeout=15)
        stdout=b""
    else:
        result=subprocess.run(command,cwd=args.out,env=env,capture_output=True,timeout=15)
        stdout=result.stdout
    for key,body in [("stdout",stdout),("stderr",result.stderr)]:
        (args.out/"streams"/(label+"."+key)).write_bytes(body)
    receipt["commands"].append({"id":label,"argv":command,"cwd":str(args.out),"returncode":result.returncode,
        "stdout_destination":"/dev/full" if full else "captured","stdout":stdout.decode("utf-8","replace"),
        "stderr":result.stderr.decode("utf-8","replace")})
    check(label+".exit",result.returncode,exitcode)
    check(label+".input-preserved",[identity(p) for p in sorted((args.out/"inputs").iterdir())],input_before)
    if exitcode in (0,1) and not full: check(label+".stderr",result.stderr.decode(),"")
    return stdout
def save(name,value):
    path=args.out/"inputs"/name
    path.write_bytes((json.dumps(value,ensure_ascii=True,indent=2)+"\n").encode())
    return path
def explain(label,path,expected,ordinary,truncated=False,exitcode=1):
    raw=invoke(label,["replay","--explain",path],exitcode)
    result=json.loads(raw)
    check(label+".field-set",sorted(result),sorted([*ordinary,"difference_limit","differences","differences_truncated"]))
    check(label+".ordinary",{k:result[k] for k in ordinary},ordinary)
    check(label+".limit",result["difference_limit"],32)
    check(label+".rows",result["differences"],expected)
    check(label+".truncated",result["differences_truncated"],truncated)
    return raw
try:
    A=json.loads(invoke("01-export-approved",["run","approved"],0))
    rejected=json.loads(invoke("02-export-rejected",["run","missing_ack"],0))
    good=save("saved approved 東京.json",A)
    changed=copy.deepcopy(A);changed["after"]["version"]+=1
    bad=save("one-field.json",changed)
    match=json.loads(invoke("03-default-match",["replay",good],0))
    mismatch=json.loads(invoke("04-default-mismatch",["replay",bad],1))
    check("default.match",match["matches"],True)
    check("default.mismatch",mismatch["matches"],False)
    check("default.no-explanation",sorted(match),["audit_valid","expected_audit_head","matches","note","outcome","rejection_reason"])
    if args.variant=="original":
        out=invoke("05-original-unsupported",["replay",good,"--explain"],2)
        check("original.unsupported-no-json",out.decode(),"")
        check("original.flag-named","--explain" in receipt["commands"][-1]["stderr"],True)
    else:
        explain("05-exact",good,[],match,exitcode=0)
        single=[difference("/after/version","value",present("number",A["after"]["version"]),present("number",changed["after"]["version"]))]
        first=explain("06-one-field",bad,single,mismatch)
        many=copy.deepcopy(A)
        many["after"]["aircraft"].pop()
        many["audit_events"].append(None)
        many["audit_valid"]=1
        del many["description"]
        many["diagnostic~/東京"]=None
        many["fixtures"]["approval"]=None
        many["rejection_reason"]=False
        many_path=save("typed and missing.json",many)
        rows=[
          difference("/after/aircraft/1","missing",present("object",A["after"]["aircraft"][1]),{"present":False}),
          difference("/audit_events/"+str(len(A["audit_events"])),"unexpected",{"present":False},present("null",None)),
          difference("/audit_valid","type",present("boolean",True),present("number",1)),
          difference("/description","missing",present("string",A["description"]),{"present":False}),
          difference("/diagnostic~0~1東京","unexpected",{"present":False},present("null",None)),
          difference("/fixtures/approval","type",present("object",A["fixtures"]["approval"]),present("null",None)),
          difference("/rejection_reason","type",present("null",None),present("boolean",False))]
        explain("07-typed-missing-pointers",many_path,rows,mismatch)
        numeric=copy.deepcopy(A)
        numeric["before"]["observed_at"]=int(numeric["before"]["observed_at"])
        numeric["after"]["version"]=float(numeric["after"]["version"])
        explain("08-numeric-equivalence",save("numbers.json",numeric),[],match,exitcode=0)
        reject_path=save("native rejection.json",rejected)
        reject_reply=json.loads(invoke("09-default-rejected",["replay",reject_path],0))
        explain("10-rejected-reproducible",reject_path,[],reject_reply,exitcode=0)
        for count in (32,33):
            cap=copy.deepcopy(A)
            for i in range(count):cap["z"+str(i).zfill(3)]=i
            caprows=[difference("/z"+str(i).zfill(3),"unexpected",{"present":False},present("number",i)) for i in range(32)]
            explain("11-cap-"+str(count),save("cap-"+str(count)+".json",cap),caprows,mismatch,truncated=count==33)
        invalid=args.out/"inputs"/"caller correction.json"
        invalid.write_bytes(b'{"x":NaN}')
        b=invoke("12-nonfinite",["replay",invalid,"--explain"],2)
        check("nonfinite.no-json",b.decode(),"")
        invalid.write_bytes((json.dumps(A,indent=2)+"\n").encode())
        explain("13-explicit-correction",invalid,[],match,exitcode=0)
        for label,body in [("invalid-utf8",b"\xff"),("overflow",b'{"x":1e999}'),("oversized",b" "*262145)]:
            p=args.out/"inputs"/(label+".json");p.write_bytes(body)
            raw=invoke("14-"+label,["replay",p,"--explain"],2)
            check(label+".no-json",raw.decode(),"")
        second=invoke("15-repeat-one-field",["replay",bad,"--explain"],1)
        check("deterministic.bytes",hashlib.sha256(first).hexdigest(),hashlib.sha256(second).hexdigest())
        if os.path.exists("/dev/full"):
            invoke("16-output-failure",["replay",good,"--explain"],2,full=True)
            check("output-failure.diagnostic",bool(receipt["commands"][-1]["stderr"]),True)
    receipt["inputs"]=[identity(p) for p in sorted((args.out/"inputs").iterdir())]
except Exception as exc:
    receipt["error"]=repr(exc)
finally:
    receipt["source_after"]=[identity(source/x["path"]) for x in spec["files"]]
    receipt["controls_after"]=[identity(pathlib.Path(__file__)),identity(args.spec)]
    receipt["source_names_after"]=names()
    receipt["source_preserved"]=before==receipt["source_after"] and original_names==names()
    receipt["controls_preserved"]=controls==receipt["controls_after"]
    receipt["accepted"]=receipt["error"] is None and receipt["source_preserved"] and receipt["controls_preserved"] and all(x["pass"] for x in receipt["checks"])
    receipt["finished_utc"]=datetime.now(timezone.utc).isoformat()
    (args.out/"receipt.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=True)+"\n")
    print(json.dumps({"accepted":receipt["accepted"],"variant":args.variant,"commands":len(receipt["commands"]),"checks":len(receipt["checks"]),"error":receipt["error"],"receipt":str(args.out/"receipt.json")}))
    sys.exit(0 if receipt["accepted"] else 1)
