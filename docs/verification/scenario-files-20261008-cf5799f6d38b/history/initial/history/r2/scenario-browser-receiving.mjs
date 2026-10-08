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
denyProxy.on('connect',(request,socket)=>{proxyBlocks.push({method:'CONNECT',url:request.url});socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');});
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
let savedStationary,savedCrossing;
try {
  browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--disable-background-networking','--no-first-run','--disable-quic','--proxy-server=http://127.0.0.1:'+denyProxy.address().port],userDataDir:path.join(out,'profile')});
  browserCDP=await browser.target().createCDPSession();
  await browserCDP.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(out,'downloads'),eventsEnabled:true});
  browserCDP.on('Browser.downloadWillBegin',event=>downloads.push(event));browserCDP.on('Browser.downloadProgress',event=>progress.set(event.guid,event.state));

  await group('download and reviewed import reproduce the saved policy',async()=>{
    const page=await newPage();
    assert.deepEqual(await readdir(path.join(out,'downloads')),[]);
    await loadWorld(page,stationary);await open(page,'.control-card');await input(page,'policy-horizontal',9);await input(page,'policy-vertical',1500);await input(page,'policy-horizon',8);await input(page,'speed-range',2.5);
    await open(page,'.telemetry-wrap');await page.click('.flight-row:last-child button');
    const before=await visibleState(page);assert.equal(before.conflicts,'1');savedStationary=await saveFile(page);
    const document=JSON.parse(savedStationary.text);
    assert.deepEqual(document.world,before.world);assert.equal(document.now,1002);assert.equal(document.selected_aircraft_id,'TWR202');assert.equal(document.time_scale,2.5);
    assert.deepEqual(Object.keys(document).sort(),['format','now','policy','selected_aircraft_id','time_scale','version','world']);
    assert.equal(document.policy.min_horizontal_nm,9);assert.equal(Object.keys(document.policy).length,7);
    assert.equal(savedStationary.suggested,'towerops-scenario-v7.json');
    await input(page,'policy-horizontal',3);await input(page,'policy-vertical',500);await input(page,'policy-horizon',2);await input(page,'speed-range',1);
    const replacement=await visibleState(page);assert.equal(replacement.conflicts,'0');
    await choose(page,savedStationary.file);await reviewed(page);
    assert.deepEqual(await visibleState(page),replacement);
    assert.equal(await page.$eval('#scenario-policy',el=>el.querySelectorAll('dt').length),7);
    assert.match(await page.$eval('#scenario-summary',el=>el.textContent),/TWR202/);
    await page.click('#load-scenario');await settled(page);
    const restored=await visibleState(page);
    assert.deepEqual(restored.world,before.world);assert.deepEqual(restored.policy,before.policy);assert.equal(restored.rate,2.5);assert.equal(restored.selected,'Edit TWR202');assert.equal(restored.conflicts,'1');assert.equal(restored.readback_disabled,true);
    await page.close();return {download_sha256:savedStationary.sha256,conflicts_before:1,changed_policy_conflicts:0,restored_conflicts:1};
  });

  await group('cancel preserves approvals; confirmed import starts an empty native Python trace',async()=>{
    const page=await newPage();
    savedCrossing=await saveFile(page);const original=JSON.parse(savedCrossing.text);
    await page.click('#run-planner');await page.waitForFunction(()=>!document.querySelector('#approve').disabled);
    assert.match(await page.$eval('#python-status',el=>el.textContent),/Live CPython/);
    await page.click('#approve');const approved=await visibleState(page);assert.equal(approved.readback_disabled,false);
    await choose(page,savedCrossing.file);await reviewed(page);assert.deepEqual(await visibleState(page),approved);
    await page.click('#cancel-scenario');assert.deepEqual(await visibleState(page),approved);
    await page.click('#readback');await page.waitForFunction(()=>document.querySelector('#proposal-output').textContent.startsWith('Simulated setpoint applied'));
    const applied=await visibleState(page);assert.match(applied.audit_status,/EVENTS \/ VALID/);assert.notEqual(applied.audit,'');assert.equal(applied.conflicts,'0');
    await choose(page,savedCrossing.file);await reviewed(page);assert.deepEqual(await visibleState(page),applied);
    await page.click('#load-scenario');await settled(page);
    const loaded=await visibleState(page);assert.deepEqual(loaded.world,original.world);assert.equal(loaded.audit,'');assert.equal(loaded.audit_status,'0 EVENTS / VALID');assert.equal(loaded.approve_disabled,true);assert.equal(loaded.readback_disabled,true);
    await page.click('#run-planner');await page.waitForFunction(()=>!document.querySelector('#approve').disabled);await page.click('#approve');await page.click('#readback');await page.waitForFunction(()=>document.querySelector('#proposal-output').textContent.startsWith('Simulated setpoint applied'));
    const again=await visibleState(page);assert.equal(again.audit,applied.audit);assert.equal(again.conflicts,'0');
    await page.close();return {python_roundtrips:2,audit_restored_from_file:false,deterministic_new_trace:true};
  });

  await group('a changed simulation invalidates the reviewed replacement',async()=>{
    const page=await newPage();await choose(page,savedStationary.file);await reviewed(page);
    await open(page,'.control-card');await input(page,'policy-horizontal',4);
    assert.equal(await page.$eval('#scenario-review',el=>el.hidden),true);assert.equal(await page.$eval('#load-scenario',el=>el.disabled),true);
    assert.match(await page.$eval('#scenario-status',el=>el.textContent),/simulation changed/);
    const before=await visibleState(page);await page.$eval('#load-scenario',el=>el.click());assert.deepEqual(await visibleState(page),before);
    await choose(page,savedStationary.file);await reviewed(page);await input(page,'speed-range',2);
    assert.equal(await page.$eval('#scenario-review',el=>el.hidden),true);
    await choose(page,savedStationary.file);await reviewed(page);await page.click('#edit-selected-track');
    assert.equal(await page.$eval('#choose-scenario',el=>el.disabled),true);assert.equal(await page.$eval('#save-scenario',el=>el.disabled),true);
    await page.click('#cancel-track-edit');assert.equal(await page.$eval('#choose-scenario',el=>el.disabled),false);
    await page.click('#toggle-run');assert.equal(await page.$eval('#choose-scenario',el=>el.disabled),true);await page.click('#toggle-run');
    assert.equal(await page.$eval('#choose-scenario',el=>el.disabled),false);assert.equal(await page.$eval('#save-scenario',el=>el.disabled),false);
    await page.close();return {invalidated_by:['policy','time scale','flight editor','running traffic'],paused_controls_available:true};
  });

  await group('canceled and superseded asynchronous file reads cannot publish a replacement',async()=>{
    const page=await newPage();
    await page.evaluate(()=>{const original=File.prototype.text;window.fileReads=[];File.prototype.text=function(){const data=original.call(this);return new Promise(resolve=>window.fileReads.push(()=>data.then(resolve)));};});
    const initial=await visibleState(page);await choose(page,savedStationary.file);await page.waitForFunction(()=>window.fileReads.length===1);
    await page.click('#cancel-scenario');await page.evaluate(()=>window.fileReads[0]());await settled(page);
    assert.equal(await page.$eval('#scenario-review',el=>el.hidden),true);assert.deepEqual(await visibleState(page),initial);
    await choose(page,savedStationary.file);await page.waitForFunction(()=>window.fileReads.length===2);
    await choose(page,savedCrossing.file);await page.waitForFunction(()=>window.fileReads.length===3);
    await page.evaluate(()=>window.fileReads[2]());await reviewed(page);const newest=await page.$eval('#scenario-summary',el=>el.textContent);
    await page.evaluate(()=>window.fileReads[1]());await settled(page);assert.equal(await page.$eval('#scenario-summary',el=>el.textContent),newest);
    await page.click('#cancel-scenario');
    await choose(page,savedStationary.file);await page.waitForFunction(()=>window.fileReads.length===4);
    await open(page,'.control-card');await input(page,'policy-horizontal',6);const changed=await visibleState(page);
    await page.evaluate(()=>window.fileReads[3]());await settled(page);
    assert.equal(await page.$eval('#scenario-review',el=>el.hidden),true);assert.deepEqual(await visibleState(page),changed);
    await page.close();return {fault:'delayed File.text only; production source unchanged',canceled:true,newest_wins:true,changed_context_refused:true};
  });

  await group('invalid files preserve the current world, proposal, approval and trace',async()=>{
    const page=await newPage();await page.click('#run-planner');await page.waitForFunction(()=>!document.querySelector('#approve').disabled);await page.click('#approve');
    const before=await visibleState(page),base=JSON.parse(savedStationary.text);
    const bad=[['broken.json','{oops'],['wrong-version.json',{...base,version:2}],['unknown-field.json',{...base,approval:{decision:'approve'}}],['invisible-policy.json',{...base,policy:{...base.policy,max_speed_nm_min:60}}],['oversize.json',' '.repeat(262145)],['foreign-selection.json',{...base,selected_aircraft_id:'FOREIGN'}]];
    const messages=[];
    for(const[name,body]of bad){await choose(page,await fixture(name,body));await page.waitForFunction(()=>document.querySelector('#scenario-status').textContent.startsWith('NOT LOADED:'));messages.push(await page.$eval('#scenario-status',el=>el.textContent));assert.equal(await page.$eval('#scenario-review',el=>el.hidden),true);assert.deepEqual(await visibleState(page),before);}
    await page.evaluate(()=>{File.prototype.text=()=>Promise.reject(new Error('synthetic unreadable file'));});
    await choose(page,savedStationary.file);await page.waitForFunction(()=>document.querySelector('#scenario-status').textContent.includes('synthetic unreadable'));assert.deepEqual(await visibleState(page),before);
    await page.close();return {refused_files:bad.map(x=>x[0]),messages,unreadable_file_preserved:true};
  });

  await group('legacy WorldState and selected-flight preview/apply remain usable',async()=>{
    const page=await newPage();await loadWorld(page,stationary);await open(page,'.control-card');await page.click('#edit-selected-track');
    await input(page,'flight-x',1);await page.click('#preview-track-edit');assert.equal(await page.$eval('#apply-track-edit',el=>el.disabled),false);
    const before=await visibleState(page);assert.deepEqual(before.world,stationary);
    await page.click('#apply-track-edit');const after=await visibleState(page);assert.equal(after.world.version,8);assert.equal(after.world.aircraft[0].x_nm,1);assert.deepEqual(after.world.aircraft[1],stationary.aircraft[1]);
    await page.click('#export-world');const raw=JSON.parse(await page.$eval('#world-json',el=>el.value));assert.equal(Object.hasOwn(raw,'format'),false);assert.deepEqual(raw,after.world);
    await page.close();return {legacy_raw_world:true,versioned_selected_edit:true,other_aircraft_preserved:true};
  });

  await group('phone review supports literal filenames, keyboard apply and bounded layout',async()=>{
    const page=await newPage(390);
    const named=await fixture('<img onerror=alert(1)>.json',savedStationary.text);
    await choose(page,named);await reviewed(page);
    assert.match(await page.$eval('#scenario-summary',el=>el.textContent),/<img onerror=alert\(1\)>/);
    assert.equal(await page.$eval('#scenario-review',el=>el.querySelectorAll('img,script').length),0);
    assert.equal(await page.evaluate(()=>document.activeElement.id),'scenario-review-title');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await (await page.$('.scenario-workbench')).screenshot({path:path.join(out,'scenario-phone.png')});
    await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'load-scenario');await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.querySelector('#scenario-status').textContent.startsWith('Scenario loaded'));
    assert.equal((await visibleState(page)).conflicts,'1');
    await page.setViewport({width:1380,height:920});await choose(page,named);await reviewed(page);
    await (await page.$('.scenario-workbench')).screenshot({path:path.join(out,'scenario-desktop.png')});
    await page.close();return {phone_width:390,no_horizontal_overflow:true,literal_filename:true,keyboard_confirmed:true};
  });

  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const files=[];
  const tracked=execFileSync('git',['ls-files','--cached','--others','--exclude-standard','-z'],{cwd:source}).toString().split('\0').filter(Boolean);
  for(const p of tracked){const data=await readFile(path.join(source,p));files.push({path:p,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex'),git_blob:createHash('sha1').update(Buffer.from('blob '+data.length+'\0')).update(data).digest('hex')});}
  await writeFile(path.join(out,'receipt.json'),JSON.stringify({schema:'towerops.scenario-browser.v1',source_parent:execFileSync('git',['rev-parse','HEAD'],{cwd:source}).toString().trim(),runtime:{node:process.version,browser:await browser.version(),puppeteer:require('puppeteer/package.json').version},groups,browser_errors:errors,external_requests:external,proxy_blocks:proxyBlocks,downloads:downloads.map(d=>({suggested_filename:d.suggestedFilename,guid:d.guid,state:progress.get(d.guid)})),requests,files},null,2)+'\n');
  console.log(JSON.stringify({passed:groups.length,total:groups.length,errors,external,out}));
}catch(error){
  await writeFile(path.join(out,'failure.json'),JSON.stringify({groups,errors,external,proxyBlocks,requests,error:String(error),stack:error.stack,pages:browser?await Promise.all((await browser.pages()).map(async p=>({url:p.url(),status:await p.evaluate(()=>({python:document.querySelector('#python-status')?.textContent,scenario:document.querySelector('#scenario-status')?.textContent,proposal:document.querySelector('#proposal-output')?.textContent})).catch(e=>String(e))}))):[]},null,2)+'\n');
  console.error(error);process.exitCode=1;
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));await new Promise(resolve=>denyProxy.close(resolve));}
