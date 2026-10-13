"""Seal original author inputs before publication selection; no Git or product execution."""
import hashlib,json,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PREFIX="docs/qualification/explorer-install-anvil-d3745/"
def need(ok,message):
 if not ok:raise RuntimeError(message)
def ident(path):
 b=path.read_bytes();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"native_mode":oct(stat.S_IMODE(path.stat().st_mode))}
def emit(path,value):
 b=(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode()
 with path.open("xb") as f:f.write(b)
 return ident(path)
source_names=["README.md","docs/EXPLORER_INSTALL.md","tests/test_explorer_install.py","tools/install_explorer.py"]
receipt=json.loads((ROOT/"evidence/author-v1/receipt.json").read_bytes())
frozen={x["path"]:x for x in receipt["before"]}
files=[];sources=[]
for name in source_names:
 p=ROOT/"candidate"/name;x=ident(p)
 need(all(x[k]==frozen[str(p)][k] for k in ("bytes","sha256","git_blob")),"consumed source bytes")
 mode="100755" if x["native_mode"]=="0o755" else "100644"
 sources.append(dict(path=name,source_path=str(p),mode=mode,**x))
 files.append(dict(path=name,content=p.read_text(),mode=mode,**x))
packet=ROOT/"evidence/source-packet-v1.json"
packetid=emit(packet,{"schema":"hamon.anvil.explorer-install.source-packet.v1","source_state":"unpublished candidate actually consumed by author course","files":files})
authority=ROOT/"source-authority-v1.json"
aid=emit(authority,{"schema":"hamon.anvil.explorer-install.source-authority.v1","base":"db62f253a0b0b2b8fe80a5412a2bdf38ec7c720d","base_tree":"834cd97dde6632fed687c1eed3a23c0c9d9bf692","source_allowlist":source_names,"source_files":sources,"original_packet":dict(path=str(packet),**packetid)})
rows=[]
explicit=[
("README.md","evidence/README.md"),
("staging.json","evidence/staging.json"),
("stage-v1.py","evidence/stage-v1.py"),
("stage-v2.py","evidence/stage-v2.py"),
("staging-input.json","evidence/staging-input.json"),
("staging-v1-refusal.json","evidence/staging-v1-refusal.json"),
("source-freeze-v1.json","evidence/source-freeze-v1.json"),
("source-packet-v1.json","evidence/source-packet-v1.json"),
("qualify-author-v1.py","qualify-author-v1.py"),
("author-v1/receipt.json","evidence/author-v1/receipt.json"),
("author-v1/normal.stdout","evidence/author-v1/normal.stdout"),
("author-v1/normal.stderr","evidence/author-v1/normal.stderr"),
("author-v1/optimized.stdout","evidence/author-v1/optimized.stdout"),
("author-v1/optimized.stderr","evidence/author-v1/optimized.stderr")]
for dest,origin in explicit:
 p=ROOT/origin;rows.append(dict(path=dest,source_path=str(p),mode="100644",**ident(p)))
descriptor=ROOT/"author-publication-inputs-v1.json"
did=emit(descriptor,{"schema":"hamon.anvil.explorer-install.author-inputs.v1","prefix":PREFIX+"author/","files":rows,"notes":["Four explicit product leaves; eight exact accepted runtime leaves are separate fixed support.","Raw author receipt unchanged; all current inputs reflect unpublished-at-execution state.","Descriptor is sealed from explicit original native paths, independent of any prepared selection or Git tree."]})
print(json.dumps({"source_authority":dict(path=str(authority),**aid),"source_packet":packetid,"author_descriptor":dict(path=str(descriptor),**did),"author_rows":len(rows),"source_rows":len(sources)}))
