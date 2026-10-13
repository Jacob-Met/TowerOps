"""Copy exact maintained publication tools and peer review inputs into owned staging."""
import hashlib,json,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=Path("/home/jacob/hamon/receiving/anvil-d3745-browser-explain-publication")
def ident(p):
 b=p.read_bytes();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"native_mode":oct(stat.S_IMODE(p.stat().st_mode))}
(ROOT/"tools").mkdir();(ROOT/"inputs").mkdir()
expected={"prepare_git_objects.py":"fb6596df63889b6b72038e3921b9144b802cc9546f9617705cfd112b57dab676","receive_source.py":"90af676b35c39f3cb1a3295d94a31a752893265af3a73292e2b2b22fb2750f35","validate_publication_layout.py":"09e931bcdb5d1ec5e55d76c8123a973a75a2d5072c6ffb84b302ddac8f443907"}
rows=[]
for name,sha in expected.items():
 p=OLD/"tools"/name;b=p.read_bytes()
 if hashlib.sha256(b).hexdigest()!=sha:raise RuntimeError("Maintained donor mismatch")
 target=ROOT/"tools"/name
 with target.open("xb") as f:f.write(b)
 target.chmod(0o644)
 if p.read_bytes()!=b:raise RuntimeError("Donor changed")
 rows.append(dict(path=str(target),repository_path=name,**ident(target)))
provenance={"schema":"hamon.anvil.explorer-install.publication-tools.v1","repository":"Jacob-Met/estate-push-tools","commit":"c00eadc94f81d2e8608a6e8a23bcfa9b201646a6","files":rows,"scope":"Exact already authenticated maintained three-file projection copied read-only; no tool modification or tool-suite replay."}
with (ROOT/"inputs/maintained-tool-provenance.json").open("x") as f:json.dump(provenance,f,indent=2);f.write("\n")
for name in ("source-review-v1.json","harness-review-v1.json"):
 p=Path("/home/jacob/hamon/receiving/root-d3745-towerops-install")/name;b=p.read_bytes()
 target=ROOT/"inputs"/("root-"+name)
 with target.open("xb") as f:f.write(b)
 if p.read_bytes()!=b:raise RuntimeError("Review donor changed")
print(json.dumps({"tools":rows,"peer_reviews":[dict(path=str(ROOT/"inputs"/("root-"+n)),**ident(ROOT/"inputs"/("root-"+n))) for n in ("source-review-v1.json","harness-review-v1.json")]}))
