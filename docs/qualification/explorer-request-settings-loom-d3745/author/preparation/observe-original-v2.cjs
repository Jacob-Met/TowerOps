"use strict";
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const [root,fixturePath,replyPath]=process.argv.slice(2);
const app=fs.readFileSync(path.join(root,'web/app.js'),'utf8'),html=fs.readFileSync(path.join(root,'web/index.html'),'utf8');
const fixture=fs.readFileSync(fixturePath,'utf8'),value=JSON.parse(fixture),reply=JSON.parse(fs.readFileSync(replyPath,'utf8'));
const nodes=new Map(),calls=[];
function node(id){if(!nodes.has(id))nodes.set(id,{id,textContent:'',value:'',checked:false,disabled:false,hidden:false,files:[],dataset:{},children:[],listeners:{},selectedOptions:[{dataset:{description:'original choice'}}],addEventListener(k,f){this.listeners[k]=f;},append(...x){this.children.push(...x);},replaceChildren(...x){this.children=x;},setAttribute(){}});return nodes.get(id);}
const context=vm.createContext({document:{getElementById:node,createElement:()=>node(Symbol()),createElementNS:()=>node(Symbol()),createTextNode:text=>({textContent:text})},console,setTimeout,URL,Blob,fetch:async(url,options)=>{calls.push({url,body:options && options.body !== undefined ? JSON.parse(options.body) : null});if(url==='/api/scenarios')return {ok:true,json:async()=>({scenarios:[{id:'approved',label:'Approved',description:'original choice'},{id:'missing_ack',label:value.label,description:value.description}]})};assert.equal(url,'/api/replay');assert.deepEqual(JSON.parse(options.body),value);return {ok:true,json:async()=>reply};}});
(async()=>{
 vm.runInContext(app,context);await new Promise(setImmediate);
 node('scenario').value='approved';node('approval').checked=false;node('ack').checked=false;
 vm.runInContext('current={retained:"original displayed result"}',context);
 const before={scenario:node('scenario').value,approval:node('approval').checked,ack:node('ack').checked,main_status:node('status').textContent,current:vm.runInContext('JSON.stringify(current)',context)};
 node('replay-file').files=[{name:'missing-ack.json',size:Buffer.byteLength(fixture),text:async()=>fixture}];await node('replay-file').listeners.change();
 const after={scenario:node('scenario').value,approval:node('approval').checked,ack:node('ack').checked,main_status:node('status').textContent,current:vm.runInContext('JSON.stringify(current)',context)};
 const checks=[['original native replay matches',reply.matches,true],['request switch differs from effective fixture',value.request.include_ack===true&&value.fixtures.ack===null,true],['ordinary form/display state preserved',JSON.stringify(after),JSON.stringify(before)],['original has no settings button',/id=["']replay-use-settings["']/.test(html),false],['original has no registered settings action',nodes.has('replay-use-settings'),false],['only catalog and replay requested',calls.map(x=>x.url),['/api/scenarios','/api/replay']],['ordinary match status present',node('replay-status').textContent.startsWith('Replay MATCH:'),true]].map(([name,actual,expected])=>({name,actual,expected,pass:JSON.stringify(actual)===JSON.stringify(expected)}));
 const out={schema:'hamon.loom.towerops-settings.original-observation.v2',scope:'Controlled Node DOM/fetch observation of unchanged browser script, using exact saved fixture and complete real native CLI replay reply; not an actual browser/HTTP course.',candidate_implemented:false,accepted:checks.every(x=>x.pass),checks,before,after,calls,replay_status:node('replay-status').textContent};
 process.stdout.write(JSON.stringify(out,null,2)+'\n');if(!out.accepted)process.exitCode=1;
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
