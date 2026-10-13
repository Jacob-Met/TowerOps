"""Assemble an explicit reviewed source/support/original-descriptor union.
No network, Git calls, product execution or writes outside this owned stage.
"""
import base64,hashlib,json,stat,subprocess,sys
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
PREFIX="docs/qualification/explorer-browser-explain-root-d3745/"
def need(ok,message):
    if not ok: raise RuntimeError(message)
def digest(b):
    return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
def raw_json(path,sha):
    p=Path(path); need(p.is_file() and not p.is_symlink(),"regular JSON")
    b=p.read_bytes();need(hashlib.sha256(b).hexdigest()==sha,"JSON pin "+str(p));return json.loads(b),b
def portable(path):
    p=PurePosixPath(path)
    need(not p.is_absolute() and str(p)==path and all(x not in ("",".","..") for x in p.parts),"relative path")
    return p
def emit(path,data):
    b=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    with path.open("xb") as f:f.write(b)
    return digest(b)
cfg=json.loads((ROOT/"inputs/assembly-inputs-v1.json").read_bytes())
source,sraw=raw_json(cfg["source_authority"]["path"],cfg["source_authority"]["sha256"])
own,oraw=raw_json(cfg["own_support_authority"]["path"],cfg["own_support_authority"]["sha256"])
author,araw=raw_json(cfg["author_descriptor"]["path"],cfg["author_descriptor"]["sha256"])
peer,praw=raw_json(cfg["independent_descriptor"]["path"],cfg["independent_descriptor"]["sha256"])
need(author["prefix"]==PREFIX+"author/" and peer["prefix"]==PREFIX+"independent/","original prefixes")
need(source["base"]==cfg["base_commit"] and source["base_tree"]==cfg["base_tree"],"base authority")
packet,_=raw_json(source["original_packet"]["path"],source["original_packet"]["sha256"])
original={r["path"]:r for r in packet["files"]}
need(set(source["source_allowlist"])=={r["path"] for r in source["source_files"]},"source allowlist")
offer=[]
for row in source["source_files"]:
    b=original[row["path"]]["content"].encode("utf-8")
    mode="100755" if row["mode"]=="0o755" else "100644"
    offer.append(("source",dict(row,mode=mode),b))
for role,d in (("support",author),("evidence",peer)):
    for row in d["files"]:
        p=Path(row["source_path"]);need(p.is_file() and not p.is_symlink(),"regular original input")
        offer.append((role,dict(row,path=d["prefix"]+row["path"]),p.read_bytes()))
for row in own["files"]:
    p=Path(row["source_path"]);need(p.is_file() and not p.is_symlink(),"regular own support")
    offer.append(("support",row,p.read_bytes()))
records=[];seen=set();files=[];roles={"source":[],"support":[],"evidence":[]}
for role,row,b in offer:
    rel=portable(row["path"]);need(row["path"] not in seen,"duplicate destination");seen.add(row["path"])
    need(row["mode"] in ("100644","100755"),"regular Git mode")
    got=digest(b);need(all(got[k]==row[k] for k in ("bytes","sha256")),"original identity "+row["path"])
    if "git_blob" in row:need(got["git_blob"]==row["git_blob"],"original Git identity")
    need((not row["path"].startswith(PREFIX)) if role=="source" else row["path"].startswith(PREFIX),"role destination")
    path=ROOT/"publication-v1/selected"/rel
    if path.exists():
        need(not path.is_symlink() and path.read_bytes()==b and stat.S_IMODE(path.stat().st_mode)==int(row["mode"][-3:],8),"existing own selection exact")
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("xb") as f:f.write(b)
        path.chmod(int(row["mode"][-3:],8))
    policyrow={k:row[k] for k in ("path","mode","bytes","sha256")}
    roles[role].append(policyrow)
    files.append({"path":row["path"],"mode":row["mode"],"sha":got["git_blob"],"encoding":"base64","content":base64.b64encode(b).decode("ascii")})
    records.append(dict(policyrow,git_blob=got["git_blob"],role=role))
actual={p.relative_to(ROOT/"publication-v1/selected").as_posix() for p in (ROOT/"publication-v1/selected").rglob("*") if p.is_file()}
need(actual==seen,"no extra selected file")
out=ROOT/"publication-v1/admission"
sourcepacket={"schema":"hamon.source-packet/1","source":{"repository":"Jacob-Met/TowerOps","commit":cfg["base_commit"],"tree":cfg["base_tree"]},"files":sorted(files,key=lambda r:r["path"])}
policy={"schema":"hamon.publication-layout/1","source_files":sorted(roles["source"],key=lambda r:r["path"]),"support_files":sorted(roles["support"],key=lambda r:r["path"]),"evidence_prefix":PREFIX,"descriptor_schema":peer["schema"],"descriptor_prefix":peer["prefix"]}
packetid=emit(out/"source-packet.json",sourcepacket)
policyid=emit(out/"layout-policy.json",policy)
inventoryid=emit(out/"selected-inventory.json",sorted(records,key=lambda r:r["path"]))
calls=[
[sys.executable,"-B","-S",str(ROOT/"tools/prepare_git_objects.py"),str(out/"source-packet.json"),"--sha256",packetid["sha256"],"--out",str(out/"git-object-plan.json")]]
results=[]
def run(argv,name):
    r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120)
    for k in ("stdout","stderr"):
        with (out/(name+"."+k)).open("xb") as f:f.write(getattr(r,k))
    results.append({"argv":argv,"exit_code":r.returncode,"stdout":digest(r.stdout),"stderr":digest(r.stderr)})
    need(r.returncode==0,"maintained "+name+" refused; inspect retained streams")
    return json.loads(r.stdout)
run(calls[0],"prepare")
planid=digest((out/"git-object-plan.json").read_bytes())
checked=run([sys.executable,"-B","-S",str(ROOT/"tools/validate_publication_layout.py"),str(out/"git-object-plan.json"),"--sha256",planid["sha256"],"--policy",str(out/"layout-policy.json"),"--policy-sha256",policyid["sha256"],"--descriptor",cfg["independent_descriptor"]["path"],"--descriptor-sha256",cfg["independent_descriptor"]["sha256"]],"layout")
receipt={"schema":"hamon.anvil.explorer-browser-publication-preflight.v1","accepted":True,"source_packet":packetid,"policy":policyid,"plan":planid,"inventory":inventoryid,"role_counts":{k:len(v) for k,v in roles.items()},"commands":results,"source_base":cfg["base_commit"],"source_tree":cfg["base_tree"],"scope":"Exact selected union; no Git operation, base-tree authentication or runtime replay"}
rid=emit(out/"receipt.json",receipt)
print(json.dumps({"accepted":True,"role_counts":receipt["role_counts"],"plan":planid,"receipt":rid}))
