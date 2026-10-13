"use strict";
const fs=require("fs"),path=require("path"),crypto=require("crypto"),assert=require("assert/strict"),http=require("http"),{spawnSync}=require("child_process");
const [specPath,out,variant]=process.argv.slice(2);
assert(specPath&&out&&path.isAbsolute(specPath)&&path.isAbsolute(out)&&["original","candidate"].includes(variant),"usage: node receiver.cjs SPEC.json ABSENT_OUT original|candidate");
const sha=b=>crypto.createHash("sha256").update(b).digest("hex");
const ident=p=>{const s=fs.lstatSync(p);assert(s.isFile()&&!s.isSymbolicLink());const b=fs.readFileSync(p);return {path:p,bytes:b.length,sha256:sha(b),mode:"0o"+(s.mode&511).toString(8)};};
const equal=(a,b)=>require("util").isDeepStrictEqual(a,b);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await wait(25);}throw Error("Timed out: "+label);}
async function bounded(p,ms,label){let t;try{return await Promise.race([p,new Promise((_,rej)=>t=setTimeout(()=>rej(Error(label)),ms))]);}finally{clearTimeout(t);}}
(async()=>{
 const base=__dirname,freeze=JSON.parse(fs.readFileSync(path.join(base,"freeze-v2.json"))),criteria=JSON.parse(fs.readFileSync(path.join(base,"criteria.json")));
 assert.equal(sha(fs.readFileSync(__filename)),freeze.receiver.sha256);
 assert.equal(sha(fs.readFileSync(path.join(base,"criteria.json"))),freeze.criteria.sha256);
 const spec=JSON.parse(fs.readFileSync(specPath));assert.equal(spec.variant,variant);assert.equal(spec.files.length,8);
 const sourceBefore=spec.files.map(r=>{assert(path.isAbsolute(r.source_path));const i=ident(r.source_path);assert.equal(i.bytes,r.bytes);assert.equal(i.sha256,r.sha256);assert.equal(i.mode,r.mode);return i;});
 assert.deepEqual(spec.files.map(r=>r.path).sort(),["EXPLORER.md","explorer.py","scenarios.py","test_explorer.py","towerops.py","web/app.js","web/index.html","web/style.css"].sort());
 const source=new Map(spec.files.map(r=>[r.path,r.source_path]));
 const controlsBefore=[__filename,path.join(base,"criteria.json"),path.join(base,"freeze-v2.json"),specPath].map(ident);
 fs.mkdirSync(out);fs.mkdirSync(path.join(out,"streams"));fs.mkdirSync(path.join(out,"fixtures"));
 const receipt={schema:"hamon.loom.towerops-replay-browser.v2",started:new Date().toISOString(),variant,source_spec:spec,source_before:sourceBefore,controls_before:controlsBefore,commands:[],checks:[],courses:[],screenshots:[],error:null};
 const check=(id,actual,expected)=>{const pass=equal(actual,expected);receipt.checks.push({id,actual,expected,pass});return pass;};
 const run=(label,args,expected)=>{const env={...process.env};for(const k of Object.keys(env))if(k.startsWith("PYTHON"))delete env[k];env.PYTHONDONTWRITEBYTECODE="1";
   const child=spawnSync(spec.python,["-B",source.get("explorer.py"),...args],{cwd:out,env,encoding:"utf8",timeout:10000,maxBuffer:1024*1024});
   for(const stream of ["stdout","stderr"])fs.writeFileSync(path.join(out,"streams",label+"."+stream),child[stream]||"",{flag:"wx"});
   const row={label,executable:spec.python,args:["-B",source.get("explorer.py"),...args],status:child.status,signal:child.signal,error:child.error?.message,stdout:ident(path.join(out,"streams",label+".stdout")),stderr:ident(path.join(out,"streams",label+".stderr"))};receipt.commands.push(row);
   assert.equal(child.status,expected,label);assert.equal(child.stderr,"",label);return JSON.parse(child.stdout);
 };
 let browser,server,releaseHeld=null;const sockets=new Set();let socketClose=false;
 try{
   const A=run("01-native-export",["run","approved"],0);
   const fixtureA=path.join(out,"fixtures","export-A.json");fs.copyFileSync(path.join(out,"streams","01-native-export.stdout"),fixtureA,fs.constants.COPYFILE_EXCL);
   assert.equal(typeof A.after.version,"number");const B=structuredClone(A);B.after.version+=1;
   const fixtureB=path.join(out,"fixtures","export-B.json");fs.writeFileSync(fixtureB,JSON.stringify(B,null,2)+"\n",{flag:"wx"});
   const replyA=run("02-native-replay-A",["replay",fixtureA],0),replyB=run("03-native-replay-B",["replay",fixtureB],1);
   check("native.A-match",replyA.matches,true);check("native.B-mismatch",replyB.matches,false);
   receipt.fixture_before=[fixtureA,fixtureB].map(ident);
   const matchText="Replay MATCH: "+replyA.outcome+". "+replyA.note;
   const mismatchText="Replay MISMATCH: export differs from the deterministic engine result. "+replyB.note;
   let course=null;
   const send=(res,status,data,label,hold=false)=>{
     const bytes=Buffer.from(JSON.stringify(data));res.writeHead(status,{"Content-Type":"application/json","Content-Length":bytes.length,"Cache-Control":"no-store","X-Loom-Response":label});res.flushHeaders();
     if(hold){assert.equal(releaseHeld,null);res.write(bytes.subarray(0,1));releaseHeld=()=>{res.end(bytes.subarray(1));releaseHeld=null;};course.held_label=label;course.held_ready=true;}
     else res.end(bytes);
   };
   server=http.createServer(async(req,res)=>{
    try{
     const url=new URL(req.url,"http://127.0.0.1");const route=url.pathname;
     if(req.method==="GET"&&["/","/app.js","/style.css"].includes(route)){
       const name={"/":"web/index.html","/app.js":"web/app.js","/style.css":"web/style.css"}[route];res.writeHead(200,{"Content-Type":name.endsWith(".html")?"text/html":name.endsWith(".js")?"text/javascript":"text/css","Cache-Control":"no-store"});res.end(fs.readFileSync(source.get(name)));return;
     }
     if(req.method==="GET"&&route==="/api/scenarios"){send(res,200,{scenarios:[{id:"approved",label:A.label,description:"Authored browser receiving: native approved fixture."}]},"scenarios");return;}
     if(req.method==="GET"&&route==="/favicon.ico"){res.writeHead(204);res.end();return;}
     if(req.method!=="POST"||!["/api/run","/api/replay"].includes(route))throw Error("Unexpected request "+req.method+" "+route);
     let body="";for await(const b of req){body+=b;if(body.length>262144)throw Error("request too large");}
     const value=JSON.parse(body);course.requests.push({method:req.method,path:route,body,bytes:Buffer.byteLength(body),sha256:sha(Buffer.from(body))});
     if(route==="/api/run"){assert.deepEqual(value,{scenario:"approved",include_approval:true,include_ack:true});send(res,200,A,"run");return;}
     const replayNo=course.requests.filter(x=>x.path==="/api/replay").length;
     assert(equal(value,A)||equal(value,B),"unexpected replay body");
     const reply=equal(value,A)?replyA:replyB;
     if(replayNo===1){assert(equal(value,A));send(res,200,reply,course.name+"-old-A",true);}
     else{assert.equal(replayNo,2);assert(equal(value,B));send(res,200,reply,course.name+"-new-B");}
    }catch(e){receipt.server_error=String(e.stack||e);if(!res.headersSent)send(res,500,{error:"Authored receiving server failure"},"server-error");else res.destroy();}
   });
   server.on("connection",s=>{sockets.add(s);s.on("close",()=>sockets.delete(s));});
   await new Promise((resolve,reject)=>{server.once("error",reject);server.listen(0,"127.0.0.1",resolve);});
   const origin="http://127.0.0.1:"+server.address().port;receipt.origin=origin;
   const puppeteer=require(spec.browser_module);
   browser=await puppeteer.launch({browser:"firefox",executablePath:spec.browser_executable,headless:true,userDataDir:path.join(out,"profile"),timeout:20000});
   receipt.browser_version=await browser.version();receipt.browser_pid=browser.process()?.pid;
   const shot=async(page,name)=>{const p=path.join(out,name+".png");await page.screenshot({path:p,fullPage:false});receipt.screenshots.push(ident(p));};
   for(const name of ["newer-file","cleared-file"]){
    course={name,requests:[],finished:[],failed_requests:[],page_errors:[],external_requests:[],inline_requests:[],held_ready:false};receipt.courses.push(course);
    const page=await browser.newPage();await page.setViewport({width:1280,height:1000});
    page.on("pageerror",e=>course.page_errors.push(String(e)));
    page.on("request",r=>{if(new URL(r.url()).protocol==="data:")course.inline_requests.push(r.url());else if(!r.url().startsWith(origin+"/"))course.external_requests.push(r.url());});
    page.on("requestfailed",r=>course.failed_requests.push({url:r.url(),error:r.failure()}));
    page.on("requestfinished",r=>{const label=r.response()?.headers()["x-loom-response"];if(label)course.finished.push(label);});
    await page.goto(origin+"/",{waitUntil:"networkidle0",timeout:15000});
    await page.waitForFunction(()=>document.querySelector("#status").textContent.startsWith("Ready."),{timeout:10000});
    await page.click("#run");await page.waitForFunction(()=>!document.querySelector("#result").hidden,{timeout:10000});
    const displayed=()=>page.evaluate(()=>({result:document.querySelector("#result").innerHTML,status:document.querySelector("#status").textContent,exportDisabled:document.querySelector("#export").disabled}));
    course.display_before=await displayed();
    const input=await page.$("#replay-file");await input.uploadFile(fixtureA);
    await until(()=>course.held_ready,"old response body is held");
    await page.waitForFunction(()=>document.querySelector("#replay-status").textContent==="Replaying locally…",{timeout:10000});
    const status=()=>page.$eval("#replay-status",x=>x.textContent);
    if(name==="newer-file"){
      await input.uploadFile(fixtureB);
      await page.waitForFunction(text=>document.querySelector("#replay-status").textContent===text,{timeout:10000},mismatchText);
      check(name+".newer-status",await status(),mismatchText);await shot(page,name+"-before-release");
    }else{
      await input.evaluate(el=>{el.value="";el.dispatchEvent(new Event("change",{bubbles:true}));});
      check(name+".files-cleared",await input.evaluate(el=>el.files.length),0);
      check(name+".immediate-status",await status(),"");
    }
    assert(releaseHeld);releaseHeld();
    await until(()=>course.finished.includes(course.held_label),"browser old-body completion");
    check(name+".completion-once",course.finished.filter(x=>x===course.held_label).length,1);
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await wait(150);
    course.final_status=await status();
    check(name+".final-status",course.final_status,name==="newer-file"?mismatchText:"");
    course.display_after=await displayed();check(name+".display-preserved",course.display_after,course.display_before);
    check(name+".request-counts",course.requests.map(x=>x.path),name==="newer-file"?["/api/run","/api/replay","/api/replay"]:["/api/run","/api/replay"]);
    check(name+".no-page-errors",course.page_errors,[]);check(name+".no-external-requests",course.external_requests,[]);
    check(name+".no-failed-requests",course.failed_requests,[]);
    await shot(page,name+"-after-release");await page.close();
   }
   check("server.no-error",receipt.server_error||null,null);
   receipt.expected_original_late_status=matchText;
 }catch(e){receipt.error=String(e.stack||e);}
 finally{
   try{if(releaseHeld)releaseHeld();if(browser){const process=browser.process();await bounded(browser.close(),15000,"browser close timeout");receipt.browser_closed=true;receipt.browser_exit_code=process?.exitCode;}}catch(e){receipt.close_error=String(e);}
   try{if(server){server.closeIdleConnections();await bounded(new Promise(r=>server.close(r)),10000,"server close timeout");socketClose=true;}receipt.server_closed=socketClose;receipt.open_socket_count=sockets.size;}catch(e){receipt.server_close_error=String(e);}
   try{receipt.source_after=sourceBefore.map(r=>ident(r.path));check("source.preserved",receipt.source_after,sourceBefore);receipt.controls_after=controlsBefore.map(r=>ident(r.path));check("controls.preserved",receipt.controls_after,controlsBefore);if(receipt.fixture_before){receipt.fixture_after=receipt.fixture_before.map(r=>ident(r.path));check("fixtures.preserved",receipt.fixture_after,receipt.fixture_before);}}catch(e){receipt.preservation_error=String(e);}
   const expected=variant==="original"?criteria.acceptance.original_expected_failed_check_ids:criteria.acceptance.candidate_expected_failed_check_ids;
   receipt.failed_check_ids=receipt.checks.filter(x=>!x.pass).map(x=>x.id);
   receipt.expected_failed_check_ids=expected;
   receipt.accepted=!receipt.error&&!receipt.close_error&&!receipt.server_close_error&&!receipt.preservation_error&&receipt.browser_closed===true&&receipt.server_closed===true&&receipt.open_socket_count===0&&equal([...receipt.failed_check_ids].sort(),[...expected].sort());
   receipt.finished=new Date().toISOString();fs.writeFileSync(path.join(out,"receipt.json"),JSON.stringify(receipt,null,2)+"\n",{flag:"wx"});
   console.log(JSON.stringify({accepted:receipt.accepted,variant,checks:receipt.checks.length,failed_check_ids:receipt.failed_check_ids,error:receipt.error,browser_pid:receipt.browser_pid,browser_closed:receipt.browser_closed,server_closed:receipt.server_closed,open_socket_count:receipt.open_socket_count,out}));
   if(!receipt.accepted)process.exitCode=1;
 }
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
