import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const require=createRequire(import.meta.url),puppeteer=require('puppeteer');
const source=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
await mkdir(out,{recursive:true});await mkdir(path.join(out,'downloads'),{recursive:true});await mkdir(path.join(out,'fixtures'),{recursive:true});
const dist=path.join(source,'web/airspace/dist'),requests=[],errors=[],external=[],groups=[],downloads=[],progress=new Map();
const sha=b=>createHash('sha256').update(b).digest('hex');
const sourceTree=execFileSync('git',['write-tree'],{cwd:source}).toString().trim();
const sourceMain=sha(await readFile(path.join(source,'web/airspace/src/main.ts')));
let activeGroup='',browser;
const server=http.createServer(async(req,res)=>{
 try{
  const pathname=new URL(req.url,'http://localhost').pathname;
  const relative=decodeURIComponent(pathname.replace(/^\/TowerOps\/airspace\/?/,''));
  const target=path.resolve(dist,relative||'index.html');
  if(target!==dist&&!target.startsWith(dist+path.sep))throw Error('Outside fixture');
  const file=(await stat(target)).isDirectory()?path.join(target,'index.html'):target;
  const body=await readFile(file),types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml'};
  requests.push({group:activeGroup,path:pathname,status:200,sha256:sha(body)});
  res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});res.end(body);
 }catch(error){requests.push({group:activeGroup,path:req.url,status:404,error:String(error)});res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port,proxyBlocks=[];
const proxy=http.createServer((req,res)=>{proxyBlocks.push({method:req.method,url:req.url});res.writeHead(403);res.end('Offline receiver');});
proxy.on('connect',(req,socket)=>{socket.on('error',e=>proxyBlocks.push({method:'SOCKET_ERROR',code:e.code}));proxyBlocks.push({method:'CONNECT',url:req.url});socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');});
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(fn,label){for(let i=0;i<750;i++){if(await fn())return;await pause(20);}throw Error('Timed out: '+label);}
async function settled(page){await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));}
async function open(page,selector){if(!await page.$eval(selector,e=>e.open))await page.click(selector+' > summary');}
async function pageAt(width=1380){
 const page=await browser.newPage();await page.setViewport({width,height:940});
 page.on('pageerror',e=>errors.push({group:activeGroup,error:String(e)}));
 page.on('request',r=>{if(!r.url().startsWith('blob:')&&!r.url().startsWith('data:')&&new URL(r.url()).origin!==origin)external.push({group:activeGroup,url:r.url()});});
 await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});
 await page.waitForFunction(()=>!!document.querySelector('#world-json')?.value);
 await open(page,'.state-workbench');await open(page,'.scenario-workbench');return page;
}
const draft=page=>page.$eval('#world-json',e=>e.value);
const feedback=page=>page.$eval('#world-json-feedback',e=>e.textContent);
const register=page=>page.$$eval('#flight-list button',nodes=>nodes.map(n=>n.textContent));
async function typeDraft(page,text){
 await page.click('#world-json');await page.$eval('#world-json',e=>e.select());
 await page.keyboard.sendCharacter(text);await settled(page);assert.equal(await draft(page),text);
}
async function save(page){
 const first=downloads.length;await page.click('#save-scenario');try{await until(()=>downloads.length>first,'download starts');}catch(error){const observed=await page.evaluate(()=>({status:document.querySelector('#scenario-status').textContent,saveDisabled:document.querySelector('#save-scenario').disabled,reviewHidden:document.querySelector('#scenario-review').hidden,rawFeedback:document.querySelector('#world-json-feedback').textContent,worldJson:document.querySelector('#world-json').value,availability:document.querySelector('#scenario-availability').textContent,run:document.querySelector('#toggle-run').textContent,active:document.activeElement?.id,register:[...document.querySelectorAll('#flight-list button')].map(e=>e.textContent)}));await writeFile(path.join(out,'download-failure.json'),JSON.stringify({group:activeGroup,observed},null,2)+'\n');throw error;}
 const record=downloads[first];await until(()=>progress.get(record.guid)==='completed','download completes');
 const file=path.join(out,'downloads',record.guid),text=await readFile(file,'utf8');
 return {file,text,document:JSON.parse(text),sha256:sha(text),suggested:record.suggestedFilename};
}
async function choose(page,file){const chooser=page.waitForFileChooser();await page.click('#choose-scenario');await(await chooser).accept([file]);}
async function reviewed(page){await page.waitForFunction(()=>!document.querySelector('#scenario-review').hidden&&!document.querySelector('#load-scenario').disabled);await settled(page);}
async function targetFrom(saved,name){
 const base=saved.document,target={...base,world:{version:73,observed_at:1002,aircraft:[
 {aircraft_id:'TWR601',x_nm:0,y_nm:0,altitude_ft:11000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0},
 {aircraft_id:'TWR602',x_nm:9,y_nm:0,altitude_ft:11000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0}]},
 policy:{...base.policy,min_horizontal_nm:7,min_vertical_ft:1800,horizon_min:9},now:1002,time_scale:2.5,selected_aircraft_id:'TWR602'};
 const file=path.join(out,'fixtures',name+'.json');await writeFile(file,JSON.stringify(target));return{document:target,file};
}
async function group(name,fn){
 activeGroup=name;const start=Date.now();
 try{const detail=await fn();groups.push({name,passed:true,seconds:(Date.now()-start)/1000,...detail});}
 catch(error){groups.push({name,passed:false,seconds:(Date.now()-start)/1000,error:String(error),stack:error.stack});}
 console.log(JSON.stringify(groups.at(-1)));
}
try{
 browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,userDataDir:path.join(out,'profile'),
  args:['--disable-background-networking','--no-first-run','--disable-quic','--proxy-server=http://127.0.0.1:'+proxy.address().port]});
 const cdp=await browser.target().createCDPSession();
 await cdp.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(out,'downloads'),eventsEnabled:true});
 cdp.on('Browser.downloadWillBegin',e=>downloads.push(e));cdp.on('Browser.downloadProgress',e=>progress.set(e.guid,e.state));
 await group('saved scenario reads the live world and preserves a separate draft through review and cancel',async()=>{
  const page=await pageAt(),initial=await save(page),target=await targetFrom(initial,'review-target');
  const text='{\n  "unfinished raw draft": "kept literally <script> & 文",\n';await typeDraft(page,text);
  const exported=await save(page);assert.deepEqual(exported.document,initial.document);assert.equal(await draft(page),text);
  await choose(page,target.file);await reviewed(page);assert.equal(await draft(page),text);
  assert.deepEqual(await register(page),initial.document.world.aircraft.map(a=>a.aircraft_id));
  assert.deepEqual((await save(page)).document,initial.document);assert.equal(await draft(page),text);
  await page.click('#cancel-scenario');await settled(page);assert.equal(await draft(page),text);
  assert.equal(await page.$eval('#scenario-review',e=>e.hidden),true);
  const after=await save(page);assert.deepEqual(after.document,initial.document);
  await page.close();return{draft_sha256:sha(text),initial_download:initial.sha256,after_cancel_download:after.sha256};
 });
 await group('Apply restores actual world and policy, keeps the authored draft and explains its ownership',async()=>{
  const page=await pageAt(390),initial=await save(page),target=await targetFrom(initial,'apply-target'),text='{\n  "my unfinished separate draft": ';
  await typeDraft(page,text);await choose(page,target.file);await reviewed(page);await page.click('#load-scenario');await settled(page);
  assert.equal(await draft(page),text);assert.deepEqual(await register(page),['TWR601','TWR602']);
  const message=await feedback(page);assert.match(message,/^Loaded scenario with 2 aircraft at version 73\./);assert.match(message,/raw JSON draft is still kept/);assert.match(message,/Export live world/);
  const restored=await save(page);assert.deepEqual(restored.document,target.document);assert.equal(await draft(page),text);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await (await page.$('.state-workbench')).screenshot({path:path.join(out,'retained-raw-draft-phone.png')});
  await page.close();
  const pristine=await pageAt();await choose(pristine,target.file);await reviewed(pristine);await pristine.click('#load-scenario');await settled(pristine);
  assert.deepEqual(JSON.parse(await draft(pristine)),target.document.world);
  assert.equal(await feedback(pristine),'Loaded scenario with 2 aircraft at version 73.');
  assert.deepEqual((await save(pristine)).document,target.document);await pristine.close();
  return{restored_download:restored.sha256,loaded_callsigns:['TWR601','TWR602'],retained_draft_sha256:sha(text),feedback:message,pristine_feedback_unchanged:true};
 });
 await group('successful raw Load invalidates reviewed scenario even for an identical world value',async()=>{
  const page=await pageAt(),initial=await save(page),target=await targetFrom(initial,'raw-load-target');
  const raw={...initial.document.world,version:81,aircraft:initial.document.world.aircraft.map((a,i)=>({...a,aircraft_id:'RAW'+(701+i)}))};
  for(const mode of ['changed-world','same-world-new-load']){
   await choose(page,target.file);await reviewed(page);await typeDraft(page,JSON.stringify(raw));await page.click('#load-world');await settled(page);
   assert.match(await feedback(page),/^Loaded /);
   assert.equal(await page.$eval('#scenario-review',e=>e.hidden),true);assert.equal(await page.$eval('#load-scenario',e=>e.disabled),true);
   assert.match(await page.$eval('#scenario-status',e=>e.textContent),/simulation changed/);
   assert.deepEqual((await save(page)).document.world,raw);assert.deepEqual(JSON.parse(await draft(page)),raw);
   assert.deepEqual(await register(page),raw.aircraft.map(a=>a.aircraft_id));
  }
  await page.close();return{raw_world_sha256:sha(JSON.stringify(raw)),review_invalidated_for:['changed-world','same-world-new-load']};
 });
 await group('failed raw Load retains review; explicit Export restores live synchronization after scenario Apply',async()=>{
  const page=await pageAt(),initial=await save(page),target=await targetFrom(initial,'failed-raw-target'),text='{"version":-1,"aircraft":[]}';
  await choose(page,target.file);await reviewed(page);const review=await page.$eval('#scenario-summary',e=>e.textContent);
  await typeDraft(page,text);await page.click('#load-world');await settled(page);
  assert.match(await feedback(page),/^NOT LOADED:/);assert.equal(await draft(page),text);
  assert.equal(await page.$eval('#scenario-review',e=>e.hidden),false);assert.equal(await page.$eval('#load-scenario',e=>e.disabled),false);
  assert.equal(await page.$eval('#scenario-summary',e=>e.textContent),review);assert.deepEqual((await save(page)).document,initial.document);
  await page.click('#load-scenario');await settled(page);assert.equal(await draft(page),text);assert.deepEqual((await save(page)).document,target.document);
  await page.click('#export-world');await settled(page);assert.match(await feedback(page),/^Live world exported/);
  assert.deepEqual(JSON.parse(await draft(page)),target.document.world);
  await page.click('#add-traffic');await settled(page);const live=await save(page);
  assert.equal(live.document.world.aircraft.length,3);assert.deepEqual(JSON.parse(await draft(page)),live.document.world);
  await page.setViewport({width:1250,height:940});await settled(page);assert.deepEqual(JSON.parse(await draft(page)),live.document.world);
  await page.close();return{failed_draft_sha256:sha(text),review_preserved_after_refusal:true,restored_after_export:target.document.world,live_after_change:live.document.world};
 });
}finally{
 const browserVersion=browser?await browser.version():'unavailable';
 if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));await new Promise(resolve=>proxy.close(resolve));
 const sourceUnchanged=sourceTree===execFileSync('git',['write-tree'],{cwd:source}).toString().trim()&&sourceMain===sha(await readFile(path.join(source,'web/airspace/src/main.ts')));
 const receipt={schema:'towerops.scenario-raw-draft-browser.v1',source_tree:sourceTree,main_sha256:sourceMain,receiver_sha256:sha(await readFile(new URL(import.meta.url))),runtime:{node:process.version,browser:browserVersion},
  source_unchanged:sourceUnchanged,groups,requests,errors,external_app_requests:external,proxy_blocks:proxyBlocks,downloads,passed:groups.filter(g=>g.passed).length,total:groups.length};
 await writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 if(groups.length!==4||groups.some(g=>!g.passed)||errors.length||external.length||!sourceUnchanged)process.exitCode=1;
}
