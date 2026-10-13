import sys,json,pathlib,hashlib,os,stat,datetime
d=json.loads(sys.argv[1])
base=pathlib.Path("/home/jacob/hamon/receiving/anvil-d3745-towerops-install")
donor=pathlib.Path("/home/jacob/hamon/receiving/anvil-d3745-browser-explain-publication/publication-v1/selected/docs/qualification/explorer-browser-explain-root-d3745/independent/candidate-source")
blob=lambda b:hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
bodies={}
rows=[]
for r in d["runtime"]:
 p=donor/r["repository_path"];b=p.read_bytes();s=p.stat()
 assert len(b)==r["bytes"] and hashlib.sha256(b).hexdigest()==r["received_sha256"] and blob(b)==r["git_blob"]
 bodies[r["repository_path"]]=b
 rows.append({**r,"source_path":str(p),"native_mode":oct(stat.S_IMODE(s.st_mode))})
rb=d["readme"].encode();assert blob(rb)==d["readme_git"]
base.mkdir()
for name in ("baseline","candidate","evidence","tmp"):
 (base/name).mkdir()
support=base/"candidate/docs/qualification/explorer-install-anvil-d3745/accepted-source";support.mkdir(parents=True)
for r in rows:
 for root in (base/"baseline",support):
  p=root/r["repository_path"];p.parent.mkdir(parents=True,exist_ok=True)
  with p.open("xb") as f:f.write(bodies[r["repository_path"]])
  p.chmod(0o755 if r["git_mode"]=="100755" else 0o644)
for root in (base/"baseline",base/"candidate"):
 (root/"README.md").write_bytes(rb);(root/"README.md").chmod(0o644)
for n in ("tools","tests"): (base/"candidate"/n).mkdir()
receipt={"schema":"hamon.anvil.explorer-install-staging.v1","created":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":d["source_commit"],"base_commit":d["base_commit"],"source_files":rows,"readme":{"bytes":len(rb),"sha256":hashlib.sha256(rb).hexdigest(),"git_blob":blob(rb)},"scope":"Exact accepted runtime copy only; no installer source or live installation created; donor unchanged."}
for r in rows:assert (donor/r["repository_path"]).read_bytes()==bodies[r["repository_path"]]
out=base/"evidence/staging.json";out.write_text(json.dumps(receipt,indent=2)+"\n")
raw=out.read_bytes();print(json.dumps({"stage":str(base),"source_files":len(rows),"receipt_bytes":len(raw),"receipt_sha256":hashlib.sha256(raw).hexdigest()}))
