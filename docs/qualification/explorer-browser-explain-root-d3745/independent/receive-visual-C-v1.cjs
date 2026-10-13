"use strict";
const fs=require("fs"),path=require("path"),crypto=require("crypto"),assert=require("assert/strict"),{spawn}=require("child_process"),{isDeepStrictEqual:equal}=require("util");
const base=__dirname,out=path.join(base,"visual-C-v1"),specPath=path.join(base,"candidate-spec-v1.json"),spec=JSON.parse(fs.readFileSync(specPath)),criteria=JSON.parse(fs.readFileSync(path.join(base,"criteria.json")));
const sha=b=>crypto.createHash("sha256").update(b).digest("hex");
const ident=p=>{const s=fs.lstatSync(p);assert(s.isFile()&&!s.isSymbolicLink());const b=fs.readFileSync(p);return {path:p,bytes:b.length,sha256:sha(b),mode:"0o"+(s.mode&511).toString(8)};};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(f,label,ms=12000){const end=Date.now()+ms;while(Date.now()<end){if(await f())return;await wait(25);}throw Error("Timeout "+label);}
(async()=>{
 const freeze=JSON.parse(fs.readFileSync(path.join(base,"visual-freeze-v1.json")));assert.equal(sha(fs.readFileSync(__filename)),freeze.receiver.sha256);
 const inputs=[...spec.files.map(r=>r.source_path),specPath,path.join(base,"criteria.json"),path.join(base,"fixtures/C.json"),__filename,path.join(base,"visual-freeze-v1.json")].map(ident);
 for(const row of spec.files){const i=ident(row.source_path);assert.equal(i.sha256,row.sha256);assert.equal(i.bytes,row.bytes);assert.equal(i.mode,row.mode);}
 const expected=criteria.expected_differences.C,fixture=path.join(base,"fixtures/C.json");fs.mkdirSync(out);fs.mkdirSync(path.join(out,"tmp"));fs.mkdirSync(path.join(out,"cache"));
 const r={schema:"hamon.loom.towerops-explain-visual-C.v1",started:new Date().toISOString(),scope:"Separate post-exposure direct-production visual opening of saved C after the closed85-check course; no original control or race/retry replay.",inputs_before:inputs,requests:[],responses:[],page_errors:[],failed_requests:[],external_requests:[],inline_requests:[],screenshots:[],checks:[],error:null};
 const check=(id,a,e)=>{const pass=equal(a,e);r.checks.push({id,actual:a,expected:e,pass});assert(pass,id);};
 const env={...process.env,PYTHONDONTWRITEBYTECODE:"1",TMPDIR:path.join(out,"tmp"),XDG_CACHE_HOME:path.join(out,"cache")};delete env.PYTHONPATH;delete env.PYTHONHOME;
 let backend,browser,stdout="",stderr="",done=false;const tasks=[];
 try{
  backend=spawn(spec.python,["-B",path.join(base,"candidate-source/explorer.py"),"serve","--port","0"],{env,stdio:["ignore","pipe","pipe"],cwd:path.join(base,"candidate-source")});r.backend_pid=backend.pid;
  backend.stdout.on("data",b=>stdout+=b);backend.stderr.on("data",b=>stderr+=b);backend.on("exit",(code,signal)=>{done=true;r.backend_exit={code,signal};});backend.on("error",e=>{done=true;r.backend_spawn_error=String(e);});
  await until(()=>stdout.includes("http://127.0.0.1:")||done,"server startup");assert(!done);const origin=stdout.match(/http:\/\/127\.0\.0\.1:\d+/)[0];r.origin=origin;
  const puppeteer=require(spec.browser_module);browser=await puppeteer.launch({browser:"firefox",executablePath:spec.browser_executable,headless:true,userDataDir:path.join(out,"profile"),env,timeout:20000});r.browser_pid=browser.process()?.pid;r.browser_version=await browser.version();
  const page=await browser.newPage();await page.setViewport({width:1440,height:1100});
  page.on("pageerror",e=>r.page_errors.push(String(e)));
  page.on("request",q=>{const u=new URL(q.url());if(u.protocol==="data:")r.inline_requests.push(q.url());else if(u.origin!==origin)r.external_requests.push(q.url());if(q.method()==="POST")r.requests.push({method:q.method(),path:u.pathname,body:q.postData()});});
  page.on("requestfailed",q=>r.failed_requests.push({url:q.url(),error:q.failure()}));
  page.on("response",q=>{if(q.request().method()==="POST")tasks.push(q.text().then(body=>r.responses.push({path:new URL(q.url()).pathname,status:q.status(),body,sha256:sha(Buffer.from(body))})));});
  await page.goto(origin+"/",{waitUntil:"networkidle0",timeout:15000});await page.waitForFunction(()=>document.querySelector("#status").textContent.startsWith("Ready."),{timeout:10000});
  const input=await page.$("#replay-file");await input.uploadFile(fixture);await page.waitForFunction(()=>document.querySelector("#replay-status").textContent.startsWith("Replay MISMATCH:"),{timeout:10000});await page.click("#replay-explain");
  await page.waitForFunction(()=>{const d=document.querySelector("#replay-differences");return !d.hidden&&d.open&&document.querySelectorAll("#replay-difference-list > li").length===3;},{timeout:10000});await Promise.all(tasks);
  r.dom=await page.evaluate(()=>{
   const box=e=>{const b=e.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height};};
   const d=document.querySelector("#replay-differences");
   return {viewport:{width:innerWidth,height:innerHeight},document:{clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth},details:{box:box(d),scrollWidth:d.scrollWidth,clientWidth:d.clientWidth,open:d.open,hidden:d.hidden},rows:Array.from(document.querySelectorAll("#replay-difference-list > li")).map(li=>({path:li.querySelector("code.replay-path").textContent,kind:li.querySelector("code.replay-kind").textContent,expected_text:li.querySelector("pre.replay-expected").textContent,actual_text:li.querySelector("pre.replay-actual").textContent,box:box(li),sides:Array.from(li.querySelectorAll("pre")).map(e=>({box:box(e),clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,whiteSpace:getComputedStyle(e).whiteSpace,overflowWrap:getComputedStyle(e).overflowWrap,overflowX:getComputedStyle(e).overflowX}))})),injected_elements:document.querySelectorAll("[data-loom-literal]").length};
  });
  check("actual-three-full-rows",r.dom.rows.map(x=>({path:x.path,kind:x.kind,expected:JSON.parse(x.expected_text),actual:JSON.parse(x.actual_text)})),expected);
  check("literal-text-no-elements",r.dom.injected_elements,0);check("no-page-horizontal-overflow",r.dom.document.scrollWidth<=r.dom.document.clientWidth,true);
  check("only-explicit-replay-and-explain",r.requests.map(x=>x.path),["/api/replay","/api/replay/explain"]);
  check("both-production-success",r.responses.map(x=>x.status),[200,200]);
  check("saved-input-exact",r.requests.map(x=>JSON.parse(x.body)),[JSON.parse(fs.readFileSync(fixture)),JSON.parse(fs.readFileSync(fixture))]);
  await page.$eval("#replay-differences",e=>e.scrollIntoView({block:"start"}));await page.evaluate(()=>new Promise(f=>requestAnimationFrame(()=>requestAnimationFrame(f))));
  const viewport=path.join(out,"C-details-scrolled-viewport.png");await page.screenshot({path:viewport,fullPage:false});r.screenshots.push(ident(viewport));
  const panel=await page.$("#replay-differences");const full=path.join(out,"C-details-complete-panel.png");await panel.screenshot({path:full});r.screenshots.push(ident(full));
  const third=await page.$("#replay-difference-list > li:last-child");await third.evaluate(e=>e.scrollIntoView({block:"center"}));await page.evaluate(()=>new Promise(f=>requestAnimationFrame(()=>requestAnimationFrame(f))));
  const tail=path.join(out,"C-literal-row-scrolled.png");await page.screenshot({path:tail,fullPage:false});r.screenshots.push(ident(tail));
  r.last_row_visibility=await third.evaluate(e=>{const b=e.getBoundingClientRect();return {top:b.top,bottom:b.bottom,viewport:innerHeight,visible:b.top>=0&&b.bottom<=innerHeight};});check("literal-row-scroll-reachable",r.last_row_visibility.visible,true);
  check("no-page-errors",r.page_errors,[]);check("no-failed-requests",r.failed_requests,[]);check("no-external-requests",r.external_requests,[]);await page.close();
 }catch(e){r.error=String(e.stack||e);}
 finally{
  try{if(browser){const p=browser.process();await browser.close();r.browser_closed=true;r.browser_exit=p?.exitCode;}if(backend&&!done){backend.kill("SIGINT");await until(()=>done,"server closed");}r.backend_closed=done;}catch(e){r.close_error=String(e);}
  for(const [name,text]of [["backend.stdout",stdout],["backend.stderr",stderr]]){const p=path.join(out,name);fs.writeFileSync(p,text,{flag:"wx"});r[name]=ident(p);}
  r.inputs_after=inputs.map(x=>ident(x.path));r.inputs_preserved=equal(r.inputs_before,r.inputs_after);
  r.accepted=!r.error&&!r.close_error&&r.inputs_preserved&&r.browser_closed&&r.browser_exit===0&&r.backend_closed&&r.backend_exit?.code===0&&r.checks.every(x=>x.pass);
  r.finished=new Date().toISOString();const p=path.join(out,"receipt.json");fs.writeFileSync(p,JSON.stringify(r,null,2)+"\n",{flag:"wx"});
  console.log(JSON.stringify({accepted:r.accepted,checks:r.checks.length,failed:r.checks.filter(x=>!x.pass).map(x=>x.id),error:r.error,receipt:ident(p),screenshots:r.screenshots,closed:{browser:r.browser_closed,backend:r.backend_closed}}));if(!r.accepted)process.exitCode=1;
 }
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
