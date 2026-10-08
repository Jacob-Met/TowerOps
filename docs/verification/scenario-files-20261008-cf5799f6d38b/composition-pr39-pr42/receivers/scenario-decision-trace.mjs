import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,stat,readdir} from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const require=createRequire(import.meta.url),puppeteer=require('puppeteer');
const source=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
await mkdir(out,{recursive:true});await mkdir(path.join(out,'downloads'),{recursive:true});await mkdir(path.join(out,'fixtures'),{recursive:true});
const root=path.join(source,'web/airspace/dist'),requests=[],errors=[],external=[],groups=[],downloads=[],progress=new Map();
let activeGroup='',browser,browserCDP;
const server=http.createServer(async(req,res)=>{
  try {
    const pathname=new URL(req.url,'http://localhost').pathname;
    const relative=decodeURIComponent(pathname.replace(/^\/TowerOps\/airspace\/?/,''));
    const target=path.resolve(root,relative||'index.html');
    if(!target.startsWith(root+path.sep)&&target!==root)throw new Error('path');
    const file=(await stat(target)).isDirectory()?path.join(target,'index.html'):target;
    const body=await readFile(file),types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml'};
    requests.push({group:activeGroup,path:pathname,status:200,sha256:createHash('sha256').update(body).digest('hex')});
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});res.end(body);
  }catch{res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const proxyBlocks=[];
const denyProxy=http.createServer((request,response)=>{proxyBlocks.push({method:request.method,url:request.url});response.writeHead(403);response.end('Offline receiving proxy');});
denyProxy.on('connect',(request,socket)=>{socket.on('error',error=>proxyBlocks.push({method:'CONNECT_SOCKET_ERROR',url:request.url,code:error.code,message:error.message}));proxyBlocks.push({method:'CONNECT',url:request.url});socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');});
await new Promise(resolve=>denyProxy.listen(0,'127.0.0.1',resolve));

const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(check,label,limit=15000){const begin=Date.now();while(Date.now()-begin<limit){if(await check())return;await delay(20);}throw new Error('Timed out: '+label);}
async function settled(page){await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));}
async function open(page,selector){if(!await page.$eval(selector,el=>el.open))await page.click(selector+' > summary');}
async function newPage(width=1380){const page=await browser.newPage();await page.setViewport({width,height:920});page.on('pageerror',e=>errors.push({group:activeGroup,error:String(e)}));page.on('request',r=>{if(new URL(r.url()).origin!==origin)external.push({group:activeGroup,url:r.url()});});await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});await open(page,'.scenario-workbench');return page;}
async function input(page,id,value){await page.$eval('#'+id,(el,v)=>{el.value=String(v);el.dispatchEvent(new Event('input',{bubbles:true}));},value);await settled(page);}
async function loadWorld(page,world){await open(page,'.state-workbench');await page.$eval('#world-json',(el,v)=>{el.focus();el.value=JSON.stringify(v);},world);await page.click('#load-world');await settled(page);assert.match(await page.$eval('#world-json-feedback',el=>el.textContent),/^Loaded/);}
async function visibleState(page){await settled(page);return page.evaluate(()=>({
  world:JSON.parse(document.querySelector('#world-json').value),
  policy:['policy-horizontal','policy-vertical','policy-horizon'].map(id=>Number(document.getElementById(id).value)),
  clock:document.querySelector('#sim-clock').textContent,
  rate:Number(document.querySelector('#speed-range').value),
  selected:document.querySelector('#edit-selected-track').textContent,
  conflicts:document.querySelector('#pair-count').textContent,
  audit:document.querySelector('#audit-events').textContent,
  audit_status:document.querySelector('#audit-status').textContent,
  proposal:document.querySelector('#proposal-output').textContent,
  approve_disabled:document.querySelector('#approve').disabled,
  readback_disabled:document.querySelector('#readback').disabled,
}));}
async function choose(page,file){const chooser=page.waitForFileChooser();await page.click('#choose-scenario');await(await chooser).accept([file]);}
async function reviewed(page){await page.waitForFunction(()=>!document.querySelector('#scenario-review').hidden&&!document.querySelector('#load-scenario').disabled);await settled(page);}
async function saveFile(page){const index=downloads.length;await page.click('#save-scenario');await until(()=>downloads.length>index,'download starts');const dl=downloads[index];await until(()=>progress.get(dl.guid)==='completed','download completes');const file=path.join(out,'downloads',dl.guid);const text=await readFile(file,'utf8');return{file,text,suggested:dl.suggestedFilename,sha256:createHash('sha256').update(text).digest('hex')};}
async function fixture(name,value){const file=path.join(out,'fixtures',name);await writeFile(file,typeof value==='string'?value:JSON.stringify(value));return file;}
async function group(name,fn){activeGroup=name;const t=Date.now();try{const evidence=await fn();groups.push({name,passed:true,milliseconds:Date.now()-t,...evidence});console.log(JSON.stringify(groups.at(-1)));}catch(e){groups.push({name,passed:false,milliseconds:Date.now()-t,error:String(e)});throw e;}}
const stationary={version:7,observed_at:1002,aircraft:[
{aircraft_id:'TWR101',x_nm:0,y_nm:0,altitude_ft:10000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0},
{aircraft_id:'TWR202',x_nm:7,y_nm:0,altitude_ft:10000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0}
]};

