"""Seal original own support and assembler inputs from explicit reviewed paths."""
import hashlib,json,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PREFIX="docs/qualification/explorer-browser-explain-root-d3745/"
LOOM=Path("/home/jacob/hamon/receiving/loom-d3745-towerops-explain/publication-inputs.json")
EXPECTED_LOOM_SHA="bb7a680c8b1dbc5ea93bb63d1666d63487879d38b06cacd8cfb8ae6351bdb9ae"
def identity(p):
    b=p.read_bytes();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
def emit(p,obj):
    b=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode()
    with p.open("xb") as f:f.write(b)
    return identity(p)
raw=LOOM.read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED_LOOM_SHA:raise RuntimeError("original independent descriptor pin")
peer=json.loads(raw)
if peer["prefix"]!=PREFIX+"independent/":raise RuntimeError("independent prefix")
copy=ROOT/"inputs/independent-publication-inputs-v1.json"
with copy.open("xb") as f:f.write(raw)
paths=[
("README.md","inputs/README.md"),
("source-authority-v1.json","inputs/source-authority-v1.json"),
("source-binding.json","inputs/source-binding.json"),
("maintained-tool-provenance.json","inputs/maintained-tool-provenance.json"),
("author-publication-inputs-v1.json","inputs/author-publication-inputs-v1.json"),
("independent-publication-inputs-v1.json","inputs/independent-publication-inputs-v1.json"),
("reviews/source-review-v1.json","inputs/issue132-source-review-v1.json"),
("reviews/harness-review-v1.json","inputs/issue132-harness-review-v1.json"),
("reviews/browser-review-v1.json","inputs/issue132-browser-review-v1.json"),
("reviews/layout-review-v1.json","inputs/issue132-layout-review-v1.json"),
("reviews/author-evidence-custody.json","inputs/author-evidence-custody.json"),
("publication/audit-browser-receiving.py","audit-browser-receiving.py"),
("publication/audit-layout-receiving.py","audit-layout-receiving.py"),
("publication/stage-author-evidence.py","stage-author-evidence.py"),
("publication/prepare-support-inputs.py","prepare-support-inputs.py"),
("publication/assemble-publication-v1.py","assemble-publication-v1.py"),
("publication/seal-own-support-v1.py","seal-own-support-v1.py")
]
records=[]
for dest,rel in paths:
    p=ROOT/rel
    if not p.is_file() or p.is_symlink():raise RuntimeError("regular support")
    records.append({"path":PREFIX+dest,"source_path":str(p),"mode":"100644","native_mode":oct(stat.S_IMODE(p.stat().st_mode)),**identity(p)})
ownpath=ROOT/"inputs/own-support-authority-v1.json"
ownid=emit(ownpath,{"schema":"hamon.anvil.explorer-browser-own-support.v1","basis":"Original own-authored exact files selected by explicit fixed path tuples, not from proposed selection or descriptor substrings.","files":records})
config={"base_commit":"6991198cde605b683331290c8c898ac5dbec6643","base_tree":"bf63ce7b3ac761bf02c9184747575f989a2876ab","source_authority":{"path":str(ROOT/"inputs/source-authority-v1.json"),"sha256":"46ba9d2012c190be8b70d2cdbd28a6b3cd10801a592f4a85cda4c6c5ba8af5b4"},"own_support_authority":{"path":str(ownpath),"sha256":ownid["sha256"]},"author_descriptor":{"path":str(ROOT/"inputs/author-publication-inputs-v1.json"),"sha256":"c85bb1ff6cc1ec08ffefb4a841303ec5874518455ece9defdbb87b9a1e44830a"},"independent_descriptor":{"path":str(LOOM),"sha256":EXPECTED_LOOM_SHA}}
configid=emit(ROOT/"inputs/assembly-inputs-v1.json",config)
print(json.dumps({"own_support_records":len(records),"peer_records":len(peer["files"]),"own_authority":ownid,"config":configid}))
