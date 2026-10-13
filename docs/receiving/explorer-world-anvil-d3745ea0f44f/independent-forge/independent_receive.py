"""Independent synthetic-only receiving for frozen TowerOps explorer connector."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path("/dev/shm/anvil-d3745ea0f44f/tower-explorer-world")
OUT=Path("/dev/shm/forge-d3745/tower-review")
sys.path.insert(0,str(ROOT))
from explorer_world import extract_world
from plan_world import parse_world
from scenarios import run_scenario
def require(condition,message):
    if not condition: raise RuntimeError(message)
def run(name,*args,raw=None):
    return subprocess.run([sys.executable,"-B",str(ROOT/name),*args],input=raw,capture_output=True,env={})
def encoded(value): return json.dumps(value,separators=(",",":")).encode()
source_before=json.loads((OUT/"source-before.json").read_text())
good=run_scenario("approved")
raw=encoded(good)
receipt={"scope":"cloud Python; local synthetic fixture only; no external service or actuation","python":sys.version,"source":source_before,"courses":[]}
# Verify full original export is refused by raw-world consumer.
full=run("plan_world.py","-",raw=raw)
require(full.returncode==2 and full.stdout==b"","baseline full carrier did not refuse")
receipt["courses"].append({"case":"original complete export raw consumer refusal","exit":full.returncode,"stdout_bytes":len(full.stdout)})
# Caller-triggered corrected lookup, same process and source carrier semantics.
bad=json.loads(raw);bad["after"]["version"]+=1
rejected=run("explorer_world.py","-","--phase","before",raw=encoded(bad))
require(rejected.returncode==1 and rejected.stdout==b"","unselected mismatch leaked world")
receipt["courses"].append({"case":"unselected-world mismatch","exit":rejected.returncode,"stdout_bytes":len(rejected.stdout)})
for phase,expected in (("before","options_available"),("after","no_conflict")):
    recovered=run("explorer_world.py","-","--phase",phase,raw=raw)
    require(recovered.returncode==0 and recovered.stderr==b"","explicit healthy receiving failed")
    require(json.loads(recovered.stdout)==good[phase],"selected world changed")
    planned=run("plan_world.py","-",raw=recovered.stdout)
    require(planned.returncode==0 and planned.stderr==b"","raw consumer rejected selected world")
    payload=json.loads(planned.stdout)
    require(payload["status"]==expected and payload["proposal_only"] is True,"planner output mismatch")
    receipt["courses"].append({"case":"explicit corrected export "+phase,"exit":recovered.returncode,"planner_status":payload["status"],"world_hash":payload["world_hash"],"proposal_only":payload["proposal_only"]})
# The replay comparison permits numeric equivalence; raw-world integer admission is still authoritative.
version_float=json.loads(raw);version_float["before"]["version"]=1.0
admission=run("explorer_world.py","-","--phase","before",raw=encoded(version_float))
require(admission.returncode==2 and admission.stdout==b"","version type bypassed existing native receiving contract")
receipt["courses"].append({"case":"replay-equivalent version float still refused by raw-world admission","exit":admission.returncode,"stdout_bytes":len(admission.stdout)})
# Bytes API decodes new graphs after a refused call; subsequent mutation cannot poison later receiving.
try:extract_world(encoded(bad),"before")
except ValueError:pass
else:raise RuntimeError("API mismatch accepted")
first=extract_world(raw,"before");first["aircraft"][0]["x_nm"]=100
next_world=extract_world(raw,"before")
require(next_world==good["before"],"API recovery state contaminated")
receipt["courses"].append({"case":"same-process explicit corrected API receiving and detached result","pass":True})
# Closed downstream read-end: require controlled exit and no interpreter-shutdown noise.
readfd,writefd=os.pipe();os.close(readfd)
with os.fdopen(writefd,"wb",buffering=0) as sink:
    broken=subprocess.run([sys.executable,"-B",str(ROOT/"explorer_world.py"),"-","--phase","before"],input=raw,stdout=sink,stderr=subprocess.PIPE,env={})
require(broken.returncode==2 and b"cannot write world" in broken.stderr and b"Exception ignored" not in broken.stderr,"closed downstream lifecycle not controlled")
receipt["courses"].append({"case":"closed downstream read-end","exit":broken.returncode,"stderr":broken.stderr.decode()})
# All reviewed source preserved.
for item in source_before:
    require(hashlib.sha256((ROOT/item["path"]).read_bytes()).hexdigest()==item["sha256"],"source changed "+item["path"])
receipt["source_unchanged"]=True
(OUT/"independent-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"courses":len(receipt["courses"]),"all_pass":True,"source_unchanged":True}))