async function planAndApprove(page){
 await page.click('#run-planner');
 await page.waitForFunction(()=>document.querySelector('#proposal-state').textContent==='PROPOSAL READY');
 await page.click('#approve');await settled(page);
 assert.equal(await page.$eval('#readback',el=>el.disabled),false);
}
async function nativeReadback(page){
 await page.click('#readback');
 await page.waitForFunction(()=>document.querySelector('#gate-ack i').textContent==='ACCEPTED');
 await settled(page);
 assert.equal(await page.$eval('#audit-events',el=>el.children.length),4);
}
async function downloadTrace(page){
 const index=downloads.length;await page.click('#download-current-trace');
 await until(()=>downloads.length>index,'trace download starts');
 const dl=downloads[index];await until(()=>progress.get(dl.guid)==='completed','trace download completes');
 const text=await readFile(path.join(out,'downloads',dl.guid),'utf8');
 assert.equal(dl.suggestedFilename,'towerops-decision-trace.json');
 return{text,sha256:createHash('sha256').update(text).digest('hex')};
}
async function reviewTrace(page,kind,verdict){
 await page.click('#review-'+kind+'-trace');
 await page.waitForFunction(()=>document.querySelector('#decision-trace-feedback').textContent.startsWith('Review complete for'));
 await settled(page);
 assert.equal(await page.$eval('#decision-trace-result',el=>el.dataset.verdict),verdict);
 return page.$eval('#decision-trace-result',el=>el.textContent);
}
try {
  browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--disable-background-networking','--no-first-run','--disable-quic','--proxy-server=http://127.0.0.1:'+denyProxy.address().port],userDataDir:path.join(out,'profile')});
  browserCDP=await browser.target().createCDPSession();
  await browserCDP.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(out,'downloads'),eventsEnabled:true});
  browserCDP.on('Browser.downloadWillBegin',event=>downloads.push(event));browserCDP.on('Browser.downloadProgress',event=>progress.set(event.guid,event.state));


  await group('scenario Apply clears the native current trace while an opened prior history remains read-only',async()=>{
    const page=await newPage(),saved=await saveFile(page);
    await open(page,'.telemetry-wrap');await planAndApprove(page);await nativeReadback(page);
    const old=await downloadTrace(page);assert.equal(JSON.parse(old.text).length,4);
    await choose(page,saved.file);await reviewed(page);await page.click('#load-scenario');await settled(page);
    const loaded=await visibleState(page);
    assert.equal(loaded.audit,'');assert.equal(loaded.readback_disabled,true);
    assert.equal((await downloadTrace(page)).text,'[]');
    const emptyReport=await reviewTrace(page,'current','empty');
    assert.match(emptyReport,/current trace snapshot · 0 events/);
    assert.deepEqual(await visibleState(page),loaded);
    const oldFile=await fixture('previous-scenario-decision-trace.json',old.text);
    const chooser=page.waitForFileChooser();await page.click('#open-trace-file');await(await chooser).accept([oldFile]);
    await page.waitForFunction(()=>!document.querySelector('#review-opened-trace').disabled);
    const openedReport=await reviewTrace(page,'opened','valid');
    assert.match(openedReport,/previous-scenario-decision-trace.json · 4 events/);
    assert.deepEqual(await visibleState(page),loaded);
    assert.equal((await downloadTrace(page)).text,'[]');
    assert.deepEqual(JSON.parse((await saveFile(page)).text),JSON.parse(saved.text));
    await (await page.$('.decision-trace-review')).screenshot({path:path.join(out,'scenario-with-prior-trace-snapshot.png')});
    await page.close();return{old_trace_sha256:old.sha256,old_event_count:4,current_trace_after_scenario_load:'[]',opened_report_is_named_history:true,scenario_and_gates_unchanged_by_history_review:true};
  });
  await group('native trace review invalidates a pending scenario import and preserves its live approved decision',async()=>{
    const page=await newPage(),saved=await saveFile(page);
    await open(page,'.telemetry-wrap');await planAndApprove(page);
    await choose(page,saved.file);await reviewed(page);
    const approved=await visibleState(page);
    await reviewTrace(page,'current','empty');
    assert.deepEqual(await visibleState(page),approved);
    assert.equal(await page.$eval('#scenario-review',el=>el.hidden),true);
    assert.equal(await page.$eval('#load-scenario',el=>el.disabled),true);
    assert.equal(await page.$eval('#readback',el=>el.disabled),false);
    await page.$eval('#load-scenario',el=>el.click());await settled(page);
    assert.deepEqual(await visibleState(page),approved);
    await nativeReadback(page);
    const applied=await visibleState(page);
    assert.equal(JSON.parse((await downloadTrace(page)).text).length,4);
    assert.equal(applied.world.version,approved.world.version+1);
    await page.close();return{pending_import_invalidated:true,approval_preserved:true,native_readback_accepted:true,new_world_version:applied.world.version};
  });

  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const files=[];
  const tracked=execFileSync('git',['ls-files','-z'],{cwd:source}).toString().split('\0').filter(Boolean);
  for(const p of tracked){const data=await readFile(path.join(source,p));files.push({path:p,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex'),git_blob:createHash('sha1').update(Buffer.from('blob '+data.length+'\0')).update(data).digest('hex')});}
  await writeFile(path.join(out,'receipt.json'),JSON.stringify({schema:'towerops.scenario-decision-trace-composition-browser.v1',source_tree:execFileSync('git',['write-tree'],{cwd:source}).toString().trim(),source_parent:execFileSync('git',['rev-parse','HEAD'],{cwd:source}).toString().trim(),runtime:{node:process.version,browser:await browser.version(),puppeteer:require('puppeteer/package.json').version},groups,browser_errors:errors,external_requests:external,proxy_blocks:proxyBlocks,downloads:downloads.map(d=>({suggested_filename:d.suggestedFilename,guid:d.guid,state:progress.get(d.guid)})),requests,files},null,2)+'\n');
  console.log(JSON.stringify({passed:groups.length,total:groups.length,errors,external,out}));
}catch(error){
  await writeFile(path.join(out,'failure.json'),JSON.stringify({groups,errors,external,proxyBlocks,requests,error:String(error),stack:error.stack,pages:browser?await Promise.all((await browser.pages()).map(async p=>({url:p.url(),status:await p.evaluate(()=>({python:document.querySelector('#python-status')?.textContent,scenario:document.querySelector('#scenario-status')?.textContent,proposal:document.querySelector('#proposal-output')?.textContent})).catch(e=>String(e))}))):[]},null,2)+'\n');
  console.error(error);process.exitCode=1;
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));await new Promise(resolve=>denyProxy.close(resolve));}