// Native built TowerOps page, disposable Chrome profile, no product-source edits.
// Only RAF scheduling is controlled. The page's rendering, physics, event handlers,
// WorldState export, DOM, and styles remain native; the Python planner is not invoked.
// node receiving-browser.mjs --chrome /path/to/chrome --repo /captured/repo
//   --manifest /source-manifest.json --out /unique/desktop [--mobile] [--expect-broken]
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { lstat, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const option = name => args.includes(name) ? args[args.indexOf(name) + 1] : undefined;
for (const name of ['--chrome', '--repo', '--manifest', '--out']) {
  if (!option(name)) throw new Error(`${name} is required`);
}
const repo = resolve(option('--repo')), app = join(repo, 'web/airspace');
const dist = resolve(option('--dist') || join(app, 'dist')), out = resolve(option('--out'));
const mobile = args.includes('--mobile'), expectBroken = args.includes('--expect-broken');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const report = { schema: 'towerops-native-playback-receiving/v1', started_at: new Date().toISOString(),
  mobile, expect_broken: expectBroken, cases: [], screenshots: [], page_errors: [], requests: [],
  boundaries: ['Exact built app and source manifest checked before and after execution.',
    'RAF callbacks receive controlled timestamps; page physics and drawing are unchanged.',
    'Controls use Chrome input events; observations use the native Export live world action.',
    'No planner, approval, readback, Pyodide execution, production service, or user profile qualification.'] };
let server, chrome, socket, profile, origin, nextId = 0, chromeErrors = '';
const pending = new Map();

async function fingerprint(path) {
  const info = await lstat(path); assert.ok(info.isFile(), `Expected regular file: ${path}`);
  const sha = createHash('sha256'), git = createHash('sha1').update(`blob ${info.size}\0`);
  for await (const data of createReadStream(path)) { sha.update(data); git.update(data); }
  return { bytes: info.size, sha256: sha.digest('hex'), git_blob: git.digest('hex') };
}
async function sourcePins() {
  const manifest = JSON.parse(await readFile(option('--manifest'), 'utf8'));
  const files = {};
  for (const entry of manifest.files) {
    const path = resolve(repo, entry.path);
    assert.ok(path.startsWith(repo + sep), `Source path escaped repo: ${entry.path}`);
    const actual = await fingerprint(path); assert.equal(actual.sha256, entry.sha256, entry.path);
    if (entry.git_blob) assert.equal(actual.git_blob, entry.git_blob, entry.path);
    files[entry.path] = actual;
  }
  return { manifest: await fingerprint(option('--manifest')), files };
}
async function buildPins(dir = dist) {
  const files = {};
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) Object.assign(files, await buildPins(path));
    else files[relative(dist, path)] = await fingerprint(path);
  }
  return files;
}
async function eventually(fn, label) {
  const end = Date.now() + 15000;
  do { const value = await fn(); if (value) return value; await pause(40); } while (Date.now() < end);
  throw new Error(`Timed out: ${label}`);
}
function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 15000);
    pending.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const answer = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (answer.exceptionDetails) throw new Error(JSON.stringify(answer.exceptionDetails));
  return answer.result.value;
}
async function click(selector) {
  const box = await evaluate(`(() => {
    const node = document.querySelector(${JSON.stringify(selector)});
    if (!node || node.disabled || !node.getClientRects().length) throw new Error('Control unavailable');
    node.scrollIntoView({ block: 'center', behavior: 'instant' });
    const r = node.getBoundingClientRect(), x = r.x + r.width / 2, y = r.y + r.height / 2;
    const hit = document.elementFromPoint(x, y);
    if (!hit || !(hit === node || node.contains(hit))) throw new Error('Control is covered');
    return { x, y };
  })()`);
  await command('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...box });
  await command('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...box });
}
async function key(name, code, virtualKey, modifiers = 0) {
  const params = { key: name, code, windowsVirtualKeyCode: virtualKey, modifiers };
  await command('Input.dispatchKeyEvent', { type: 'rawKeyDown', ...params });
  await command('Input.dispatchKeyEvent', { type: 'keyUp', ...params });
}
async function details(selector, open = true) {
  if (await evaluate(`document.querySelector(${JSON.stringify(selector)}).open`) !== open)
    await click(`${selector} > summary`);
}
async function setRange(selector, value) {
  const range = await evaluate(`(() => {const n=document.querySelector(${JSON.stringify(selector)});return {min:+n.min,step:+n.step};})()`);
  const steps = (value - range.min) / range.step; assert.ok(Number.isInteger(steps) && steps >= 0);
  await click(selector); await key('Home', 'Home', 36);
  for (let i = 0; i < steps; i++) await key('ArrowRight', 'ArrowRight', 39);
  assert.equal(await evaluate(`+document.querySelector(${JSON.stringify(selector)}).value`), value);
}
async function tick(time) {
  const frame = await evaluate(`window.__toweropsPlaybackReceiving.tick(${time})`);
  assert.equal(frame.called, 1, 'Exactly the native playback RAF must execute');
  assert.equal(frame.pending, 1, 'The native playback RAF must schedule its next frame');
}
async function world() {
  await details('.state-workbench'); await click('#export-world');
  return evaluate(`(async () => {
    const canvas=document.querySelector('#airspace'), ctx=canvas.getContext('2d');
    const pixels=ctx.getImageData(0,0,canvas.width,canvas.height).data;
    const digest=await crypto.subtle.digest('SHA-256',pixels);
    return { world:JSON.parse(document.querySelector('#world-json').value),
      label:document.querySelector('#toggle-run').textContent, rate:+document.querySelector('#speed-range').value,
      rate_label:document.querySelector('#speed-value').textContent, clock:document.querySelector('#sim-clock').textContent,
      feedback:document.querySelector('#builder-feedback').textContent,
      python:document.querySelector('#python-status').textContent,
      canvas:{width:canvas.width,height:canvas.height,sha256:Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('')} };
  })()`);
}
function check(test, name, actual, expected) {
  try { assert.deepEqual(actual, expected); test.checks.push({ name, ok: true }); }
  catch { test.checks.push({ name, ok: false, actual, expected }); }
}
function near(test, name, actual, expected) {
  check(test, name, Number.isFinite(actual) && Math.abs(actual - expected) < 1e-8, true);
  test.numeric_observations ??= []; test.numeric_observations.push({ name, actual, expected });
}
function progression(test, name, before, after, minutes, clockStart) {
  near(test, `${name}: clock`, after.observed_at - clockStart, minutes * 60);
  check(test, `${name}: world version`, after.version, before.version + 2);
  check(test, `${name}: aircraft identity`, after.aircraft.map(a=>a.aircraft_id), before.aircraft.map(a=>a.aircraft_id));
  for (let i = 0; i < before.aircraft.length; i++) {
    const a = before.aircraft[i], b = after.aircraft[i];
    near(test, `${name}: ${a.aircraft_id} east`, b.x_nm - a.x_nm, a.vx_nm_min * minutes);
    near(test, `${name}: ${a.aircraft_id} north`, b.y_nm - a.y_nm, a.vy_nm_min * minutes);
    near(test, `${name}: ${a.aircraft_id} altitude`, b.altitude_ft - a.altitude_ft, a.climb_ft_min * minutes);
    check(test, `${name}: ${a.aircraft_id} velocity`, [b.vx_nm_min,b.vy_nm_min,b.climb_ft_min], [a.vx_nm_min,a.vy_nm_min,a.climb_ft_min]);
  }
}
async function freshPage() {
  const previousTimeOrigin = await evaluate('performance.timeOrigin');
  await command('Page.navigate', { url: origin + '/' });
  await eventually(async () => {
    try { return await evaluate(`performance.timeOrigin!==${previousTimeOrigin} && document.readyState==='complete' && !!window.__toweropsPlaybackReceiving && window.__toweropsPlaybackReceiving.pending()===1 && document.querySelector('#world-json')?.value.startsWith('{')`); }
    catch (error) { if (/Cannot find context|Execution context was destroyed/.test(String(error))) return false; throw error; }
  }, 'new native app initialization');
  await details('.control-card'); await details('.state-workbench');
}
async function screenshot(test) {
  await details('.state-workbench', false);
  report.layout = await evaluate(`(() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
    controls:Object.fromEntries(['toggle-run','reset-world','speed-range','speed-value'].map(id=>{
      const n=document.getElementById(id),r=n.getBoundingClientRect();
      return [id,{x:r.x,y:r.y+scrollY,width:r.width,height:r.height,visible:!!n.getClientRects().length,text:n.textContent}];
    }))}))()`);
  check(test, 'native page has no horizontal overflow', report.layout.scrollWidth <= report.layout.width + 1, true);
  for (const [id, r] of Object.entries(report.layout.controls))
    check(test, `${id} visible within page width`, r.visible && r.x >= -1 && r.x + r.width <= report.layout.width + 1, true);
  const metrics = await command('Page.getLayoutMetrics');
  const size = metrics.cssContentSize; assert.ok(size.height < 14000, 'Unexpected page height');
  const shot = await command('Page.captureScreenshot', { format:'png',captureBeyondViewport:true,
    clip:{x:0,y:0,width:size.width,height:size.height,scale:1} });
  const path=out+'.png'; await writeFile(path,Buffer.from(shot.data,'base64'));
  report.screenshots.push({path,step:'reset-3x/after-reset-paused',...await fingerprint(path)});
}

try {
  await mkdir(dirname(out), {recursive:true});
  report.driver = await fingerprint(fileURLToPath(import.meta.url));
  report.source_before = await sourcePins(); report.build_before = await buildPins();
  const fixture = JSON.parse(await readFile(join(app,'tests/python-reference.json'),'utf8')).scenarios[0];
  const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.wasm':'application/wasm','.zip':'application/zip'};
  server=createServer(async(req,res)=>{
    try {
      const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
      const path=resolve(dist,'.'+(pathname==='/'?'/index.html':pathname));
      if(!path.startsWith(dist+sep))throw new Error('Outside build');
      const info=await lstat(path);if(!info.isFile())throw new Error('Not a file');
      res.writeHead(200,{'Content-Type':mime[extname(path)]||'application/octet-stream','Cache-Control':'no-store'});
      createReadStream(path).pipe(res);
    }catch{res.writeHead(404);res.end('Not found');}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve)); origin=`http://127.0.0.1:${server.address().port}`;
  profile=await mkdtemp(join(tmpdir(),'towerops-playback-chrome-55e3-'));
  chrome=spawn(option('--chrome'),['--headless=new','--remote-debugging-port=0','--user-data-dir='+profile,
    '--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-sync',
    '--disable-component-update','--password-store=basic','--use-mock-keychain','about:blank'],{stdio:['ignore','ignore','pipe']});
  chrome.stderr.on('data',data=>{chromeErrors=(chromeErrors+data).slice(-5000);});
  chrome.once('error',error=>{chromeErrors+=String(error);});
  const port=await eventually(async()=>{
    if(chrome.exitCode!==null)throw new Error('Chrome exited: '+chromeErrors);
    try{return Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);}catch{return null;}
  },'Chrome debugger');
  const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  socket.addEventListener('message',({data})=>{
    const message=JSON.parse(data);
    if(message.id){const call=pending.get(message.id);if(!call)return;clearTimeout(call.timer);pending.delete(message.id);
      message.error?call.reject(new Error(JSON.stringify(message.error))):call.resolve(message.result);
    }else if(message.method==='Runtime.exceptionThrown')report.page_errors.push(message.params.exceptionDetails);
    else if(message.method==='Network.responseReceived'){
      const r=message.params.response;report.requests.push({url:r.url,status:r.status,mime:r.mimeType});
    }
  });
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
  await command('Runtime.enable');await command('Page.enable');await command('Network.enable');
  report.browser=await command('Browser.getVersion');
  await command('Emulation.setDeviceMetricsOverride',{width:mobile?390:1280,height:1000,deviceScaleFactor:1,mobile});
  await command('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{
    let next=0,last=-1;const frames=new Map(),events=[];
    window.requestAnimationFrame=fn=>{const id=++next;frames.set(id,fn);return id;};
    window.cancelAnimationFrame=id=>frames.delete(id);
    window.__toweropsPlaybackReceiving={events,pending:()=>frames.size,tick:t=>{
      if(t<=last)throw new Error('RAF timestamps must increase');last=t;
      const batch=[...frames.values()];frames.clear();for(const fn of batch)fn(t);
      return{called:batch.length,pending:frames.size};
    }};
    for(const type of ['click','input'])document.addEventListener(type,event=>{
      const n=event.target;if(n?.id)events.push({type,id:n.id,trusted:event.isTrusted});
    },true);
  })();`});
  for(const rate of [3,0.5]){
    const test={name:`reset-${rate}x`,checks:[],observations:{}};report.cases.push(test);await freshPage();
    await setRange('#speed-range',rate);await click('#toggle-run');await tick(1000);await tick(1080);
    const moving=await world();test.observations.moving=moving;
    progression(test,'chosen rate',fixture.state,moving.world,0.08*rate,fixture.now);
    await click('#reset-world');const reset=await world();test.observations.reset=reset;
    await tick(1160);await tick(1240);const idle=await world();test.observations.idle=idle;
    check(test,'reset exact native fixture',reset.world,fixture.state);check(test,'paused across two frames',idle.world,reset.world);
    check(test,'reset action label',reset.label,'Run traffic');
    check(test,'reset slider value',reset.rate,1);
    check(test,'reset rate readout',reset.rate_label,'1.0x');
    check(test,'reset visible clock',reset.clock,'T+0 SEC');
    if(rate===3)await screenshot(test);
    await click('#toggle-run');await tick(2000);await tick(2080);const resumed=await world();test.observations.resumed=resumed;
    progression(test,'reset default engine rate',fixture.state,resumed.world,0.08,fixture.now);
    check(test,'resumed action label',resumed.label,'Pause traffic');
    check(test,'native drawing changes with actual movement',resumed.canvas.sha256!==reset.canvas.sha256,true);
    if(expectBroken){
      // Require the original rate itself, with intact world identity/version and
      // velocity. An arbitrary wrong clock, position, or DOM value is not proof.
      check(test,'known baseline stale rate readout',reset.rate_label,`${rate.toFixed(1)}x`);
      progression(test,'known baseline retained rate',fixture.state,resumed.world,0.08*rate,fixture.now);
      test.expected_baseline_failures=['reset rate readout','reset default engine rate: clock'];
      for(const aircraft of fixture.state.aircraft)for(const [axis,velocity] of [['east','vx_nm_min'],['north','vy_nm_min'],['altitude','climb_ft_min']])
        if(aircraft[velocity]!==0)test.expected_baseline_failures.push(`reset default engine rate: ${aircraft.aircraft_id} ${axis}`);
    }
    test.events=await evaluate('window.__toweropsPlaybackReceiving.events');
  }
  for(const kind of ['policy','refused-flight']){
    const test={name:`automatic-pause-${kind}-2x`,checks:[],observations:{}};report.cases.push(test);await freshPage();
    await setRange('#speed-range',2);await click('#toggle-run');await tick(1000);await tick(1080);
    const before=await world();test.observations.before=before;
    progression(test,'2x before automatic pause',fixture.state,before.world,0.16,fixture.now);
    if(kind==='policy'){await details('.policy-editor');await setRange('#policy-horizontal',6);}
    else{await click('#flight-speed');await key('a','KeyA',65,4);await key('Backspace','Backspace',8);
      assert.equal(await evaluate('document.querySelector("#flight-speed").value'),'');await click('#add-custom-flight');}
    const paused=await world();test.observations.paused=paused;
    await tick(1160);await tick(1240);const idle=await world();test.observations.idle=idle;
    check(test,'automatic pause action label',paused.label,'Run traffic');check(test,'chosen rate preserved',[paused.rate,paused.rate_label],[2,'2.0x']);
    check(test,'policy/refusal leaves world unchanged',paused.world,before.world);check(test,'paused across two frames',idle.world,paused.world);
    if(kind==='refused-flight')check(test,'native validation refusal',paused.feedback.startsWith('NOT ADDED:'),true);
    await click('#toggle-run');await tick(2000);await tick(2080);const resumed=await world();test.observations.resumed=resumed;
    progression(test,'resume retains 2x',paused.world,resumed.world,0.16,paused.world.observed_at);
    check(test,'resumed action label',resumed.label,'Pause traffic');
    if(expectBroken){
      check(test,'known baseline stale pause button',paused.label,'Pause traffic');
      test.expected_baseline_failures=['automatic pause action label'];
    }
    test.events=await evaluate('window.__toweropsPlaybackReceiving.events');
  }
  for(const test of report.cases){
    check(test,'all observed control events are trusted',test.events.every(e=>e.trusted),true);
    for(const id of ['toggle-run','speed-range','export-world'])check(test,`${id} received native input`,test.events.some(e=>e.id===id),true);
    test.ok=test.checks.every(c=>c.ok);
  }
  report.failed_cases=report.cases.filter(c=>!c.ok).map(c=>c.name);
  assert.deepEqual(report.page_errors,[],'No native page exceptions');
  assert.equal(report.failed_cases.length,expectBroken?4:0,'Expected known before/after case outcomes');
  if(expectBroken)for(const test of report.cases){
    const failures=test.checks.filter(c=>!c.ok).map(c=>c.name);
    assert.deepEqual(failures.sort(),test.expected_baseline_failures.toSorted(),
      'Only exact known baseline observations qualify; all unrelated native invariants must pass');
  }
  assert.ok(report.requests.some(r=>r.mime==='text/css'&&r.status===200),'Native built styles received');
  assert.ok(!report.requests.some(r=>/pyodide|python_stdlib|\.wasm(?:$|\?)/.test(r.url)),'Planner runtime must remain uninvoked');
  report.ok=true;
}catch(error){report.ok=false;report.error=String(error.stack||error);process.exitCode=1;}
finally{
  if(socket?.readyState===WebSocket.OPEN){try{await command('Browser.close');}catch{}}
  socket?.close();for(const call of pending.values()){clearTimeout(call.timer);call.reject(new Error('Receiving complete'));}pending.clear();
  if(chrome&&chrome.exitCode===null){chrome.kill('SIGTERM');await Promise.race([new Promise(resolve=>chrome.once('exit',resolve)),pause(3000)]);if(chrome.exitCode===null)chrome.kill('SIGKILL');}
  if(server){server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
  if(profile)await rm(profile,{recursive:true,force:true});
  try{report.source_after=await sourcePins();report.build_after=await buildPins();assert.deepEqual(report.source_after,report.source_before);assert.deepEqual(report.build_after,report.build_before);report.source_and_build_unchanged=true;}
  catch(error){report.ok=false;report.integrity_error=String(error);process.exitCode=1;}
  report.finished_at=new Date().toISOString();if(!report.ok)report.chrome_stderr=chromeErrors;
  await writeFile(out+'.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({ok:report.ok,report:out+'.json',screenshots:report.screenshots,failed_cases:report.failed_cases,error:report.error},null,2));
}
