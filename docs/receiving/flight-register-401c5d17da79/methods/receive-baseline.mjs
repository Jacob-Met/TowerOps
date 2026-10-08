// SPDX-License-Identifier: MIT
// Real Chromium baseline for the existing 60-flight input and deliberate selection route.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,lstat} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {openBrowser} from './cdp.mjs';
const root=resolve(fileURLToPath(new URL('..',import.meta.url))),inputsRaw=await readFile(join(root,'BASELINE-INPUTS.json')),inputs=JSON.parse(inputsRaw);
const out=join(root,'evidence','baseline-89529c5'),profile='/home/jacob/towerops-radar-profiles-401c5d17da79/independent-register-baseline-89529c5';
for(const p of [out,profile]){await assert.rejects(lstat(p),{code:'ENOENT'});}
await mkdir(out);
const sha=b=>createHash('sha256').update(b).digest('hex');
const report={schema:'towerops.flight-register-baseline.v1',parent:inputs.parent,tree:inputs.tree,started_at:new Date().toISOString(),source:inputs.source_root,inputs_sha256:sha(inputsRaw),method_sha256:sha(await readFile(fileURLToPath(import.meta.url))),checks:[],failure:null};
const check=(name,ok,details={})=>{report.checks.push({name,passed:!!ok,details});assert.ok(ok,name);};
async function pinSource(){const bad=[];for(const [p,h] of Object.entries(inputs.source_files))if(sha(await readFile(join(inputs.source_root,p)))!==h)bad.push(p);return bad;}
let server,browser;
try{
 assert.deepEqual(await pinSource(),[]);
 const {createServer}=await import(pathToFileURL(inputs.vite_module).href);
 server=await createServer({root:join(inputs.source_root,'web/airspace'),configFile:false,base:'./',cacheDir:join(root,'cache','baseline-89529c5'),server:{host:'127.0.0.1',port:0,fs:{allow:inputs.allowed_roots}}});
 await server.listen();browser=await openBrowser({profile,evidence:out,width:1440,height:1000});const c=browser.cdp;
 report.browser=browser.version;
 await c.send('Page.addScriptToEvaluateOnNewDocument',{source:'window.__registerBaselineRequests=[];const OriginalWorker=window.Worker;window.Worker=class extends OriginalWorker {postMessage(value,...rest){window.__registerBaselineRequests.push(structuredClone(value));return super.postMessage(value,...rest);}};'});
 await c.send('Page.navigate',{url:'http://127.0.0.1:'+server.httpServer.address().port+'/'});
 await c.wait('document.querySelector("#world-json")?.value?.includes("aircraft")');
 const initial=JSON.parse(await c.evaluate('document.querySelector("#world-json").value'));
 const aircraft=Array.from({length:60},(_,index)=>{const n=(index*17)%60;return {aircraft_id:['NTH_','EST_','STH_'][n%3]+String(n).padStart(2,'0'),x_nm:n*8,y_nm:(n%3)*14,altitude_ft:10000+(n%5)*1000,vx_nm_min:(n%3)*0.1,vy_nm_min:0.2,climb_ft_min:(n%3-1)*60};});
 const world={version:29,observed_at:initial.observed_at+60,aircraft};report.fixture=world;
 await writeFile(join(out,'world-60.json'),JSON.stringify(world,null,2)+'\n');
 await c.click('.state-workbench > summary');await c.fill('#world-json',JSON.stringify(world));await c.click('#load-world');
 await c.wait('document.querySelector("#flight-count").textContent==="60 FLIGHTS" && document.querySelector("#audit-status").textContent==="0 EVENTS / VALID"');
 await c.click('.telemetry-wrap > summary');
 const rows=await c.evaluate('[...document.querySelectorAll("#flight-list button")].map(e=>e.textContent)');
 check('Normal JSON input admits all 60 aircraft in the existing scenario order',JSON.stringify(rows)===JSON.stringify(aircraft.map(a=>a.aircraft_id)),{count:rows.length});
 const before=await c.evaluate('({clock:document.querySelector("#sim-clock").textContent,world:document.querySelector("#world-json").value,audit:document.querySelector("#audit-status").textContent,requests:window.__registerBaselineRequests})');
 await c.click('#flight-list .flight-row:nth-child(58) button');
 await c.wait('document.querySelector("#edit-selected-track").textContent==='+JSON.stringify('Edit '+aircraft[57].aircraft_id));
 check('Existing explicit row selection chooses the requested flight',await c.evaluate('document.querySelector("#flight-list .selected button").textContent')===aircraft[57].aircraft_id);
 const after=await c.evaluate('({clock:document.querySelector("#sim-clock").textContent,world:document.querySelector("#world-json").value,audit:document.querySelector("#audit-status").textContent,requests:window.__registerBaselineRequests})');
 check('Existing selection preserves world, clock, audit and native worker traffic',JSON.stringify(after)===JSON.stringify(before));
 report.feature_absence=await c.evaluate('({query:!!document.querySelector("#flight-filter"),order:!!document.querySelector("#flight-order"),matches:!!document.querySelector("#flight-matches")})');
 check('Current source has no register search or order controls',Object.values(report.feature_absence).every(x=>!x));
 await c.evaluate('document.querySelector(".telemetry-wrap").scrollIntoView({block:"start"})');
 await c.screenshot(join(out,'existing-60-flight-register.png'));
 check('Baseline emits no page errors or external requests',browser.errors.length===0&&browser.blocked.length===0,{pageErrors:browser.errors,externalRequests:browser.blocked});
}catch(e){report.failure={name:e.name,message:e.message,stack:e.stack};}
finally{
 report.source_changed=await pinSource();
 report.borrowed_changed=[];
 for(const [p,h] of Object.entries(inputs.borrowed_files))if(sha(await readFile(p))!==h)report.borrowed_changed.push(p);
 if(browser){report.page_errors=browser.errors;report.external_requests=browser.blocked;await browser.close();}
 if(server)await server.close();
 report.completed_at=new Date().toISOString();report.passed=report.checks.filter(c=>c.passed).length;report.failed=report.checks.filter(c=>!c.passed).length;report.status=!report.failure&&!report.source_changed.length&&!report.borrowed_changed.length?'passed':'failed';
 await writeFile(join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,passed:report.passed,failed:report.failed,source_changed:report.source_changed,borrowed_changed:report.borrowed_changed,failure:report.failure,receipt:join(out,'receipt.json')},null,2));
 if(report.status!=='passed')process.exitCode=1;
}