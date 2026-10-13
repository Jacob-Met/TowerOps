import ast,datetime,hashlib,json,os,pathlib,stat,subprocess,sys
BASE=pathlib.Path("/home/jacob/hamon/receiving/anvil-d3745-towerops-install")
C=BASE/"candidate"
E=BASE/"evidence"/"author-v1"
E.mkdir()
product=["tools/install_explorer.py","tests/test_explorer_install.py","docs/EXPLORER_INSTALL.md","README.md"]
for name in product: (C/name).chmod(0o755 if name=="tools/install_explorer.py" else 0o644)
def identity(p):
 b=p.read_bytes();s=p.stat()
 return {"path":str(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"mode":oct(stat.S_IMODE(s.st_mode)),"inode":s.st_ino,"mtime_ns":s.st_mtime_ns}
def inventory():
 return [identity(p) for root in (BASE/"baseline",C) for p in sorted(root.rglob("*")) if p.is_file()]
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt={"schema":"towerops.explorer-install.author.v1","started":utc(),"pid":os.getpid(),"python":sys.version,"executable":sys.executable,"scope":"Temporary owned prefixes only; no live adoption","before":inventory(),"commands":[],"live_before":{"selector_absent":not os.path.lexists("/home/jacob/.local/bin/towerops-explorer"),"namespace_absent":not os.path.lexists("/home/jacob/.local/share/towerops")}}
for n in product[:2]:ast.parse((C/n).read_text(),filename=n)
receipt["syntax"]="ast.parse accepted both maintained Python files"
env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",TMPDIR=str(BASE/"tmp"))
for label,flags in (("normal",[]),("optimized",["-O"])):
 argv=[sys.executable,"-B",*flags,"-m","unittest","discover","-s","tests","-p","test_explorer_install.py","-v"]
 proc=subprocess.Popen(argv,cwd=C,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 out,err=proc.communicate(timeout=120)
 op=E/(label+".stdout");ep=E/(label+".stderr");op.write_bytes(out);ep.write_bytes(err)
 receipt["commands"].append({"label":label,"argv":argv,"cwd":str(C),"pid":proc.pid,"exit":proc.returncode,"stdout":identity(op),"stderr":identity(ep)})
 print(json.dumps({"label":label,"pid":proc.pid,"exit":proc.returncode,"stderr":err.decode(),"stdout":out.decode()}),flush=True)
receipt["after"]=inventory()
receipt["source_unchanged"]=receipt["before"]==receipt["after"]
receipt["live_after"]={"selector_absent":not os.path.lexists("/home/jacob/.local/bin/towerops-explorer"),"namespace_absent":not os.path.lexists("/home/jacob/.local/share/towerops")}
receipt["accepted"]=receipt["source_unchanged"] and receipt["live_before"]==receipt["live_after"] and all(x["exit"]==0 for x in receipt["commands"])
receipt["finished"]=utc()
path=E/"receipt.json";path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps({"receipt":identity(path),"accepted":receipt["accepted"],"source_files":len(receipt["before"]),"live":receipt["live_after"]}),flush=True)
sys.exit(0 if receipt["accepted"] else 1)
