import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';

const require=createRequire(import.meta.url),puppeteer=require('puppeteer');
const root=path.dirname(new URL(import.meta.url).pathname);
const source=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
const inputs=JSON.parse(await readFile(path.join(root,'input-receipt.json'),'utf8'));
const sourceManifest=JSON.parse(await readFile(path.join(root,'source-manifest.json'),'utf8'));
const buildManifest=JSON.parse(await readFile(path.join(root,'dist-manifest.json'),'utf8'));
assert.equal(source,inputs.source);
await mkdir(out,{recursive:false});
await mkdir(path.join(out,'downloads'));
await mkdir(path.join(out,'fixtures'));
const dist=path.join(source,'web/airspace/dist'),requests=[],errors=[],external=[],groups=[],downloads=[],progress=new Map(),proxyBlocks=[];
const sha=body=>createHash('sha256').update(body).digest('hex');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let activeGroup='',browser,browserVersion='unavailable';
async function verifyInputs(){
  let sourceCount=0,buildCount=0;
  for(const row of sourceManifest.source_files){
    const body=await readFile(path.join(source,row.path));
    assert.equal(body.length,row.bytes,'source length '+row.path);
    assert.equal(sha(body),row.sha256,'source digest '+row.path);sourceCount++;
  }
  for(const row of buildManifest.files){
    const body=await readFile(path.join(dist,row.path));
    assert.equal(body.length,row.bytes,'build length '+row.path);
    assert.equal(sha(body),row.sha256,'build digest '+row.path);buildCount++;
  }
  return {source_files:sourceCount,build_files:buildCount,main_sha256:sha(await readFile(path.join(source,'web/airspace/src/main.ts')))};
}
const before=await verifyInputs();
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=new URL(req.url,'http://localhost').pathname;
    const relative=decodeURIComponent(pathname.replace(/^\/TowerOps\/airspace\/?/,''));
    const target=path.resolve(dist,relative||'index.html');
    if(target!==dist&&!target.startsWith(dist+path.sep))throw Error('Outside frozen fixture');
    const file=(await stat(target)).isDirectory()?path.join(target,'index.html'):target;
    const body=await readFile(file),types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml'};
    requests.push({group:activeGroup,path:pathname,status:200,sha256:sha(body)});
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});res.end(body);
  }catch(error){requests.push({group:activeGroup,path:req.url,status:404,error:String(error)});res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const proxy=http.createServer((req,res)=>{
  proxyBlocks.push({method:req.method,url:req.url});
  res.writeHead(403);res.end('Isolated receiving: external requests denied');
});
proxy.on('connect',(req,socket)=>{
  socket.on('error',error=>proxyBlocks.push({method:'SOCKET_ERROR',code:error.code}));
  proxyBlocks.push({method:'CONNECT',url:req.url});
  socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');
});
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
async function until(fn,label){
  for(let i=0;i<750;i++){if(await fn())return;await sleep(20);}
  throw Error('Timed out: '+label);
}
async function settled(page){
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
}
async function newPage(){
  const page=await browser.newPage();await page.setViewport({width:1320,height:940});
  page.on('pageerror',error=>errors.push({group:activeGroup,error:String(error)}));
  page.on('request',request=>{
    const url=request.url();
    if(!url.startsWith('blob:')&&!url.startsWith('data:')&&new URL(url).origin!==origin)external.push({group:activeGroup,url});
  });
  await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});
  await page.waitForFunction(()=>!!document.querySelector('#world-json')?.value);
  for(const selector of ['.state-workbench','.scenario-workbench']){
    if(!await page.$eval(selector,node=>node.open))await page.click(selector+' > summary');
  }
  return page;
}
const draft=page=>page.$eval('#world-json',node=>node.value);
const feedback=page=>page.$eval('#world-json-feedback',node=>node.textContent);
const register=page=>page.$$eval('#flight-list button',nodes=>nodes.map(node=>node.textContent));
const reviewState=page=>page.evaluate(()=>({
  visible:!document.querySelector('#scenario-review').hidden,
  apply_enabled:!document.querySelector('#load-scenario').disabled,
  status:document.querySelector('#scenario-status').textContent,
  summary:document.querySelector('#scenario-summary').textContent,
}));
async function typeDraft(page,text){
  await page.click('#world-json');
  const selection=await page.$eval('#world-json',node=>{
    node.select();return {start:node.selectionStart,end:node.selectionEnd,length:node.value.length};
  });
  assert.equal(selection.start,0);assert.equal(selection.end,selection.length);
  await page.keyboard.sendCharacter(text);await settled(page);
  assert.equal(await draft(page),text);
}
async function save(page,label){
  const first=downloads.length;await page.click('#save-scenario');
  await until(()=>downloads.length>first,'real scenario download starts');
  const item=downloads[first];await until(()=>progress.get(item.guid)==='completed','real scenario download completes');
  const file=path.join(out,'downloads',item.guid),text=await readFile(file,'utf8');
  item.receiving_label=label;
  return {file,text,document:JSON.parse(text),sha256:sha(text),suggested:item.suggestedFilename};
}
async function choose(page,file){
  const promise=page.waitForFileChooser();await page.click('#choose-scenario');
  await(await promise).accept([file]);
}
async function reviewed(page){
  await page.waitForFunction(()=>!document.querySelector('#scenario-review').hidden&&!document.querySelector('#load-scenario').disabled);
  await settled(page);
}
async function targetFrom(saved,name){
  const initial=saved.document;
  const document={...initial,world:{version:73,observed_at:1002,aircraft:[
    {aircraft_id:'FILE601',x_nm:0,y_nm:0,altitude_ft:11000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0},
    {aircraft_id:'FILE602',x_nm:9,y_nm:0,altitude_ft:11000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0}]},
    policy:{...initial.policy,min_horizontal_nm:7,min_vertical_ft:1800,horizon_min:9},
    now:1002,time_scale:2.5,selected_aircraft_id:'FILE602'};
  const text=JSON.stringify(document),file=path.join(out,'fixtures',name+'.json');
  await writeFile(file,text);return {document,file,text,sha256:sha(text)};
}
async function group(name,fn){
  activeGroup=name;const start=Date.now();
  try{groups.push({name,passed:true,seconds:(Date.now()-start)/1000,...await fn()});}
  catch(error){groups.push({name,passed:false,seconds:(Date.now()-start)/1000,error:String(error),stack:error.stack});}
  groups.at(-1).seconds=(Date.now()-start)/1000;
  console.log(JSON.stringify(groups.at(-1)));
}

