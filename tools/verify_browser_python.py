"""Exercise deployed worker against the actual native Python oracle."""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from generate_airspace_reference import CASES, result
from playwright.sync_api import sync_playwright

from towerops import SafetyPolicy

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(ROOT/'web/airspace/dist'),**k)
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Quiet);Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_address[1]}/'
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page();page.goto(url)
  worker=next((ROOT/'web/airspace/dist/assets').glob('python-worker-*.js')).name
  page.evaluate("name=>{window.pyWorker=new Worker('./assets/'+name,{type:'module'});window.pyCall=request=>new Promise((resolve,reject)=>{pyWorker.onmessage=e=>e.data.error?reject(Error(e.data.error)):resolve(e.data.result);pyWorker.postMessage({id:1,base:location.href,request});});}",worker)
  policy=SafetyPolicy();count=0
  for name,state in CASES:
   expected=result(name,state,policy);now=expected['now'];s=expected['state']
   q={'op':'plan','state':s,'policy':__import__('dataclasses').asdict(policy),'now':now}
   actual=page.evaluate('q=>pyCall(q)',q)
   a=actual['advisory'];wanted=expected['advisory']
   assert a==dict(wanted,advisory_hash=expected['advisory_hash']) if wanted else a is None
   if a:
    approval={'advisory_hash':a['advisory_hash'],'decision':'approve','approved_at':now+0.2,'approver':'synthetic-controller'}
    ack={'advisory_hash':a['advisory_hash'],'status':'accepted','acknowledged_at':now+0.4}
    apply={**q,'op':'apply','advisory':a,'approval':approval,'ack':ack,'now':now+0.5,'audit_json':'[]'}
    after=page.evaluate('q=>pyCall(q)',apply)
    assert after['state']==expected['after_state'] and after['events']==expected['audit_events'] and after['valid']
    repeated=page.evaluate('q=>pyCall(q)',{**apply,'audit_json':after['audit_json']})
    assert repeated['valid'] and len(repeated['events'])==8
    denied=page.evaluate('q=>pyCall(q)',{**apply,'ack':None})
    assert denied['error']=='ack_missing'
    denied=page.evaluate('q=>pyCall(q)',{**apply,'approval':None})
    assert denied['error']=='human_approval_required'
   count+=1
  # Source failure must not use a TypeScript/mock fallback.
  failed=browser.new_page();failed.route('**/python/towerops.py',lambda route:route.abort());failed.goto(url);failed.locator('#run-planner').click();failed.wait_for_function("document.querySelector('#proposal-output').textContent.includes('Python unavailable')",timeout=90000)
  assert failed.locator('#approve').is_disabled() and failed.locator('#pair-count').text_content()=='1'
  print(json.dumps({'native_python_cases':count,'planner_gate_audit_parity':True,'missing_approval_and_ack_rejected':True,'source_load_failure_closed':True}))
  browser.close()
finally:server.shutdown();server.server_close()
