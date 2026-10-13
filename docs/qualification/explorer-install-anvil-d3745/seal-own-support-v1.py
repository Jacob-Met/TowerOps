"""Seal a fixed original support list; never infer roles from candidate output paths."""
import hashlib,json,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PREFIX="docs/qualification/explorer-install-anvil-d3745/"
def ident(p):
 b=p.read_bytes();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"native_mode":oct(stat.S_IMODE(p.stat().st_mode))}
def emit(p,value):
 with p.open("x") as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write("\n")
 return ident(p)
source=ROOT/"source-authority-v1.json"
author=ROOT/"author-publication-inputs-v1.json"
peer=ROOT/"inputs/independent-publication-inputs-v1.json"
names=[
("README.md","inputs/README.md"),
("source-binding.json","inputs/source-binding.json"),
("source-authority-v1.json","source-authority-v1.json"),
("author-publication-inputs-v1.json","author-publication-inputs-v1.json"),
("independent-publication-inputs-v1.json","inputs/independent-publication-inputs-v1.json"),
("maintained-tool-provenance.json","inputs/maintained-tool-provenance.json"),
("publication-base.json","inputs/publication-base.json"),
("root-source-review-v1.json","inputs/root-source-review-v1.json"),
("root-harness-review-v1.json","inputs/root-harness-review-v1.json"),
("root-harness-review-v2.json","inputs/root-harness-review-v2.json"),
("forge-ordering-review.json","inputs/forge-ordering-review.json"),
("independent-receiving-review.json","inputs/independent-receiving-review.json"),
("audit-independent-v1.py","audit-independent-v1.py"),
("assemble-publication-v1.py","assemble-publication-v1.py"),
("seal-author-v1.py","seal-author-v1.py"),
("prepare-publication-inputs-v1.py","prepare-publication-inputs-v1.py"),
("seal-own-support-v1.py","seal-own-support-v1.py")]
rows=[]
for dest,origin in names:
 p=ROOT/origin;rows.append(dict(path=PREFIX+dest,source_path=str(p),mode="100644",purpose="Explicit original publication support: "+dest,**ident(p)))
binding=json.loads((ROOT/"inputs/source-binding.json").read_bytes())
for original in binding["accepted_runtime_support"]:
 p=Path(original["source_path"]);x=ident(p)
 if any(x[k]!=original[k] for k in ("bytes","sha256","git_blob")):raise RuntimeError("Accepted runtime support changed")
 rows.append(dict(path=original["path"],source_path=str(p),mode="100755" if x["native_mode"]=="0o755" else "100644",purpose="Exact fixed c77 accepted runtime/guide dependency",**x))
if len({x["path"] for x in rows})!=len(rows):raise RuntimeError("Duplicate support destination")
own=ROOT/"inputs/own-support-authority-v1.json"
ownid=emit(own,{"schema":"hamon.anvil.explorer-install.own-support-authority.v1","files":rows,"notes":["Original explicit17-file support list and eight frozen accepted runtime rows; not derived from selected output or Git tree."]})
cfg={"base_commit":"db62f253a0b0b2b8fe80a5412a2bdf38ec7c720d","base_tree":"834cd97dde6632fed687c1eed3a23c0c9d9bf692",
"source_authority":dict(path=str(source),**ident(source)),"own_support_authority":dict(path=str(own),**ownid),
"author_descriptor":dict(path=str(author),**ident(author)),"independent_descriptor":dict(path=str(peer),**ident(peer))}
cfgid=emit(ROOT/"inputs/assembly-inputs-v1.json",cfg)
print(json.dumps({"support_rows":len(rows),"own_support":ownid,"assembly_inputs":cfgid,"original_author":cfg["author_descriptor"],"original_peer":cfg["independent_descriptor"]}))
