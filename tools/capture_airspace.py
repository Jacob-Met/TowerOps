import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(ROOT/'web/airspace/dist'),**k)
 def log_message(self,*a):pass
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--chrome',default=r'C:\Program Files\Google\Chrome\Application\chrome.exe');args=ap.parse_args()
 out=ROOT/'web/airspace/public/captures';out.mkdir(parents=True,exist_ok=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),Quiet);Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_address[1]}/'
 try:
  assert urlopen(url,timeout=5).status==200;errors=[];bad=[]
  with sync_playwright() as pw:
   kw={'headless':True,'args':['--disable-gpu']}
   if args.chrome:kw['executable_path']=args.chrome
   browser=pw.chromium.launch(**kw);ctx=browser.new_context(viewport={'width':1440,'height':1000})
   page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None);page.on('response',lambda r:bad.append((r.status,r.url)) if r.status>=400 else None)
   page.goto(url,wait_until='networkidle');assert page.locator('#pair-count').inner_text()=='1'
   page.locator('#run-planner').click();page.wait_for_function("document.querySelector('#proposal-state').textContent==='PROPOSAL READY'",timeout=90000);assert 'TWR419' in page.locator('#proposal-output').inner_text()
   page.locator('#approve').click();page.locator('#readback').click();page.wait_for_function("document.querySelector('#world-title').textContent.includes('No projected conflict')")
   assert 'VALID' in page.locator('#audit-status').text_content();assert [page.locator(f'#{x} i').inner_text() for x in ('gate-screen','gate-approval','gate-ack')]==['PASS','APPROVED','ACCEPTED'];desktop=page.locator('#world-title').inner_text();page.screenshot(path=str(out/'airspace-desktop.png'),full_page=True)
   page.evaluate("document.querySelectorAll('details.depth').forEach(d=>d.open=true)");page.locator('#flight-id').fill('VISIT1');page.locator('#flight-x').fill('11');page.locator('#flight-y').fill('9');page.locator('#flight-level').fill('110');page.locator('#flight-bearing').fill('270');page.locator('#flight-speed').fill('150');page.locator('#add-custom-flight').click()
   user_flight='VISIT1' in page.locator('#flight-list').inner_text();assert user_flight and page.locator('#flight-count').inner_text()=='3 FLIGHTS'
   page.locator('.policy-editor summary').click();page.locator('#policy-horizontal').evaluate("(e)=>{e.value='6.5';e.dispatchEvent(new Event('input',{bubbles:true}));}");policy_label=page.locator('#horizontal-value').inner_text();slider_value=page.locator('#policy-horizontal').input_value();assert policy_label=='6.5 NM',f'policy label {policy_label!r}; range value {slider_value!r}'
   page.locator('#policy-horizontal').evaluate("(e)=>{e.value='5';e.dispatchEvent(new Event('input',{bubbles:true}));}")
   page.locator('#export-world').click();world=json.loads(page.locator('#world-json').input_value());visit=next(a for a in world['aircraft'] if a['aircraft_id']=='VISIT1');visit['altitude_ft']=11500;world['version']+=1
   page.locator('#world-json').fill(json.dumps(world));page.locator('#load-world').click();assert '115 FL' in page.locator('#flight-list').inner_text()
   page.locator('#add-traffic').click();flights=page.locator('#flight-count').inner_text();pairs=page.locator('#pair-count').inner_text();assert flights=='4 FLIGHTS' and int(pairs)>0
   page.locator('#perturb-track').click();assert 'TWR820' in page.locator('#flight-list').inner_text()
   mobile=ctx.new_page();mobile.set_viewport_size({'width':390,'height':844});mobile.goto(url,wait_until='networkidle');assert mobile.locator('#pair-count').inner_text()=='1'
   overflow=mobile.evaluate('document.documentElement.scrollWidth>window.innerWidth');assert not overflow,'mobile horizontal overflow';mobile.screenshot(path=str(out/'airspace-mobile.png'),full_page=True)
   print(json.dumps({'desktop_after_apply':desktop,'visitor_flight_loaded':user_flight,'policy_tuned':'6.5 NM','imported_altitude':'115 FL','post_add_pairs':pairs,'flights':flights,'mobile_overflow':overflow,'console_errors':errors,'http_errors':bad,'captures':[(f.name,f.stat().st_size) for f in out.glob('*.png')]}));browser.close()
  assert not errors,errors;assert not bad,bad
 finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
