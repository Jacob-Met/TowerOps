"use strict";
const fs=require("fs"),path=require("path"),http=require("http"),crypto=require("crypto"),assert=require("assert/strict"),{spawn}=require("child_process"),{isDeepStrictEqual:equal}=require("util");
const [specPath,out,variant]=process.argv.slice(2);
assert(specPath&&out&&path.isAbsolute(specPath)&&path.isAbsolute(out)&&["original","candidate"].includes(variant),"SPEC ABSENT_OUT original|candidate required");
const sha=b=>crypto.createHash("sha256").update(b).digest("hex");
const ident=p=>{const s=fs.lstatSync(p);assert(s.isFile()&&!s.isSymbolicLink());const b=fs.readFileSync(p);return {path:p,bytes:b.length,sha256:sha(b),mode:"0o"+(s.mode&511).toString(8)};};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error("Timed out: "+label);}
async function bounded(p,ms,label){let t;try{return await Promise.race([p,new Promise((_,j)=>t=setTimeout(()=>j(Error(label)),ms))]);}finally{clearTimeout(t);}}
function readHTTP(port,method,url,body,headers={}){
 return new Promise((resolve,reject)=>{const b=body===undefined?null:Buffer.from(body);const req=http.request({host:"127.0.0.1",port,path:url,method,headers:{Host:"127.0.0.1:"+port,...(b?{"Content-Type":"application/json","Content-Length":b.length}:{}),...headers},timeout:12000},res=>{const chunks=[];res.on("data",b=>chunks.push(b));res.on("end",()=>resolve({status:res.statusCode,headers:res.headers,body:Buffer.concat(chunks)}));res.on("error",reject);});req.on("error",reject);req.on("timeout",()=>req.destroy(Error("HTTP timeout")));if(b)req.write(b);req.end();});
}
(async()=>{
 const base=__dirname,criteriaPath=path.join(base,"criteria.json"),freezePath=path.join(base,"driver-freeze-v2.json");
 const criteria=JSON.parse(fs.readFileSync(criteriaPath)),freeze=JSON.parse(fs.readFileSync(freezePath)),spec=JSON.parse(fs.readFileSync(specPath));
 assert.equal(sha(fs.readFileSync(__filename)),freeze.receiver.sha256);assert.equal(sha(fs.readFileSync(criteriaPath)),freeze.criteria.sha256);
 assert.equal(spec.variant,variant);assert.equal(spec.files.length,8);assert.deepEqual(spec.files.map(x=>x.path).sort(),criteria.source_boundary.slice().sort());
 const sourceBefore=spec.files.map(r=>{const i=ident(r.source_path);assert.equal(i.bytes,r.bytes);assert.equal(i.sha256,r.sha256);assert.equal(i.mode,r.mode);return i;});
 const source=new Map(spec.files.map(r=>[r.path,r.source_path]));
 const controlsBefore=[__filename,criteriaPath,freezePath,path.join(base,"criteria-freeze.json"),specPath].map(ident);
 const fixtures=Object.fromEntries(["A","B","C","D"].map(n=>[n,path.join(base,"fixtures",n+".json")]));
 const fixtureBefore=Object.values(fixtures).map(ident),values=Object.fromEntries(Object.entries(fixtures).map(([k,p])=>[k,JSON.parse(fs.readFileSync(p))]));
 for(const r of freeze.fixtures){const i=ident(r.path);assert.equal(i.sha256,r.sha256);assert.equal(i.bytes,r.bytes);assert.equal(i.mode,r.mode);}
 fs.mkdirSync(out);fs.mkdirSync(path.join(out,"streams"));fs.mkdirSync(path.join(out,"tmp"));fs.mkdirSync(path.join(out,"cache"));
 const receipt={schema:"hamon.loom.towerops-explain-browser.v2",variant,started:new Date().toISOString(),source_spec:spec,source_before:sourceBefore,controls_before:controlsBefore,fixtures_before:fixtureBefore,checks:[],http:[],request_finished:[],page_errors:[],failed_requests:[],external_requests:[],inline_requests:[],screenshots:[],error:null};
 const check=(id,actual,expected)=>{const pass=equal(actual,expected);receipt.checks.push({id,actual,expected,pass});return pass;};
 const need=(id,actual,expected)=>{assert(check(id,actual,expected),id);};
 let backend,browser,relay,releaseHeld=null,backendStdout="",backendStderr="",backendDone=false,relayClosed=false,backendPort,relayError=null;
 const sockets=new Set();let failureArmed=false,holdArmed=false,heldReady=false,sequence=0;
 const env={...process.env};for(const k of Object.keys(env))if(k.startsWith("PYTHON"))delete env[k];env.PYTHONDONTWRITEBYTECODE="1";env.TMPDIR=path.join(out,"tmp");env.XDG_CACHE_HOME=path.join(out,"cache");
 const save=(name,body)=>{const p=path.join(out,"streams",name);fs.writeFileSync(p,body,{flag:"wx"});return ident(p);};
 const ordinary=matches=>({matches,audit_valid:values.A.audit_valid,outcome:values.A.outcome,rejection_reason:values.A.rejection_reason,expected_audit_head:values.A.audit_head,note:"Local deterministic reproduction only; not a signature, provenance proof, or authority."});
 const expectedExplain=n=>({...ordinary(false),difference_limit:32,differences:criteria.expected_differences[n],differences_truncated:n==="D"});
 const responseRows=()=>receipt.http.filter(r=>r.method==="POST"&&r.path==="/api/replay/explain");
 const postRows=()=>receipt.http.filter(r=>r.method==="POST");
 try{
  backend=spawn(spec.python,["-B",source.get("explorer.py"),"serve","--port","0"],{cwd:path.dirname(source.get("explorer.py")),env,stdio:["ignore","pipe","pipe"]});
  receipt.backend_pid=backend.pid;receipt.backend_command=[spec.python,"-B",source.get("explorer.py"),"serve","--port","0"];
  backend.stdout.on("data",b=>backendStdout+=b);backend.stderr.on("data",b=>backendStderr+=b);backend.on("exit",(code,signal)=>{backendDone=true;receipt.backend_exit={code,signal};});
  backend.on("error",e=>{receipt.backend_spawn_error=String(e);backendDone=true;});
  await until(()=>/http:\/\/127\.0\.0\.1:(\d+)/.test(backendStdout)||backendDone,"Python server startup");assert(!backendDone,"backend terminated during startup");
  backendPort=Number(backendStdout.match(/http:\/\/127\.0\.0\.1:(\d+)/)[1]);receipt.backend_origin="http://127.0.0.1:"+backendPort;
  relay=http.createServer(async(req,res)=>{
   let row;
   try{
    const chunks=[];for await(const b of req)chunks.push(b);const body=Buffer.concat(chunks);const id=++sequence;
    row={id,method:req.method,path:req.url,request_body:body.toString("utf8"),request_json:body.length?JSON.parse(body):null};
    receipt.http.push(row);
    const headers={};if(req.headers.origin)headers.Origin="http://127.0.0.1:"+backendPort;
    const reply=await readHTTP(backendPort,req.method,req.url,body.length?body:undefined,headers);
    row.backend_status=reply.status;row.backend_body=reply.body.toString("utf8");row.backend_sha256=sha(reply.body);row.backend_bytes=reply.body.length;
    row.backend_stream=save(String(id).padStart(3,"0")+"-backend.body",reply.body);
    if(req.method==="POST")row.request_stream=save(String(id).padStart(3,"0")+"-request.json",body);
    let outBody=reply.body,status=reply.status,label="http-"+id;
    const explain=req.method==="POST"&&req.url==="/api/replay/explain";
    if(explain&&failureArmed){failureArmed=false;row.authored_fault="One relay HTTP503 after capturing the unchanged production backend response";outBody=Buffer.from(JSON.stringify({error:"Loom authored explanation transport failure; retry this file."}));status=503;}
    row.delivered_status=status;row.delivered_body=outBody.toString("utf8");row.delivered_sha256=sha(outBody);row.response_label=label;
    const sentHeaders={...reply.headers,"content-length":outBody.length,"cache-control":"no-store","x-loom-response":label};delete sentHeaders.connection;delete sentHeaders["transfer-encoding"];
    res.writeHead(status,sentHeaders);
    if(explain&&holdArmed){holdArmed=false;assert.equal(releaseHeld,null);row.authored_delay="Production headers and first response byte flushed; remainder held";res.flushHeaders();res.write(outBody.subarray(0,1));receipt.held_response_label=label;heldReady=true;releaseHeld=()=>{res.end(outBody.subarray(1));releaseHeld=null;};}
    else res.end(outBody);
   }catch(e){relayError=String(e.stack||e);if(row)row.error=relayError;if(!res.headersSent)res.writeHead(500,{"Content-Type":"application/json"});res.end(JSON.stringify({error:"Receiver relay failure"}));}
  });
  relay.on("connection",s=>{sockets.add(s);s.on("close",()=>sockets.delete(s));});
  await new Promise((resolve,reject)=>{relay.once("error",reject);relay.listen(0,"127.0.0.1",resolve);});
  const origin="http://127.0.0.1:"+relay.address().port;receipt.origin=origin;
  const puppeteer=require(spec.browser_module);
  browser=await puppeteer.launch({browser:"firefox",executablePath:spec.browser_executable,headless:true,userDataDir:path.join(out,"profile"),timeout:25000,env});
  receipt.browser_pid=browser.process()?.pid;receipt.browser_version=await browser.version();
  const page=await browser.newPage();await page.setViewport({width:1440,height:1100});
  page.on("pageerror",e=>receipt.page_errors.push(String(e)));
  page.on("request",r=>{const u=new URL(r.url());if(u.protocol==="data:")receipt.inline_requests.push(r.url());else if(u.origin!==origin)receipt.external_requests.push(r.url());});
  page.on("requestfailed",r=>receipt.failed_requests.push({url:r.url(),error:r.failure()}));
  page.on("requestfinished",r=>{const l=r.response()?.headers()["x-loom-response"];if(l)receipt.request_finished.push({label:l,url:r.url(),at:Date.now()});});
  await page.goto(origin+"/",{waitUntil:"networkidle0",timeout:20000});
  await page.waitForFunction(()=>document.querySelector("#status").textContent.startsWith("Ready."),{timeout:10000});
  await page.select("#scenario","approved");await page.click("#run");
  await page.waitForFunction(()=>!document.querySelector("#result").hidden&&!document.querySelector("#run").disabled,{timeout:10000});
  const display=()=>page.evaluate(()=>({result:document.querySelector("#result").innerHTML,status:document.querySelector("#status").textContent,export_disabled:document.querySelector("#export").disabled}));
  receipt.display_before=await display();
  need("production.run-export",JSON.parse(postRows().find(r=>r.path==="/api/run").backend_body),values.A);
  const replayStatus=()=>page.$eval("#replay-status",e=>e.textContent);
  // A passive listener runs after the application's synchronous change handler,
  // before its first file.text await resumes; this records the promised immediate retirement.
  await page.evaluate(()=>{
   window.__loomImmediateSelections=[];
   document.getElementById("replay-file").addEventListener("change",()=>{
    const e=id=>document.getElementById(id),visible=x=>!!x&&!x.hidden&&getComputedStyle(x).display!=="none"&&x.getClientRects().length>0;
    const b=e("replay-explain"),d=e("replay-differences"),s=e("replay-explain-status"),l=e("replay-difference-list");
    window.__loomImmediateSelections.push({button_available:visible(b)&&!b.disabled,status:s?.textContent??null,details_visible:visible(d),details_open:d?.open??null,list_count:l?.children.length??null});
   });
  });
  const input=await page.$("#replay-file");
  const select=async n=>{await input.uploadFile(fixtures[n]);await page.waitForFunction(()=>/^Replay (MATCH|MISMATCH):/.test(document.querySelector("#replay-status").textContent),{timeout:10000});const r=postRows().filter(r=>r.path==="/api/replay").at(-1);need("ordinary."+n+"."+r.id+".body",r.request_json,values[n]);need("ordinary."+n+"."+r.id+".reply",JSON.parse(r.backend_body),ordinary(n==="A"));return r;};
  const shot=async name=>{const p=path.join(out,name+".png");await page.screenshot({path:p,fullPage:false});receipt.screenshots.push(ident(p));};
  const widget=()=>page.evaluate(()=>{
   const el=id=>document.getElementById(id),visible=e=>!!e&&!e.hidden&&getComputedStyle(e).display!=="none"&&getComputedStyle(e).visibility!=="hidden"&&e.getClientRects().length>0;
   const button=el("replay-explain"),details=el("replay-differences"),status=el("replay-explain-status"),limit=el("replay-difference-limit"),list=el("replay-difference-list");
   return {button_exists:!!button,button_available:visible(button)&&!button.disabled,button_disabled:button?.disabled??null,status:status?.textContent??null,status_role:status?.getAttribute("role")??null,details_visible:visible(details),details_open:details?.open??null,list_count:list?.children.length??null,limit_visible:visible(limit),limit_text:limit?.textContent??null,rows:list?Array.from(list.children).map(li=>({path:li.querySelector("code.replay-path")?.textContent,kind:li.querySelector("code.replay-kind")?.textContent,expected_text:li.querySelector("pre.replay-expected")?.textContent,actual_text:li.querySelector("pre.replay-actual")?.textContent,text:li.textContent})):[],injected_elements:document.querySelectorAll("[data-loom-literal]").length};
  });
  const retired=w=>({button_available:w.button_available,status:w.status,details_visible:w.details_visible,details_open:w.details_open,list_count:w.list_count});
  const retiredExpected={button_available:false,status:"",details_visible:false,details_open:false,list_count:0};
  const validateReport=async(n,label)=>{
   await page.waitForFunction(()=>{const d=document.getElementById("replay-differences");return d&&!d.hidden&&d.open&&document.querySelector("#replay-difference-list").children.length>0;},{timeout:10000});
   const w=await widget(),r=responseRows().at(-1);need(label+".production-status",r.backend_status,200);need(label+".whole-production-reply",JSON.parse(r.backend_body),expectedExplain(n));
   need(label+".exact-delivery",r.delivered_body,r.backend_body);need(label+".request",r.request_json,values[n]);
   need(label+".rows",w.rows.map(x=>({path:x.path,kind:x.kind,expected:JSON.parse(x.expected_text),actual:JSON.parse(x.actual_text)})),criteria.expected_differences[n]);
   need(label+".full-json-format",w.rows.every((x,i)=>x.expected_text===JSON.stringify(criteria.expected_differences[n][i].expected,null,2)&&x.actual_text===JSON.stringify(criteria.expected_differences[n][i].actual,null,2)),true);
   need(label+".side-labels",w.rows.every(x=>x.text.includes("Expected (local reproduction)")&&x.text.includes("Actual (saved export)")),true);
   need(label+".open",w.details_visible&&w.details_open,true);need(label+".literal-only",w.injected_elements,0);
   need(label+".status-role",w.status_role,"status");
   need(label+".verdict-preserved",(await replayStatus()).startsWith("Replay MISMATCH:"),true);
   return w;
  };
  await select("B");
  need("ordinary.no-auto-explanation",responseRows().length,0);
  if(variant==="original"){
   need("original.action-absent",await page.$("#replay-explain"),null);
   const r=await readHTTP(relay.address().port,"POST","/api/replay/explain",JSON.stringify(values.B),{Origin:origin});
   need("original.endpoint-absent",r.status,404);receipt.original_endpoint_reply=r.body.toString("utf8");
   await shot("original-mismatch-no-action");
   need("original.post-paths",postRows().map(r=>r.path),["/api/run","/api/replay","/api/replay/explain"]);
  }else{
   need("B.action-available",(await widget()).button_available,true);await page.click("#replay-explain");await validateReport("B","B");
   const beforeToggle=responseRows().length;await page.click("#replay-difference-summary");need("B.user-collapsed",(await widget()).details_open,false);
   await page.click("#replay-difference-summary");need("B.user-expanded",(await widget()).details_open,true);need("B.toggle-no-request",responseRows().length,beforeToggle);await shot("B-one-field");
   await input.uploadFile(fixtures.C);need("C.selection-retires",await page.evaluate(()=>window.__loomImmediateSelections.at(-1)),retiredExpected);
   await page.waitForFunction(()=>document.querySelector("#replay-status").textContent.startsWith("Replay MISMATCH:"),{timeout:10000});
   failureArmed=true;await page.click("#replay-explain");await page.waitForFunction(()=>{const e=document.getElementById("replay-explain-status");return e.textContent.includes("Loom authored explanation transport failure");},{timeout:10000});
   const failed=responseRows().at(-1);need("C.failure-authored-only",failed.delivered_status,503);need("C.failure-production-valid",JSON.parse(failed.backend_body),expectedExplain("C"));
   need("C.failure-explicit-retry",(await widget()).button_available,true);need("C.failure-verdict-kept",(await replayStatus()).startsWith("Replay MISMATCH:"),true);need("C.failure-display-kept",await display(),receipt.display_before);
   await page.click("#replay-explain");await validateReport("C","C.retry");await shot("C-literal-typed-and-missing");
   await select("D");await page.click("#replay-explain");const dw=await validateReport("D","D");
   need("D.truncation-visible",dw.limit_visible&&dw.limit_text.trim().length>0,true);need("D.exact-limit",dw.list_count,32);receipt.truncation_notice=dw.limit_text;await shot("D-limited-differences");
   await select("B");holdArmed=true;await page.click("#replay-explain");await until(()=>heldReady,"held production explanation body");
   need("stale.pending-disabled",(await widget()).button_disabled,true);
   await input.uploadFile(fixtures.A);need("stale.new-selection-retires",await page.evaluate(()=>window.__loomImmediateSelections.at(-1)),retiredExpected);
   await page.waitForFunction(()=>document.querySelector("#replay-status").textContent.startsWith("Replay MATCH:"),{timeout:10000});
   assert(releaseHeld);releaseHeld();await until(()=>receipt.request_finished.some(x=>x.label===receipt.held_response_label),"held response public requestfinished");
   await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await delay(150);
   need("stale.completed-once",receipt.request_finished.filter(x=>x.label===receipt.held_response_label).length,1);
   need("stale.completed-keeps-retired",retired(await widget()),retiredExpected);need("stale.MATCH-kept",(await replayStatus()).startsWith("Replay MATCH:"),true);await shot("A-match-after-old-explanation");
   await select("B");await page.click("#replay-explain");await validateReport("B","B.before-clear");
   await input.evaluate(el=>{el.value="";el.dispatchEvent(new Event("change",{bubbles:true}));});
   need("clear.input-empty",await input.evaluate(el=>el.files.length),0);need("clear.widget-retired",retired(await widget()),retiredExpected);need("clear.verdict-empty",await replayStatus(),"");
   need("candidate.post-paths",postRows().map(r=>r.path),["/api/run","/api/replay","/api/replay/explain","/api/replay","/api/replay/explain","/api/replay/explain","/api/replay","/api/replay/explain","/api/replay","/api/replay/explain","/api/replay","/api/replay","/api/replay/explain"]);
   const reqNames=["B","C","C","D","B","B"];need("candidate.explanation-exact-captured-inputs",responseRows().map(r=>r.request_json),reqNames.map(n=>values[n]));
   need("candidate.exact-ordinary-captured-inputs",postRows().filter(r=>r.path==="/api/replay").map(r=>r.request_json),["B","C","D","B","A","B"].map(n=>values[n]));
  }
  receipt.display_after=await display();need("display.unchanged",receipt.display_after,receipt.display_before);
  need("network.no-external",receipt.external_requests,[]);need("browser.no-page-errors",receipt.page_errors,[]);need("network.no-failed",receipt.failed_requests,[]);
  need("relay.no-error",relayError,null);await page.close();
 }catch(e){receipt.error=String(e.stack||e);}
 finally{
  try{if(releaseHeld)releaseHeld();if(browser){const p=browser.process();await bounded(browser.close(),15000,"browser close");receipt.browser_closed=true;receipt.browser_exit_code=p?.exitCode;}}catch(e){receipt.browser_close_error=String(e);}
  try{if(relay){relay.closeIdleConnections();await bounded(new Promise(r=>relay.close(r)),10000,"relay close");await until(()=>sockets.size===0,"relay socket close events",2000);relayClosed=true;}receipt.relay_closed=relayClosed;receipt.open_relay_sockets=sockets.size;}catch(e){receipt.relay_close_error=String(e);for(const s of sockets)s.destroy();}
  try{if(backend&&!backendDone){backend.kill("SIGINT");await until(()=>backendDone,"backend graceful close",7000);}receipt.backend_closed=backendDone;}catch(e){receipt.backend_close_error=String(e);backend?.kill("SIGTERM");}
  receipt.backend_stdout=save("backend.stdout",backendStdout);receipt.backend_stderr=save("backend.stderr",backendStderr);
  try{receipt.source_after=sourceBefore.map(r=>ident(r.path));check("source.preserved",receipt.source_after,sourceBefore);receipt.controls_after=controlsBefore.map(r=>ident(r.path));check("controls.preserved",receipt.controls_after,controlsBefore);receipt.fixtures_after=fixtureBefore.map(r=>ident(r.path));check("fixtures.preserved",receipt.fixtures_after,fixtureBefore);}catch(e){receipt.preservation_error=String(e);}
  receipt.failed_checks=receipt.checks.filter(x=>!x.pass).map(x=>x.id);
  receipt.accepted=!receipt.error&&!receipt.preservation_error&&!receipt.browser_close_error&&!receipt.relay_close_error&&!receipt.backend_close_error&&receipt.browser_closed===true&&relayClosed&&receipt.open_relay_sockets===0&&backendDone&&receipt.backend_exit?.code===0&&receipt.browser_exit_code===0&&receipt.failed_checks.length===0;
  receipt.finished=new Date().toISOString();fs.writeFileSync(path.join(out,"receipt.json"),JSON.stringify(receipt,null,2)+"\n",{flag:"wx"});
  console.log(JSON.stringify({accepted:receipt.accepted,variant,checks:receipt.checks.length,failed_checks:receipt.failed_checks,http:receipt.http.length,posts:receipt.http.filter(x=>x.method==="POST").length,screenshots:receipt.screenshots.length,error:receipt.error,browser_closed:receipt.browser_closed,backend_exit:receipt.backend_exit,relay_closed:receipt.relay_closed,open_relay_sockets:receipt.open_relay_sockets,out}));
  if(!receipt.accepted)process.exitCode=1;
 }
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
