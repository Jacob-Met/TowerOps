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
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(check,label,limit=15000){const begin=Date.now();while(Date.now()-begin<limit){if(await check())return;await delay(20);}throw new Error('Timed out: '+label);}
async function settled(page){await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));}
async function open(page,selector){if(!await page.$eval(selector,el=>el.open))await page.click(selector+' > summary');}
async function newPage(width=1380){const page=await browser.newPage();await page.setViewport({width,height:920});page.on('pageerror',e=>errors.push({group:activeGroup,error:String(e)}));await page.setRequestInterception(true);page.on('request',r=>{if(new URL(r.url()).origin===origin)r.continue();else{external.push({group:activeGroup,url:r.url()});r.abort();}});await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});await open(page,'.scenario-workbench');return page;}
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
  browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--disable-background-networking','--no-first-run'],userDataDir:path.join(out,'profile')});
  browserCDP=await browser.target().createCDPSession();
  await browserCDP.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(out,'downloads'),eventsEnabled:true});
  browserCDP.on('Browser.downloadWillBegin',event=>downloads.push(event));browserCDP.on('Browser.downloadProgress',event=>progress.set(event.guid,event.state));


  const page=await browser.newPage();await page.setViewport({width:1380,height:920});
  const clientLogs=[];page.on('console',m=>clientLogs.push(m.text()));page.on('pageerror',e=>clientLogs.push(String(e)));
  await page.setRequestInterception(true);page.on('request',r=>{if(new URL(r.url()).origin===origin)r.continue();else{external.push({url:r.url()});r.abort();}});
  page.on('workercreated',w=>clientLogs.push('worker-created '+w.url()));
  await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});
  await page.click('#run-planner');
  await delay(10000);
  const observed=await page.evaluate(()=>({python:document.querySelector('#python-status').textContent,proposal:document.querySelector('#proposal-output').textContent,run_disabled:document.querySelector('#run-planner').disabled,approve_disabled:document.querySelector('#approve').disabled}));
  await writeFile(path.join(out,'diagnosis.json'),JSON.stringify({observed,clientLogs,requests,external},null,2)+'\n');console.log(JSON.stringify({observed,clientLogs,paths:requests.map(x=>x.path),external}));
}catch(error){console.error(error);process.exitCode=1;}
finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
