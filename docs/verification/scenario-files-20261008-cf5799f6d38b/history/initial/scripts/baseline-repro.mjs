import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const require=createRequire(import.meta.url),puppeteer=require('puppeteer');
const source=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
await mkdir(out,{recursive:true});
const root=path.join(source,'web/airspace/dist'),requests=[],errors=[];
const server=http.createServer(async(req,res)=>{
  try {
    const pathname=new URL(req.url,'http://localhost').pathname;
    const relative=decodeURIComponent(pathname.replace(/^\/TowerOps\/airspace\/?/,''));
    const target=path.resolve(root,relative||'index.html');
    if(!target.startsWith(root+path.sep)&&target!==root)throw new Error('path');
    const file=(await stat(target)).isDirectory()?path.join(target,'index.html'):target;
    const body=await readFile(file);
    const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml'};
    requests.push({path:pathname,status:200,sha256:createHash('sha256').update(body).digest('hex')});
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});res.end(body);
  }catch{res.writeHead(404);res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
try{
  browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--disable-background-networking','--no-first-run'],userDataDir:path.join(out,'profile')});
  const page=await browser.newPage();await page.setViewport({width:1380,height:920});
  page.on('pageerror',e=>errors.push(String(e)));
  await page.setRequestInterception(true);
  const origin='http://127.0.0.1:'+server.address().port;
  page.on('request',r=>new URL(r.url()).origin===origin?r.continue():r.abort());
  await page.goto(origin+'/TowerOps/airspace/',{waitUntil:'networkidle0'});
  await page.$eval('.control-card',el=>el.open=true);await page.$eval('.state-workbench',el=>el.open=true);
  const world={version:7,observed_at:1002,aircraft:[
    {aircraft_id:'TWR101',x_nm:0,y_nm:0,altitude_ft:10000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0},
    {aircraft_id:'TWR202',x_nm:7,y_nm:0,altitude_ft:10000,vx_nm_min:0,vy_nm_min:0,climb_ft_min:0}
  ]};
  const policy=async value=>page.$eval('#policy-horizontal',(el,v)=>{el.value=String(v);el.dispatchEvent(new Event('input',{bubbles:true}));},value);
  const load=async text=>{await page.$eval('#world-json',(el,v)=>{el.focus();el.value=v;},text);await page.click('#load-world');await page.waitForFunction(()=>document.querySelector('#world-json-feedback').textContent.startsWith('Loaded'));};
  await load(JSON.stringify(world));await policy(9);
  assert.equal(await page.$eval('#pair-count',el=>el.textContent),'1');
  await page.click('#export-world');
  const saved=await page.$eval('#world-json',el=>el.value),exported=JSON.parse(saved);
  assert.deepEqual(exported,world);assert.equal(Object.hasOwn(exported,'policy'),false);
  const before=await page.$eval('#policy-horizontal',el=>Number(el.value));
  await policy(3);await load(saved);
  const after=await page.$eval('#policy-horizontal',el=>Number(el.value));
  assert.equal(after,3);assert.equal(await page.$eval('#pair-count',el=>el.textContent),'0');
  assert.deepEqual(JSON.parse(await page.$eval('#world-json',el=>el.value)),world);
  await page.screenshot({path:path.join(out,'policy-lost.png'),fullPage:true});
  await policy(9);assert.equal(await page.$eval('#pair-count',el=>el.textContent),'1');
  assert.equal(await page.$('#save-scenario'),null);assert.deepEqual(errors,[]);
  const tracked=execFileSync('git',['ls-files','-z'],{cwd:source}).toString().split('\0').filter(Boolean);
  const files=[];for(const p of tracked){const data=await readFile(path.join(source,p));files.push({path:p,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex'),git_blob:createHash('sha1').update(Buffer.from('blob '+data.length+'\0')).update(data).digest('hex')});}
  const receipt={schema:'towerops.scenario-baseline.v1',source_commit:execFileSync('git',['rev-parse','HEAD'],{cwd:source}).toString().trim(),source_tree:execFileSync('git',['rev-parse','HEAD^{tree}'],{cwd:source}).toString().trim(),status:execFileSync('git',['status','--porcelain'],{cwd:source}).toString(),runtime:{node:process.version,browser:await browser.version()},observations:[{name:'export omits the selected policy',before_horizontal_nm:before,exported_keys:Object.keys(exported)},{name:'loading the same world uses the replacement policy',after_horizontal_nm:after,conflicts_before:1,conflicts_after:0},{name:'manually restoring policy restores the conflict',conflicts:1}],browser_errors:errors,requests,files};
  await writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify({out,source:receipt.source_commit,observations:receipt.observations,browser_errors:errors,files:files.length}));
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
