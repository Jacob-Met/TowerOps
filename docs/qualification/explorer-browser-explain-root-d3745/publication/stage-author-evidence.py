"""Stage original author evidence and verify retained streams without execution."""
import hashlib,json,stat
from pathlib import Path
ROOT=Path("/home/jacob/hamon/receiving/anvil-d3745-browser-explain-publication")
AUTHOR=Path("/home/jacob/hamon/receiving/root-d3745-browser-explain")
DESC=AUTHOR/"author-publication-inputs-v1.json"
raw=DESC.read_bytes()
def need(ok,message):
    if not ok: raise RuntimeError(message)
def ident(body):
    return dict(bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),git_blob=hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest())
need(len(raw)==6216 and hashlib.sha256(raw).hexdigest()=="c85bb1ff6cc1ec08ffefb4a841303ec5874518455ece9defdbb87b9a1e44830a","descriptor pin")
d=json.loads(raw); need(d["prefix"]=="docs/qualification/explorer-browser-explain-root-d3745/author/","prefix")
need(len(d["files"])==16,"16 original records")
pending=[]; seen=set()
for row in d["files"]:
    relative=Path(row["path"]); need(not relative.is_absolute() and ".." not in relative.parts and row["path"] not in seen,"path")
    seen.add(row["path"]); p=Path(row["source_path"]); need(p.is_file() and not p.is_symlink(),"regular")
    b=p.read_bytes(); obs=ident(b)
    need(all(obs[k]==row[k] for k in obs),"identity "+row["path"])
    need(oct(stat.S_IMODE(p.stat().st_mode))==row["native_mode"],"native mode")
    need(row["mode"]=="100644","Git mode")
    pending.append((row,b))
r=json.loads((AUTHOR/"author-receipt-v1.json").read_bytes())
need(r["accepted"] and r["source_preserved"] and r["source_before"]==r["source_after"],"author outcome")
need(len(r["commands"])==5 and len(r["source_before"])==12,"course shape")
checks=[]
for c in r["commands"]:
    need(c["exit_code"]==0,"command exit")
    for kind in ("stdout","stderr"):
        s=c[kind]; b=(AUTHOR/s["path"]).read_bytes()
        need(b==s["utf8"].encode("utf-8") and len(b)==s["bytes"] and hashlib.sha256(b).hexdigest()==s["sha256"],"stream")
        checks.append(dict(path=s["path"],bytes=len(b),sha256=s["sha256"]))
packet=json.loads((AUTHOR/"candidate-packet-v1.json").read_bytes())
for row in packet["files"]:
    need(r["source_before"][row["path"]]=={k:row[k] for k in ("bytes","sha256","mode")},"source binding")
for row,b in pending:
    out=ROOT/"publication-v1/selected"/d["prefix"]/row["path"]
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("xb") as f:f.write(b)
    out.chmod(0o644)
with (ROOT/"inputs/author-publication-inputs-v1.json").open("xb") as f:f.write(raw)
receipt={"schema":"hamon.anvil.author-evidence-custody.v1","scope":"Read-only audit and exact own-stage copying; no product or test execution","descriptor":ident(raw),"records":len(pending),"source_before_after_exact":True,"source_packet_bindings":12,"commands":5,"all_exits":0,"raw_streams":checks,"author_method_counts":[4,4,5,10,8],"accepted":True}
out=ROOT/"inputs/author-evidence-custody.json"; data=(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n").encode()
with out.open("xb") as f:f.write(data)
print(json.dumps({"accepted":True,"descriptor_records":16,"raw_streams":len(checks),"receipt":str(out),**ident(data)}))
