import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';

const require=createRequire(import.meta.url),puppeteer=require('puppeteer');
const inputPath=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
const inputBytes=await readFile(inputPath),input=JSON.parse(inputBytes);
const source=path.resolve(input.source_root),dist=path.resolve(input.build_root);
const sha=body=>createHash('sha256').update(body).digest('hex');
const blob=body=>createHash('sha1').update(Buffer.from('blob '+body.length+'\0')).update(body).digest('hex');
await mkdir(out,{recursive:false});
await mkdir(path.join(out,'downloads'));await mkdir(path.join(out,'fixtures'));
const requests=[],errors=[],external=[],proxyBlocks=[],downloads=[],downloadProgress=new Map(),groups=[];
let groupName='',browser,browserVersion='unavailable';
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function verifyInputs(){
  for(const [base,rows,label] of [[source,input.source_files,'source'],[dist,input.build_files,'build']]){
    assert.ok(Array.isArray(rows)&&rows.length>0,label+' pins exist');
    for(const row of rows){
      const file=path.resolve(base,row.path);
      assert.ok(file.startsWith(base+path.sep),'pin path remains inside '+label);
      const body=await readFile(file);
      assert.equal(body.length,row.bytes,label+' length '+row.path);
      assert.equal(sha(body),row.sha256,label+' digest '+row.path);
      if(row.git_blob)assert.equal(blob(body),row.git_blob,label+' Git blob '+row.path);
    }
  }
  return {source_files:input.source_files.length,build_files:input.build_files.length,
    main_sha256:sha(await readFile(path.join(source,'web/airspace/src/main.ts')))};
}
const before=await verifyInputs();
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=new URL(req.url,'http://localhost').pathname;
    const relative=decodeURIComponent(pathname.replace(/^\/TowerOps\/airspace\/?/,''));
    const target=path.resolve(dist,relative||'index.html');
    if(target!==dist&&!target.startsWith(dist+path.sep))throw Error('Outside pinned production build');
    const file=(await stat(target)).isDirectory()?path.join(target,'index.html'):target;
    const body=await readFile(file),types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript',
      '.css':'text/css','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml','.py':'text/plain'};
    requests.push({group:groupName,path:pathname,status:200,sha256:sha(body)});
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});res.end(body);
  }catch(error){requests.push({group:groupName,path:req.url,status:404,error:String(error)});res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const proxy=http.createServer((req,res)=>{
  proxyBlocks.push({method:req.method,url:req.url});res.writeHead(403);res.end('External receiving requests denied');
});
proxy.on('connect',(req,socket)=>{
  socket.on('error',error=>proxyBlocks.push({method:'SOCKET_ERROR',code:error.code}));
  proxyBlocks.push({method:'CONNECT',url:req.url});
  socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');
});
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
async function until(fn,label,milliseconds=20000){
  const start=Date.now();
  while(Date.now()-start<milliseconds){if(await fn())return;await sleep(20);}
  throw Error('Timed out: '+label);
}
async function settled(page){
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
}
async function pageAt(){
  const page=await browser.newPage();await page.setViewport({width:1320,height:960});
  page.on('pageerror',error=>errors.push({group:groupName,error:String(error)}));
  page.on('request',request=>{
    const url=request.url();
    if(!url.startsWith('blob:')&&!url.startsWith('data:')&&new URL(url).origin!==origin)external.push({group:groupName,url});
  });
  await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});
  await page.waitForSelector('#review-options');
  await page.waitForFunction(()=>!!document.querySelector('#world-json')?.value);
  if(!await page.$eval('.scenario-workbench',node=>node.open))await page.click('.scenario-workbench > summary');
  return page;
}
async function stateOf(page){
  return page.evaluate(()=>{
    const text=id=>document.getElementById(id).textContent;
    const visible=node=>!!node.getClientRects().length&&!node.closest('[hidden]');
    return {
      proposal_state:text('proposal-state'),proposal_output:text('proposal-output'),
      approve_enabled:!document.getElementById('approve').disabled,
      readback_enabled:!document.getElementById('readback').disabled,
      gates:['gate-screen','gate-approval','gate-ack'].map(id=>document.getElementById(id).querySelector('i').textContent),
      options_visible:!document.getElementById('advisory-review').hidden,
      options_count:text('advisory-options-count'),options_status:text('advisory-options-status'),
      review_enabled:!document.getElementById('review-options').disabled,
      options:[...document.querySelectorAll('#advisory-options-list button[data-advisory-hash]')].map(node=>({
        hash:node.dataset.advisoryHash,enabled:!node.disabled,visible:visible(node),text:node.textContent
      })),
      flight_ids:[...document.querySelectorAll('#flight-list button')].map(node=>node.textContent),
      python_status:text('python-status'),scenario_status:text('scenario-status'),
      scenario_review_visible:!document.getElementById('scenario-review').hidden,
      scenario_apply_enabled:!document.getElementById('load-scenario').disabled
    };
  });
}
async function save(page,label){
  const first=downloads.length;await page.click('#save-scenario');
  await until(()=>downloads.length>first,'real scenario Save starts');
  const event=downloads[first];event.receiving_label=label;
  await until(()=>downloadProgress.get(event.guid)==='completed','real scenario Save completes');
  const file=path.join(out,'downloads',event.guid),text=await readFile(file,'utf8');
  return {file,document:JSON.parse(text),sha256:sha(text)};
}
async function chooseFile(page,file){
  const chooser=page.waitForFileChooser();await page.click('#choose-scenario');
  await(await chooser).accept([file]);
  await page.waitForFunction(()=>!document.querySelector('#scenario-review').hidden&&!document.querySelector('#load-scenario').disabled);
  await settled(page);
}
async function reviewNative(page){
  await page.click('#review-options');
  await page.waitForFunction(()=>!document.querySelector('#review-options').disabled&&
    document.querySelectorAll('#advisory-options-list button[data-advisory-hash]').length>0,{timeout:90000});
  await settled(page);
  const view=await stateOf(page);
  assert.match(view.python_status,/Live CPython.*native candidate review/);
  assert.ok(view.options.some(option=>option.enabled&&option.visible),'genuine native review offers an action');
  return view;
}
async function chooseOption(page,hash){
  await page.click('#advisory-options-list button[data-advisory-hash="'+hash+'"]');await settled(page);
  const view=await stateOf(page);
  assert.equal(view.proposal_state,'PROPOSAL READY');
  assert.equal(view.approve_enabled,true);assert.equal(view.readback_enabled,false);
  return view;
}
async function group(name,fn){
  groupName=name;const start=Date.now(),observations={};
  try{await fn(observations);groups.push({name,passed:true,seconds:(Date.now()-start)/1000,observations});}
  catch(error){groups.push({name,passed:false,seconds:(Date.now()-start)/1000,observations,error:String(error),stack:error.stack});}
  finally{for(const page of await browser.pages())if(page.url().startsWith(origin+'/'))await page.close();}
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
  cdp.on('Browser.downloadWillBegin',event=>downloads.push(event));
  cdp.on('Browser.downloadProgress',event=>downloadProgress.set(event.guid,event.state));

  await group('explicit same-value scenario Load retires previous native alternatives and approval',async observed=>{
    const page=await pageAt(),saved=await save(page,'same-value scenario before native alternatives');
    observed.saved_scenario=saved.document;observed.initial_download_sha256=saved.sha256;
    observed.native_review=await reviewNative(page);
    const hash=observed.native_review.options.find(option=>option.enabled&&option.visible).hash;
    observed.selected_before_load=await chooseOption(page,hash);
    await page.click('#approve');await settled(page);
    observed.approved_before_load=await stateOf(page);
    assert.equal(observed.approved_before_load.approve_enabled,false);
    assert.equal(observed.approved_before_load.readback_enabled,true);
    await chooseFile(page,saved.file);
    observed.reviewed_scenario=await stateOf(page);
    assert.equal(observed.reviewed_scenario.readback_enabled,true,'file review preserves the existing approval');
    await page.click('#load-scenario');await settled(page);
    observed.after_explicit_load=await stateOf(page);
    const after=await save(page,'same-value live world after explicit scenario Load');
    observed.after_load_download_sha256=after.sha256;
    assert.deepEqual(after.document,saved.document,'the world, policy, clock, scale and selected flight really are unchanged');
    const stale=observed.after_explicit_load.options.find(option=>option.enabled&&option.visible&&option.hash===hash)
      ??observed.after_explicit_load.options.find(option=>option.enabled&&option.visible);
    if(stale){
      observed.stale_action_hash=stale.hash;
      await page.click('#advisory-options-list button[data-advisory-hash="'+stale.hash+'"]');await settled(page);
      observed.after_old_action=await stateOf(page);
    }
    await page.$eval(observed.after_explicit_load.options_visible?'#advisory-review':'.proposal-card',node=>node.scrollIntoView({block:'start'}));
    await settled(page);
    await page.screenshot({path:path.join(out,'same-value-alternatives.png'),fullPage:false});
    assert.equal(observed.after_explicit_load.approve_enabled,false,'Load clears the existing selected proposal');
    assert.equal(observed.after_explicit_load.readback_enabled,false,'Load clears the existing approval');
    assert.deepEqual(observed.after_explicit_load.gates,['WAIT','WAIT','WAIT']);
    assert.equal(stale,undefined,'prior alternatives must not remain selectable after explicit scenario replacement');
    observed.fresh_native_review=await reviewNative(page);
    const freshHash=observed.fresh_native_review.options.find(option=>option.enabled&&option.visible).hash;
    observed.fresh_selection=await chooseOption(page,freshHash);
    assert.equal(observed.fresh_selection.readback_enabled,false,'the fresh selection requires a new approval');
    await page.close();
  });

  await group('changed-version scenario Load also invalidates alternatives through the existing snapshot guard',async observed=>{
    const page=await pageAt(),saved=await save(page,'changed-version control initial scenario');
    observed.initial=saved.document;
    observed.native_review=await reviewNative(page);
    const changed=structuredClone(saved.document);changed.world.version+=1;
    const file=path.join(out,'fixtures','changed-version-scenario.json');
    await writeFile(file,JSON.stringify(changed));
    await chooseFile(page,file);
    await page.click('#load-scenario');await settled(page);
    observed.after_explicit_load=await stateOf(page);
    const after=await save(page,'changed-version scenario after explicit Load');
    observed.loaded=after.document;observed.download_sha256=after.sha256;
    assert.deepEqual(after.document,changed);
    assert.equal(observed.after_explicit_load.approve_enabled,false);
    assert.equal(observed.after_explicit_load.readback_enabled,false);
    assert.equal(observed.after_explicit_load.options.filter(option=>option.enabled&&option.visible).length,0);
    assert.equal(observed.after_explicit_load.review_enabled,true);
    await page.close();
  });
}finally{
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));await new Promise(resolve=>proxy.close(resolve));
  let after,integrityError=null;
  try{after=await verifyInputs();assert.deepEqual(after,before);}catch(error){integrityError=String(error);}
  const nativeAssetRequests=requests.filter(request=>request.status===200&&
    /\/python\/(?:advisory_options\.py|towerops\.py|pyodide\.asm\.wasm)$/.test(request.path));
  const nativeAssetsReceived=['advisory_options.py','towerops.py','pyodide.asm.wasm']
    .every(name=>nativeAssetRequests.some(request=>request.path.endsWith('/'+name)));
  const receipt={
    schema:'towerops.scenario-alternatives-independent.v1',captured_utc:new Date().toISOString(),
    phase:input.phase,source_tree:input.source_tree,source,dist,input_manifest_sha256:sha(inputBytes),
    receiver_sha256:sha(await readFile(new URL(import.meta.url))),
    runtime:{node:process.version,browser:browserVersion,puppeteer:require('puppeteer/package.json').version},
    before,after,integrity_error:integrityError,read_only_source_and_existing_build:true,
    groups,requests,native_asset_requests:nativeAssetRequests,native_assets_received:nativeAssetsReceived,
    errors,external_app_requests:external,proxy_blocks:proxyBlocks,downloads,
    passed:groups.filter(item=>item.passed).length,total:groups.length,
    product_overrides:false,native_result_fabrication:false
  };
  await writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  if(groups.length!==2||groups.some(item=>!item.passed)||errors.length||external.length||integrityError||!nativeAssetsReceived)process.exitCode=1;
}
