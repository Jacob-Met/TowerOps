"""Run existing capture predicates with output isolated from frozen source."""
import hashlib,json,sys
from pathlib import Path
source=Path(sys.argv[1]).resolve();chrome=sys.argv[2];output=Path(sys.argv[3]).resolve()
entry=source/"tools/capture_airspace.py";raw=entry.read_text()
old="out=ROOT/'web/airspace/public/captures';out.mkdir(parents=True,exist_ok=True)"
assert raw.count(old)==1
changed=raw.replace(old,"out=Path("+repr(str(output))+");out.mkdir(parents=True,exist_ok=True)")
print(json.dumps({"entry":str(entry),"entry_sha256":hashlib.sha256(entry.read_bytes()).hexdigest(),"override":"capture output directory only; browser predicates unchanged","output":str(output)}),flush=True)
sys.argv=[str(entry),"--chrome",chrome]
exec(compile(changed,str(entry),"exec"),{"__name__":"__main__","__file__":str(entry)})
