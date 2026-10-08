#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),puppeteer=require('puppeteer');
import fs from 'node:fs';
import {readFile,writeFile,mkdir,mkdtemp,rm} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn,execFileSync} from 'node:child_process';
import {join,resolve} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';

const args=process.argv.slice(2);
const option=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const root=resolve(option('--root',process.cwd()));
const qa=resolve(option('--qa',root+'-qa'));
const output=resolve(option('--output',join(qa,'browser-baseline')));
const toolchain=resolve(option('--toolchain',join(root,'web/airspace/node_modules')));
const web=join(root,'web/airspace'), executable=option('--browser','/snap/bin/chromium');
await mkdir(output,{recursive:true});
const sha=b=>createHash('sha256').update(b).digest('hex');
const sourceFiles=execFileSync('git',['-C',root,'ls-files','-z'],{encoding:'utf8'}).split('\0').filter(Boolean);
const snapshot=()=>Object.fromEntries(sourceFiles.map(p=>[p,sha(fs.readFileSync(join(root,p)))]));
const sourceBefore=snapshot();
const lock=await readFile(join(web,'package-lock.json'));
assert.equal(sha(lock),sha(await readFile(join(toolchain,'../package-lock.json'))),'borrowed dependency lock is the exact project lock');
const expectedVersions={typescript:'5.7.3',vite:'8.3.3',vitest:'4.1.11',pyodide:'0.27.7'};
const dependencies={};
for(const [name,version] of Object.entries(expectedVersions)){
 const file=join(toolchain,name,'package.json'), bytes=await readFile(file);
 assert.equal(JSON.parse(bytes).version,version);
 dependencies[name]={version,sha256:sha(bytes)};
}
const ownModules=join(web,'node_modules');
if(!fs.existsSync(ownModules))fs.symlinkSync(toolchain,ownModules,'dir');
else assert.equal(fs.realpathSync(ownModules),fs.realpathSync(toolchain),'only own dependency link may exist');
const {createServer}=await import(pathToFileURL(join(toolchain,'vite/dist/node/index.js')));
const server=await createServer({root:web,configFile:false,cacheDir:join(qa,'vite-cache'),logLevel:'error',optimizeDeps:{noDiscovery:true,include:[]},server:{host:'127.0.0.1',port:0,fs:{allow:[root,toolchain]}}});
await server.listen();
const base='http://127.0.0.1:'+server.httpServer.address().port;
const profile=await mkdtemp(join(output,'profile-'));
const report={kind:'raw-world-json-draft-browser-receiving',receiverSha256:sha(await readFile(fileURLToPath(import.meta.url))),node:process.version,startedAt:new Date().toISOString(),root,baseCommit:execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),sourceBefore,toolchain,dependencyLockSha256:sha(lock),dependencies,serving:'Exact source through existing pinned Vite API; configFile:false, own cache only',checks:[],observations:[],pageErrors:[]};
let browser,browserSession,pageSession,browserLog='';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function waitFor(check,label){let last;for(let n=0;n<200;n++){try{if(await check())return;}catch(e){last=e;}await sleep(100);}throw Error('Timed out: '+label+(last?' '+last.message:''));}
function command(method,params={},scoped=true){return (scoped?pageSession:browserSession).send(method,params);}
async function evaluate(expression){const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);return r.result.value;}
async function click(selector){
 const point=await evaluate('(()=>{const n=document.querySelector('+JSON.stringify(selector)+');if(!n)throw Error("Missing element");n.scrollIntoView({block:"center"});const r=n.getBoundingClientRect();if(!r.width||!r.height)throw Error("Hidden element");return {x:r.x+r.width/2,y:r.y+r.height/2}})()');
 await command('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
 await command('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...point});
 await command('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...point});
}
async function press(key,code,modifiers=0){for(const type of ['keyDown','keyUp'])await command('Input.dispatchKeyEvent',{type,key,code:key,windowsVirtualKeyCode:code,nativeVirtualKeyCode:code,modifiers});}
async function edit(text){await click('#world-json');await command('Input.dispatchKeyEvent',{type:'rawKeyDown',key:'a',code:'KeyA',windowsVirtualKeyCode:65,modifiers:process.platform==='darwin'?4:2,commands:['selectAll']});await command('Input.dispatchKeyEvent',{type:'keyUp',key:'a',code:'KeyA',windowsVirtualKeyCode:65,modifiers:process.platform==='darwin'?4:2});await command('Input.insertText',{text});assert.equal(await evaluate('document.querySelector("#world-json").value'),text,'actual typing reaches editor');}
const editor=()=>evaluate('document.querySelector("#world-json").value');
const feedback=()=>evaluate('document.querySelector("#world-json-feedback").textContent');
const register=()=>evaluate('[...document.querySelectorAll("#flight-list button")].map(n=>n.textContent)');
async function navigate(){
 await command('Emulation.setDeviceMetricsOverride',{width:1280,height:950,deviceScaleFactor:1,mobile:false});
 await command('Page.navigate',{url:base+'/'});
 await waitFor(()=>evaluate('document.readyState==="complete" && !!document.querySelector("#world-json")?.value && document.querySelector("#flight-list")?.children.length>0'),'actual workbench ready');
 await click('.state-workbench > summary');
}
async function check(name,fn){try{await fn();report.checks.push({name,status:'passed'});console.log('PASS '+name);}catch(e){report.checks.push({name,status:'failed',error:e.message});console.log('FAIL '+name+': '+e.message);}}
try{
 browser=await puppeteer.launch({executablePath:executable,headless:true,userDataDir:profile,args:['--no-sandbox','--disable-gpu','--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run','--no-default-browser-check']});
 browserSession=await browser.target().createCDPSession();
 report.browser=await command('Browser.getVersion',{},false);
 report.transport={kind:'Puppeteer25.12 CDP sessions',originalReceiverSha256:"441e5b9ef989ce9e301ae09c21441dcba41bcb0188b85319dbbd1434fd58849f",change:'Replace only handrolled WebSocket/session launch and cleanup transport; retain pinned Vite serving, native CDP input and all nine predicate bodies.'};
 const page=await browser.newPage();
 pageSession=await page.createCDPSession();
 pageSession.on('Runtime.exceptionThrown',params=>report.pageErrors.push(params.exceptionDetails.exception?.description??params.exceptionDetails.text));
 await command('Page.enable');await command('Runtime.enable');
 await check('untouched editor follows the live world',async()=>{
  await navigate();const initial=JSON.parse(await editor());assert.deepEqual(initial.aircraft.map(a=>a.aircraft_id),await register());
  await click('#toggle-run');await sleep(550);await click('#toggle-run');await command('Emulation.setDeviceMetricsOverride',{width:1240,height:950,deviceScaleFactor:1,mobile:false});await sleep(150);
  assert.ok(JSON.parse(await editor()).version>initial.version);report.observations.push({name:'untouched-world-sync',beforeVersion:initial.version,afterVersion:JSON.parse(await editor()).version});
 });
 await check('paused flight selection preserves an authored valid JSON draft',async()=>{
  await navigate();const live=JSON.parse(await editor()),draft=structuredClone(live);draft.aircraft[0].aircraft_id='DRAFT101';draft.aircraft[0].x_nm=42;const text=JSON.stringify(draft,null,2);
  await edit(text);assert.deepEqual(await register(),live.aircraft.map(a=>a.aircraft_id));
  await click('.telemetry-wrap > summary');await click('#flight-list button');await sleep(150);
  const after=await editor();report.observations.push({name:'paused-selection-draft',draftSha256:sha(Buffer.from(text)),afterSha256:sha(Buffer.from(after)),beforeCallsign:draft.aircraft[0].aircraft_id,afterCallsign:JSON.parse(after).aircraft[0].aircraft_id});
  assert.equal(after,text,'flight selection must not replace unsubmitted JSON');
 });
 await check('loading after a focus-changing render applies the exact authored world',async()=>{
  await navigate();const draft=JSON.parse(await editor());draft.aircraft[0].aircraft_id='DRAFT202';draft.aircraft[0].x_nm=-37;const text=JSON.stringify(draft,null,2);
  await edit(text);await click('.telemetry-wrap > summary');await click('#flight-list button');await sleep(100);await click('#load-world');await sleep(150);
  const actual=await register();report.observations.push({name:'loaded-world-identity',expected:'DRAFT202',actual,feedback:await feedback()});assert.ok(actual.includes('DRAFT202'),'the explicitly loaded authored callsign must appear');
 });
 await check('resizing preserves an unfinished invalid JSON draft',async()=>{
  await navigate();const text='{\n  "version": ';await edit(text);await press('Tab',9);assert.notEqual(await evaluate('document.activeElement.id'),'world-json');
  await command('Emulation.setDeviceMetricsOverride',{width:1090,height:900,deviceScaleFactor:1,mobile:false});await sleep(150);const actual=await editor();report.observations.push({name:'resize-partial-draft',expected:text,actualPrefix:actual.slice(0,75)});assert.equal(actual,text,'layout changes must not discard partial editing');
 });
 await check('moving traffic preserves the blurred draft while the simulation continues',async()=>{
  await navigate();await click('#toggle-run');await edit('{"still editing": ');const beforeClock=await evaluate('document.querySelector("#sim-clock").textContent');await sleep(350);assert.equal(await editor(),'{"still editing": ','focused editing is a baseline control');
  await press('Tab',9);await sleep(750);const afterClock=await evaluate('document.querySelector("#sim-clock").textContent'),actual=await editor();report.observations.push({name:'running-blurred-draft',beforeClock,afterClock,actualPrefix:actual.slice(0,75)});assert.notEqual(afterClock,beforeClock,'draft protection must not freeze live traffic');assert.equal(actual,'{"still editing": ','running renders must preserve blurred draft');
 });
 await check('a rejected load keeps invalid text through a later render',async()=>{
  await navigate();const text='{"version":-1,"aircraft":[]}';await edit(text);await click('#load-world');assert.match(await feedback(),/NOT LOADED/);
  await command('Emulation.setDeviceMetricsOverride',{width:1050,height:900,deviceScaleFactor:1,mobile:false});await sleep(150);assert.equal(await editor(),text,'failed validation must leave the exact draft available to correct');
 });
 await check('explicit Export live world replaces the draft and restores live synchronization',async()=>{
  await navigate();const initial=JSON.parse(await editor());await edit('{"unfinished":');await click('#export-world');assert.deepEqual(JSON.parse(await editor()),initial);assert.match(await feedback(),/exported/i);
  await click('#toggle-run');await sleep(550);await click('#toggle-run');await command('Emulation.setDeviceMetricsOverride',{width:1180,height:950,deviceScaleFactor:1,mobile:false});await sleep(150);assert.ok(JSON.parse(await editor()).version>initial.version);
 });
 await check('valid direct load normalizes successfully and restores live synchronization',async()=>{
  await navigate();const draft=JSON.parse(await editor());draft.aircraft[0].aircraft_id='DRAFT303';const text=JSON.stringify(draft);await edit(text);await click('#load-world');assert.match(await feedback(),/Loaded/);assert.ok((await register()).includes('DRAFT303'));
  await click('#toggle-run');await sleep(550);await click('#toggle-run');await command('Emulation.setDeviceMetricsOverride',{width:1140,height:950,deviceScaleFactor:1,mobile:false});await sleep(150);const current=JSON.parse(await editor());assert.ok(current.version>draft.version);assert.equal(current.aircraft[0].aircraft_id,'DRAFT303');
 });
 await check('all observed browser paths are free from JavaScript exceptions',async()=>assert.deepEqual(report.pageErrors,[]));
}catch(e){report.fatal=e.stack;report.browserLog=browserLog;console.log('FATAL '+e.stack);}
finally{
 report.sourceAfter=snapshot();report.sourceChanged=Object.keys(sourceBefore).filter(p=>sourceBefore[p]!==report.sourceAfter[p]);
 try{
  if(browser)await browser.close();
  await server.close();
  await rm(profile,{recursive:true,force:true,maxRetries:8,retryDelay:150});
  report.cleanup={status:'passed',profileRemoved:!fs.existsSync(profile)};
 }catch(e){report.cleanup={status:'failed',error:e.stack};console.log('CLEANUP ERROR '+e.stack);}
 report.finishedAt=new Date().toISOString();report.status=!report.fatal&&report.checks.every(x=>x.status==='passed')&&!report.sourceChanged.length&&report.cleanup.status==='passed'?'passed':'failed';
 await writeFile(join(output,'browser-report.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,passed:report.checks.filter(x=>x.status==='passed').length,failed:report.checks.filter(x=>x.status==='failed').length,pageErrors:report.pageErrors.length,sourceChanged:report.sourceChanged,cleanup:report.cleanup,report:join(output,'browser-report.json')}));
 if(report.status!=='passed')process.exitCode=1;
}
