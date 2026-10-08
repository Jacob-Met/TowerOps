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

async function encounter(page){
 await settled(page);
 return page.evaluate(()=>({
  first:document.querySelector('#encounter-first').value,
  second:document.querySelector('#encounter-second').value,
  first_options:Array.from(document.querySelector('#encounter-first').options,x=>x.value),
  second_options:Array.from(document.querySelector('#encounter-second').options,x=>x.value),
  seconds:Number(document.querySelector('#encounter-time').value),
  max_seconds:Number(document.querySelector('#encounter-time').max),
  horizontal:document.querySelector('#encounter-horizontal-value').textContent,
  vertical:document.querySelector('#encounter-vertical-value').textContent,
  source:document.querySelector('#encounter-source').textContent,
  message:document.querySelector('#encounter-message').textContent,
  hidden:document.querySelector('#encounter-content').hidden,
  disabled:['first','second','time','midpoint','closest','now'].map(x=>document.querySelector('#encounter-'+x).disabled),
 }));
}
async function checkEncounter(page,doc){
 const view=await encounter(page),world=(await visibleState(page)).world;
 assert.deepEqual(world,doc.world);
 assert.equal(view.hidden,false);assert.ok(view.first!==view.second);
 const a=world.aircraft.find(x=>x.aircraft_id===view.first),b=world.aircraft.find(x=>x.aircraft_id===view.second),t=view.seconds/60;
 assert.ok(a&&b);assert.ok(t>=0&&t<=doc.policy.horizon_min);
 assert.equal(view.max_seconds,doc.policy.horizon_min*60);
 const h=Math.hypot(a.x_nm-b.x_nm+(a.vx_nm_min-b.vx_nm_min)*t,a.y_nm-b.y_nm+(a.vy_nm_min-b.vy_nm_min)*t);
 const v=Math.abs(a.altitude_ft-b.altitude_ft+(a.climb_ft_min-b.climb_ft_min)*t);
 assert.ok(Math.abs(parseFloat(view.horizontal)-h)<=.0051);
 assert.ok(Math.abs(parseFloat(view.vertical)-v)<=.0501);
 assert.equal(view.source,'WORLD '+world.version+' · CURRENT PAUSED TRAFFIC');
 assert.equal((await visibleState(page)).selected,'Edit '+doc.selected_aircraft_id);
 return view;
}
async function applyFile(page,file){
 await choose(page,file);await reviewed(page);await page.click('#load-scenario');await settled(page);
 assert.match(await page.$eval('#scenario-status',el=>el.textContent),/^Scenario loaded/);
}
function threeFlight(base,version=73){
 return {...base,world:{version,observed_at:1000,aircraft:[
 {aircraft_id:'A1',x_nm:0,y_nm:0,altitude_ft:10000,vx_nm_min:3,vy_nm_min:0,climb_ft_min:0},
 {aircraft_id:'B2',x_nm:10,y_nm:0,altitude_ft:10000,vx_nm_min:-3,vy_nm_min:0,climb_ft_min:0},
 {aircraft_id:'C3',x_nm:0,y_nm:20,altitude_ft:11000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0}
 ]},now:1000,time_scale:1,selected_aircraft_id:'C3',policy:{...base.policy,min_horizontal_nm:3,min_vertical_ft:500,horizon_min:2}};
}
try {
  browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--disable-background-networking','--no-first-run','--disable-quic','--proxy-server=http://127.0.0.1:'+denyProxy.address().port],userDataDir:path.join(out,'profile')});
  browserCDP=await browser.target().createCDPSession();
  await browserCDP.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(out,'downloads'),eventsEnabled:true});
  browserCDP.on('Browser.downloadWillBegin',event=>downloads.push(event));browserCDP.on('Browser.downloadProgress',event=>progress.set(event.guid,event.state));


  await group('review preserves active forecast and approval; Apply refreshes a foreign pair and shorter horizon',async()=>{
    const page=await newPage(),saved=await saveFile(page),doc=threeFlight(JSON.parse(saved.text));
    const file=await fixture('three-flight-short-horizon.json',doc);
    await open(page,'#encounter-explorer');
    await page.click('#run-planner');
    await page.waitForFunction(()=>document.querySelector('#proposal-state').textContent==='PROPOSAL READY');
    await page.click('#approve');await settled(page);
    const stateBefore=await visibleState(page),forecastBefore=await encounter(page);
    await choose(page,file);await reviewed(page);
    assert.deepEqual(await visibleState(page),stateBefore);
    assert.deepEqual(await encounter(page),forecastBefore);
    await input(page,'encounter-time',300);
    assert.equal(await page.$eval('#scenario-review',el=>el.hidden),false);
    assert.equal(await page.$eval('#load-scenario',el=>el.disabled),false);
    assert.deepEqual(await visibleState(page),stateBefore);
    await page.click('#load-scenario');await settled(page);
    const view=await checkEncounter(page,doc);
    assert.deepEqual(view.first_options,['A1','B2','C3']);
    assert.equal(view.first,'A1');assert.equal(view.second,'B2');assert.equal(view.seconds,120);
    assert.equal((await visibleState(page)).audit,'');
    assert.equal((await visibleState(page)).readback_disabled,true);
    const resaved=JSON.parse((await saveFile(page)).text);assert.deepEqual(resaved,doc);
    await (await page.$('#encounter-explorer')).screenshot({path:path.join(out,'scenario-encounter-desktop.png')});
    await page.close();return{view,review_kept_prior_approval:true,apply_cleared_prior_approval:true,resaved_selected_aircraft_id:resaved.selected_aircraft_id};
  });
  await group('same-call-sign replacement recomputes the chosen pair; one-flight load hides and recovery restores forecasts',async()=>{
    const page=await newPage(),saved=JSON.parse((await saveFile(page)).text),first=threeFlight(saved);
    await open(page,'#encounter-explorer');
    await applyFile(page,await fixture('initial-pair.json',first));
    await page.select('#encounter-first','B2');await page.select('#encounter-second','C3');await input(page,'encounter-time',60);
    const before=await checkEncounter(page,first);
    const changed={...first,world:{...first.world,version:74,aircraft:[
      {...first.world.aircraft[2],x_nm:12,y_nm:4,altitude_ft:13000,climb_ft_min:-250},
      {...first.world.aircraft[0]},
      {...first.world.aircraft[1],x_nm:-7,y_nm:2,altitude_ft:9000,vy_nm_min:2}
    ]},selected_aircraft_id:'A1',policy:{...first.policy,min_horizontal_nm:6,horizon_min:8}};
    await applyFile(page,await fixture('same-identities-new-vectors.json',changed));
    const after=await checkEncounter(page,changed);
    assert.equal(after.first,'B2');assert.equal(after.second,'C3');assert.equal(after.seconds,60);
    assert.notEqual(after.horizontal,before.horizontal);assert.notEqual(after.vertical,before.vertical);
    const singleton={...changed,world:{...changed.world,version:75,aircraft:[changed.world.aircraft[0]]},selected_aircraft_id:'C3'};
    await applyFile(page,await fixture('single-flight.json',singleton));
    const one=await encounter(page);
    assert.equal(one.hidden,true);assert.ok(one.disabled.every(Boolean));assert.equal(one.first,'C3');assert.equal(one.second,'');
    assert.match(one.message,/Add a second flight/);assert.deepEqual((await visibleState(page)).world,singleton.world);
    await applyFile(page,await fixture('restored-multiple-flight.json',changed));
    const restored=await checkEncounter(page,changed);
    assert.equal(restored.first,'C3');assert.equal(restored.second,'A1');
    await page.close();return{before,after,singleton:one,restored};
  });
  await group('run and pause immediately update both scenario import and encounter controls on a phone',async()=>{
    const page=await newPage(320),saved=await saveFile(page);
    await open(page,'#encounter-explorer');await choose(page,saved.file);await reviewed(page);
    await page.click('#toggle-run');
    const moving=await page.evaluate(()=>({
      review_hidden:document.querySelector('#scenario-review').hidden,
      load_disabled:document.querySelector('#load-scenario').disabled,
      choose_disabled:document.querySelector('#choose-scenario').disabled,
      forecast_hidden:document.querySelector('#encounter-content').hidden,
      cursor_disabled:document.querySelector('#encounter-time').disabled
    }));
    assert.deepEqual(moving,{review_hidden:true,load_disabled:true,choose_disabled:true,forecast_hidden:true,cursor_disabled:true});
    await page.click('#toggle-run');
    const paused=await page.evaluate(()=>({
      load_disabled:document.querySelector('#load-scenario').disabled,
      choose_disabled:document.querySelector('#choose-scenario').disabled,
      forecast_hidden:document.querySelector('#encounter-content').hidden,
      cursor_disabled:document.querySelector('#encounter-time').disabled
    }));
    assert.deepEqual(paused,{load_disabled:true,choose_disabled:false,forecast_hidden:false,cursor_disabled:false});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await (await page.$('#encounter-explorer')).screenshot({path:path.join(out,'scenario-encounter-phone.png')});
    await page.close();return{moving,paused,phone_width:320,no_horizontal_overflow:true};
  });

  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const files=[];
  const tracked=execFileSync('git',['ls-files','-z'],{cwd:source}).toString().split('\0').filter(Boolean);
  for(const p of tracked){const data=await readFile(path.join(source,p));files.push({path:p,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex'),git_blob:createHash('sha1').update(Buffer.from('blob '+data.length+'\0')).update(data).digest('hex')});}
  await writeFile(path.join(out,'receipt.json'),JSON.stringify({schema:'towerops.scenario-encounter-composition-browser.v1',source_tree:execFileSync('git',['write-tree'],{cwd:source}).toString().trim(),source_parent:execFileSync('git',['rev-parse','HEAD'],{cwd:source}).toString().trim(),runtime:{node:process.version,browser:await browser.version(),puppeteer:require('puppeteer/package.json').version},groups,browser_errors:errors,external_requests:external,proxy_blocks:proxyBlocks,downloads:downloads.map(d=>({suggested_filename:d.suggestedFilename,guid:d.guid,state:progress.get(d.guid)})),requests,files},null,2)+'\n');
  console.log(JSON.stringify({passed:groups.length,total:groups.length,errors,external,out}));
}catch(error){
  await writeFile(path.join(out,'failure.json'),JSON.stringify({groups,errors,external,proxyBlocks,requests,error:String(error),stack:error.stack,pages:browser?await Promise.all((await browser.pages()).map(async p=>({url:p.url(),status:await p.evaluate(()=>({python:document.querySelector('#python-status')?.textContent,scenario:document.querySelector('#scenario-status')?.textContent,proposal:document.querySelector('#proposal-output')?.textContent})).catch(e=>String(e))}))):[]},null,2)+'\n');
  console.error(error);process.exitCode=1;
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));await new Promise(resolve=>denyProxy.close(resolve));}