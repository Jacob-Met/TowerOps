// SPDX-License-Identifier: MIT
// Receiver calibration on a native HTML control; no TowerOps source is loaded.
import { openBrowser } from './cdp.mjs';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const root="/home/jacob/.commander-tp-1/hamon-work/estate-401c5d17da79/towerops-radar-independent";
const output=root+'/evidence/keyboard-native-control-v1';await mkdir(output);
const browser=await openBrowser({profile:'/home/jacob/towerops-radar-profiles-401c5d17da79/independent-keyboard-native-control-v1',evidence:output,width:700,height:500});
const cdp=browser.cdp;const report={schema:'towerops.receiver.native-keyboard-calibration.v1',browser:browser.version,method_sha256:createHash('sha256').update(await readFile(new URL(import.meta.url))).digest('hex'),observations:[]};
try{
 const html='<button id="button" type="button">Native button</button><script>window.clicks=0;window.events=[];for(const type of ["keydown","keypress","keyup","click"]){document.addEventListener(type,e=>{if(type==="click")window.clicks++;window.events.push({type,key:e.key??null,code:e.code??null,isTrusted:e.isTrusted,defaultPrevented:e.defaultPrevented})})}</script>';
 await cdp.send('Page.navigate',{url:'data:text/html,'+encodeURIComponent(html)});await cdp.wait('!!document.querySelector("#button")');await cdp.click('#button');
 for(const row of [{name:'Enter without text',key:'Enter',code:'Enter',n:13,text:null},{name:'Enter with carriage-return text',key:'Enter',code:'Enter',n:13,text:'\r'},{name:'Space without text',key:' ',code:'Space',n:32,text:null},{name:'Space with text',key:' ',code:'Space',n:32,text:' '}]){
  await cdp.evaluate('window.clicks=0;window.events=[];document.querySelector("#button").focus()');
  for(const type of ['keyDown','keyUp']){
   const params={type,key:row.key,code:row.code,windowsVirtualKeyCode:row.n,nativeVirtualKeyCode:row.n,modifiers:0};
   if(type==='keyDown'&&row.text!==null){params.text=row.text;params.unmodifiedText=row.text;}
   await cdp.send('Input.dispatchKeyEvent',params);
  }
  await cdp.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
  report.observations.push({...row,...await cdp.evaluate('({clicks:window.clicks,events:window.events,active:document.activeElement.id})')});
 }
}catch(e){report.failure=String(e.stack??e);}finally{await browser.close();report.errors=browser.errors;report.blocked=browser.blocked;const raw=JSON.stringify(report,null,2)+'\n';await writeFile(output+'/receipt.json',raw);console.log(raw);if(report.failure)process.exitCode=1;}
