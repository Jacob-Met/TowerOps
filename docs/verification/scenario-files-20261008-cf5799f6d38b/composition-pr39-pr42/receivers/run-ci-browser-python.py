"""Run the unchanged CI worker oracle with the installed Chrome executable."""
import hashlib, json, runpy, sys
from pathlib import Path
from playwright.sync_api import BrowserType
source=Path(sys.argv[1]).resolve()
chrome=sys.argv[2]
entry=source/"tools/verify_browser_python.py"
launch=BrowserType.launch
def installed_launch(self,*args,**kwargs):
    kwargs.setdefault("executable_path",chrome)
    return launch(self,*args,**kwargs)
BrowserType.launch=installed_launch
sys.path[:0]=[str(source),str(source/"tools")]
print(json.dumps({"entry":str(entry),"entry_sha256":hashlib.sha256(entry.read_bytes()).hexdigest(),"browser_executable":chrome,"override":"installed browser executable only; original oracle predicates unchanged"}),flush=True)
runpy.run_path(str(entry),run_name="__main__")