try{
  browser=await puppeteer.launch({
    executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless:true,userDataDir:path.join(out,'profile'),
    args:['--disable-background-networking','--no-first-run','--disable-quic',
      '--proxy-server=http://127.0.0.1:'+proxy.address().port]
  });
  browserVersion=await browser.version();
  const cdp=await browser.target().createCDPSession();
  await cdp.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(out,'downloads'),eventsEnabled:true});
  cdp.on('Browser.downloadWillBegin',item=>downloads.push(item));
  cdp.on('Browser.downloadProgress',item=>progress.set(item.guid,item.state));

  await group('valid raw world authored after review remains separate; explicit Export preserves a pending review',async()=>{
    const page=await newPage(),initial=await save(page,'first live scenario A'),target=await targetFrom(initial,'three-world-target');
    const rawWorld={version:101,observed_at:1004,aircraft:[
      {aircraft_id:'DRAFT701',x_nm:-7,y_nm:2,altitude_ft:13000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0},
      {aircraft_id:'DRAFT702',x_nm:18,y_nm:2,altitude_ft:13000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0}]};
    const rawText='\n'+JSON.stringify(rawWorld,null,2)+'\n';
    await writeFile(path.join(out,'fixtures','valid-third-world-raw.json'),rawText);
    await choose(page,target.file);await reviewed(page);
    const reviewBeforeDraft=await reviewState(page);
    await typeDraft(page,rawText);
    const reviewAfterDraft=await reviewState(page);
    assert.equal(reviewAfterDraft.visible,true);assert.equal(reviewAfterDraft.apply_enabled,true);
    assert.equal(reviewAfterDraft.summary,reviewBeforeDraft.summary);
    const stillInitial=await save(page,'live A after valid C authored during B review');
    assert.deepEqual(stillInitial.document,initial.document);
    assert.equal(await draft(page),rawText);
    await page.click('#load-scenario');await settled(page);
    assert.equal(await draft(page),rawText);
    assert.deepEqual(await register(page),target.document.world.aircraft.map(a=>a.aircraft_id));
    const retainedFeedback=await feedback(page);
    assert.match(retainedFeedback,/^Loaded scenario with 2 aircraft at version 73\./);
    assert.match(retainedFeedback,/Your raw JSON draft is still kept\. Use Export live world to replace it\./);
    const restoredTarget=await save(page,'live B after Apply with C kept');
    assert.deepEqual(restoredTarget.document,target.document);
    assert.equal(await draft(page),rawText);
    await (await page.$('.state-workbench')).screenshot({path:path.join(out,'valid-draft-after-apply.png')});
    await choose(page,initial.file);await reviewed(page);
    const reviewBeforeExport=await reviewState(page);
    await page.click('#export-world');await settled(page);
    const reviewAfterExport=await reviewState(page);
    assert.equal(reviewAfterExport.visible,true);assert.equal(reviewAfterExport.apply_enabled,true);
    assert.equal(reviewAfterExport.summary,reviewBeforeExport.summary);
    assert.deepEqual(JSON.parse(await draft(page)),target.document.world);
    assert.match(await feedback(page),/^Live world exported\./);
    await page.click('#load-scenario');await settled(page);
    const restoredInitial=await save(page,'live A after pending review survives Export');
    assert.deepEqual(restoredInitial.document,initial.document);
    assert.deepEqual(JSON.parse(await draft(page)),initial.document.world);
    const pristineFeedback=await feedback(page);
    assert.equal(pristineFeedback,'Loaded scenario with '+initial.document.world.aircraft.length+' aircraft at version '+initial.document.world.version+'.');
    await page.close();
    return {
      independent_order:'Choose B, author valid C, Save A, Apply B, review A, Export B, Apply A',
      raw_draft_sha256:sha(rawText),raw_draft_world:rawWorld,
      initial:initial.document,target:target.document,
      download_sha256:{initial:initial.sha256,still_initial:stillInitial.sha256,target:restoredTarget.sha256,restored_initial:restoredInitial.sha256},
      review_after_draft:reviewAfterDraft,review_after_export:reviewAfterExport,
      retained_feedback:retainedFeedback,pristine_feedback:pristineFeedback,
      raw_world_never_implicitly_loaded:true
    };
  });

  await group('same-value successful raw Load invalidates an in-flight genuine File.text completion',async()=>{
    const page=await newPage(),first=await save(page,'second control original live scenario');
    await typeDraft(page,JSON.stringify(first.document.world));
    await page.click('#load-world');await settled(page);
    assert.match(await feedback(page),/^Loaded /);
    const initial=await save(page,'normalized same-value raw-load basis A'),target=await targetFrom(initial,'pending-native-read-target');
    await page.evaluate(filename=>{
      const original=File.prototype.text;
      const gate={state:'installed',filename,actualText:null,release:null,restore:()=>{File.prototype.text=original;}};
      globalThis.__independentRawReadGate=gate;
      File.prototype.text=function(...args){
        const nativeResult=original.apply(this,args);
        if(this.name!==filename)return nativeResult;
        gate.file={name:this.name,size:this.size,type:this.type,lastModified:this.lastModified};
        return nativeResult.then(text=>{
          gate.actualText=text;gate.state='held-native-result';
          return new Promise(resolve=>{gate.release=()=>{gate.state='released';resolve(text);};});
        });
      };
    },path.basename(target.file));
    await choose(page,target.file);
    await page.waitForFunction(()=>globalThis.__independentRawReadGate?.state==='held-native-result');
    const actualRead=await page.evaluate(()=>({
      state:globalThis.__independentRawReadGate.state,file:globalThis.__independentRawReadGate.file,
      text:globalThis.__independentRawReadGate.actualText
    }));
    assert.equal(actualRead.text,target.text);assert.equal(actualRead.file.size,Buffer.byteLength(target.text));
    const beforeLoad=await reviewState(page);
    assert.equal(beforeLoad.visible,false);assert.equal(beforeLoad.apply_enabled,false);assert.match(beforeLoad.status,/Reading/);
    const equivalentText='\n'+JSON.stringify(initial.document.world)+'\n';
    await typeDraft(page,equivalentText);
    const afterTyping=await reviewState(page);
    assert.match(afterTyping.status,/Reading/);
    assert.equal(await page.evaluate(()=>globalThis.__independentRawReadGate.state),'held-native-result');
    await page.click('#load-world');await settled(page);
    assert.match(await feedback(page),/^Loaded /);
    const afterLoad=await reviewState(page);
    assert.equal(afterLoad.visible,false);assert.equal(afterLoad.apply_enabled,false);
    assert.match(afterLoad.status,/simulation changed/);
    await page.evaluate(()=>{
      const gate=globalThis.__independentRawReadGate;
      if(gate.state!=='held-native-result'||!gate.release)throw Error('Native File.text result is not held');
      gate.release();gate.restore();
    });
    await settled(page);
    const afterRelease=await reviewState(page);
    assert.equal(afterRelease.visible,false);assert.equal(afterRelease.apply_enabled,false);
    assert.equal(afterRelease.status,afterLoad.status);
    assert.equal(await page.evaluate(()=>globalThis.__independentRawReadGate.state),'released');
    assert.deepEqual(await register(page),initial.document.world.aircraft.map(a=>a.aircraft_id));
    const final=await save(page,'same live A after stale native completion');
    assert.deepEqual(final.document,initial.document);
    assert.equal(await draft(page),JSON.stringify(initial.document.world,null,2));
    await (await page.$('.scenario-workbench')).screenshot({path:path.join(out,'stale-native-read-refused.png')});
    await page.close();
    return {
      independent_order:'Begin genuine B read, hold its resolved text, type same-value A, Load A, release B completion, Save A',
      genuine_native_read:{file:actualRead.file,sha256:sha(actualRead.text),same_as_uploaded_file:true},
      initial:initial.document,raw_text_sha256:sha(equivalentText),
      before_raw_load:beforeLoad,after_typing:afterTyping,after_raw_load:afterLoad,after_native_completion:afterRelease,
      download_sha256:{initial:initial.sha256,final:final.sha256},
      same_value_world_preserved:true,stale_review_not_reopened:true,
      timing_instrumentation:'Original File.prototype.text executes and resolves actual uploaded bytes; only delivery of its successful result is held, then restored.'
    };
  });
}finally{
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));await new Promise(resolve=>proxy.close(resolve));
  let after,integrityError=null;
  try{after=await verifyInputs();assert.deepEqual(after,before);}catch(error){integrityError=String(error);}
  const receipt={
    schema:'towerops.raw-draft-independent-browser.v1',captured_utc:new Date().toISOString(),
    source_tree:inputs.nominated_composition_tree,product_source_tree:inputs.nominated_product_source_tree,
    source_manifest_sha256:inputs.source_manifest_sha256,source,
    receiver_sha256:sha(await readFile(new URL(import.meta.url))),runtime:{node:process.version,browser:browserVersion,puppeteer:require('puppeteer/package.json').version},
    before,after,integrity_error:integrityError,read_only_owner_source_and_build:true,
    groups,requests,errors,external_app_requests:external,proxy_blocks:proxyBlocks,downloads,
    passed:groups.filter(group=>group.passed).length,total:groups.length
  };
  await writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  if(groups.length!==2||groups.some(group=>!group.passed)||errors.length||external.length||integrityError)process.exitCode=1;
}
