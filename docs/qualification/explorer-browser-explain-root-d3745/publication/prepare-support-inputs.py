"""Seal explicit source binding and maintained-tool provenance from retained inputs."""
import hashlib,json,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def ident(p):
    b=p.read_bytes()
    return {"path":str(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"native_mode":oct(stat.S_IMODE(p.stat().st_mode))}
def emit(name,obj):
    p=ROOT/"inputs"/name;b=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode()
    with p.open("xb") as f:f.write(b)
    return ident(p)
a=json.loads((ROOT/"inputs/source-authority-v1.json").read_bytes())
packet=json.loads(Path(a["original_packet"]["path"]).read_bytes())
source_paths=set(a["source_allowlist"])
binding={"schema":"hamon.anvil.explorer-browser-source-binding.v1","authored_base":a["base"],"authored_base_tree":a["base_tree"],"source_authority":ident(ROOT/"inputs/source-authority-v1.json"),"original_packet":a["original_packet"],"selected_source":a["source_files"],"unchanged_packet_closure":[r for r in packet["files"] if r["path"] not in source_paths],"author_descriptor":ident(ROOT/"inputs/author-publication-inputs-v1.json"),"receiving_state":"Frozen unpublished candidate; later repository publication does not change execution identity.","limits":["Eight explicit source paths only; six modified and two new focused tests.","The independent browser source projection has eight runtime leaves; author packet has twelve runtime/test leaves.","Anvil source/harness/receipt audits execute no product or browser.","Fresh full base preservation and expected-head adoption are separate checks."]}
for row in binding["unchanged_packet_closure"]:row.pop("content",None)
ids=[emit("source-binding.json",binding)]
expected={"prepare_git_objects.py":"fb6596df63889b6b72038e3921b9144b802cc9546f9617705cfd112b57dab676","receive_source.py":"90af676b35c39f3cb1a3295d94a31a752893265af3a73292e2b2b22fb2750f35","validate_publication_layout.py":"09e931bcdb5d1ec5e55d76c8123a973a75a2d5072c6ffb84b302ddac8f443907"}
rows=[]
for name,sha in expected.items():
    x=ident(ROOT/"tools"/name)
    if x["sha256"]!=sha:raise RuntimeError("Maintained tool changed")
    rows.append(dict(x,repository_path=name))
ids.append(emit("maintained-tool-provenance.json",{"schema":"hamon.anvil.publication-tools.v1","repository":"Jacob-Met/estate-push-tools","commit":"c00eadc94f81d2e8608a6e8a23bcfa9b201646a6","files":rows,"guide":{"path":"docs/prepare-git-objects.md","git_blob":"2e592c7e3b06ce9c11a21acb0150a90ac64f42cb"},"scope":"All three complete source bodies fetched at the same commit and admitted unchanged; no tool test replay.","inherited_towerops_workflows":[{"path":".github/workflows/airspace-demo.yml","git_blob":"24356d4f5ce88f21cc1a27329b06df351e156810"},{"path":".github/workflows/ci.yml","git_blob":"4791e16741c2ee136585d8f4d99f918535a3a017"}],"no_actions":"No workflow changes or runs requested. Ordinary publication commit requires skip-ci/skip-actions and skip-checks markers."}))
print(json.dumps(ids))
