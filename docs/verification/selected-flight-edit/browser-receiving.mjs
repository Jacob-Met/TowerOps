// Independent receiving for the selected-flight editor. Raw CDP transport is
// retained from ShadeWindow's proven native browser receiver.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';

const projectRoot = path.resolve(process.argv[2]);
const sourceRoot = path.join(projectRoot, 'web/airspace/dist');
const browserPath = process.env.TOWEROPS_CHROMIUM || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const evidenceDir = process.env.TOWEROPS_EVIDENCE_DIR || path.join(projectRoot, 'browser-evidence');
await fs.mkdir(evidenceDir, { recursive: true });
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'hamon-towerops-receiving-72ac1419-'));
const manifest = JSON.parse(await fs.readFile(process.env.TOWEROPS_SOURCE_MANIFEST || path.join(projectRoot, 'docs/verification/selected-flight-edit/receiving-candidate.json')));
const sourceFiles = manifest.files.filter(x => !x.path.includes('/dist/')).map(x => x.path);
const hashSources = async () => Object.fromEntries(await Promise.all(sourceFiles.map(async name => [
  name, crypto.createHash('sha256').update(await fs.readFile(path.join(projectRoot, name))).digest('hex'),
])));
const before = await hashSources();
for (const f of manifest.files.filter(x => !x.path.includes('/dist/'))) assert.equal(before[f.path], f.sha256, f.path);
const checks = [], exceptions = [], requests = [], served = [], checkpoints = {};
let browser, socket, receipt, failure, browserContextId;
const types = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript',
  '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
  '.wasm': 'application/wasm', '.zip': 'application/zip' };
const server = http.createServer(async (request, response) => {
  try {
    let pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    if (pathname === '/') pathname = '/index.html';
    const file = path.resolve(sourceRoot, '.' + pathname);
    if (!file.startsWith(sourceRoot + path.sep)) throw new Error('Outside test source');
    const bytes = await fs.readFile(file);
    served.push({ path: pathname, bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') });
    response.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
    response.end(bytes);
  } catch (error) {
    console.error('HTTP_RECEIVER_ERROR', request.url, String(error));
    response.writeHead(404);
    response.end('Unavailable in isolated receiver');
  }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const url = 'http://127.0.0.1:' + server.address().port + '/';
const probe = await fetch(url, {signal:AbortSignal.timeout(10000)});
assert.equal(probe.status,200);
assert.ok((await probe.text()).includes('TowerOps'));
console.log('LOOPBACK_SELF_PROBE_PASS',url);
const browserVersion = execFileSync(browserPath, ['--version'], { encoding: 'utf8', timeout: 15000 }).trim();
let nextId = 0;
const pending = new Map();
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
function send(method, params = {}, sessionId) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, method==='Page.navigate'?45000:15000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
}
async function evaluate(sessionId, expression) {
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }, sessionId);
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}
async function waitFor(sessionId, expression, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await evaluate(sessionId, expression)) return;
    await delay(80);
  }
  throw new Error('Page did not reach expected state: ' + expression);
}
async function openPage(width = 1280, height = 1000) {
  assert.ok(browserContextId, 'A private receiving context is required');
  const { targetId } = await send('Target.createTarget', { url: 'about:blank', browserContextId });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
  await send('Runtime.enable', {}, sessionId);
  await send('Page.enable', {}, sessionId);
  await send('Network.enable', {}, sessionId);
  await send('Page.navigate', { url }, sessionId);
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false }, sessionId);
  await waitFor(sessionId, 'document.querySelector("#world-json")?.value.includes("aircraft")');
  return { targetId, sessionId };
}
async function click(sessionId, selector) {
  const point = await evaluate(sessionId, '(() => { const e=document.querySelector(' + JSON.stringify(selector) +
    '); if(!e) throw new Error("Missing element"); if(e.disabled) throw new Error("Disabled element"); e.scrollIntoView({block:"center"}); const r=e.getBoundingClientRect(); if(!r.width||!r.height) throw new Error("Hidden element"); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()');
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point }, sessionId);
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point }, sessionId);
}
async function key(sessionId, name, code, virtual) {
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: name, code, windowsVirtualKeyCode: virtual,
    ...(name === 'Enter' ? {text:'\r'} : {}) }, sessionId);
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code, windowsVirtualKeyCode: virtual }, sessionId);
}
async function activateKeyboard(sessionId, selector) {
  await evaluate(sessionId, 'document.querySelector(' + JSON.stringify(selector) + ').focus()');
  await key(sessionId, 'Enter', 'Enter', 13);
}
async function setControls(sessionId, values) {
  await evaluate(sessionId, '(() => { for(const [id,value] of Object.entries(' + JSON.stringify(values) +
    ')){const e=document.getElementById(id);e.value=String(value);e.dispatchEvent(new Event("input",{bubbles:true}));} })()');
}
async function readState(sessionId) {
  return evaluate(sessionId, '(() => ({' +
    'world:JSON.parse(document.getElementById("world-json").value),' +
    'draft:Object.fromEntries(["flight-id","flight-x","flight-y","flight-level","flight-bearing","flight-speed","flight-climb"].map(id=>[id,document.getElementById(id).value])),' +
    'mode:document.getElementById("builder-mode").textContent,' +
    'preview:document.getElementById("track-edit-preview").textContent,' +
    'rows:[...document.querySelectorAll("#track-edit-preview tbody tr")].map(r=>[...r.children].map(c=>c.textContent)),' +
    'feedback:document.getElementById("builder-feedback").textContent,' +
    'proposal:document.getElementById("proposal-output").textContent,' +
    'proposalState:document.getElementById("proposal-state").textContent,' +
    'gates:["gate-screen","gate-approval","gate-ack"].map(id=>document.getElementById(id).className),' +
    'disabled:Object.fromEntries(["run-planner","approve","readback","toggle-run","reset-world","apply-track-edit","policy-horizontal","load-world"].map(id=>[id,document.getElementById(id).disabled])),' +
    'audit:[...document.querySelectorAll("#audit-events li")].map(e=>e.textContent),' +
    'auditStatus:document.getElementById("audit-status").textContent,' +
    'python:document.getElementById("python-status").textContent,' +
    'idReadonly:document.getElementById("flight-id").readOnly,' +
    'active:document.activeElement.id,' +
    'bodyOverflow:document.documentElement.scrollWidth>window.innerWidth+1' +
    '}))()');
}
async function screenshot(sessionId, name) {
  await evaluate(sessionId, 'window.scrollTo(0,0)');
  const { cssContentSize } = await send('Page.getLayoutMetrics', {}, sessionId);
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: cssContentSize.width, height: cssContentSize.height, scale: 1 } }, sessionId);
  await fs.writeFile(path.join(evidenceDir, name), Buffer.from(shot.data, 'base64'));
}
function pass(description) { checks.push(description); console.log('CHECK_PASS ' + description); }
async function runPlanner(sessionId) {
  await click(sessionId, '#run-planner');
  await waitFor(sessionId, 'document.getElementById("python-status").textContent.includes("Live CPython") && document.getElementById("proposal-state").textContent==="PROPOSAL READY"', 90000);
}
async function readback(sessionId, expectedEvents) {
  await click(sessionId, '#readback');
  await waitFor(sessionId, 'document.getElementById("python-status").textContent.includes("ControlRoom.apply") && document.querySelectorAll("#audit-events li").length===' + expectedEvents, 90000);
}

try {
  browser = spawn(browserPath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-extensions',
    '--password-store=basic', '--incognito', '--no-proxy-server', '--log-net-log=' + path.join(evidenceDir, 'chrome-netlog.json'), '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
    '--user-data-dir=' + profile, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
  const endpoint = await new Promise((resolve, reject) => {
    let errors = '';
    const timer = setTimeout(() => reject(new Error('Chromium did not start: ' + errors.slice(-2000))), 15000);
    browser.on('error', error => { clearTimeout(timer); reject(error); });
    browser.on('exit', code => { clearTimeout(timer); reject(new Error('Chromium exited: ' + code + ' ' + errors.slice(-2000))); });
    browser.stderr.on('data', bytes => {
      errors += bytes.toString();
      const found = errors.match(/DevTools listening on (ws:\/\/127\.0\.0\.1:[^\s]+)/);
      if (found) { clearTimeout(timer); resolve(found[1]); }
    });
  });
  socket = new WebSocket(endpoint);
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const task = pending.get(message.id); pending.delete(message.id); clearTimeout(task.timer);
      if (message.error) task.reject(new Error(JSON.stringify(message.error))); else task.resolve(message.result);
    }
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails);
    if (message.method === 'Network.requestWillBeSent') requests.push(message.params.request.url);
    if (message.method === 'Network.loadingFailed') console.error('BROWSER_LOADING_FAILED',JSON.stringify(message.params));
  });
  ({ browserContextId } = await send('Target.createBrowserContext', {disposeOnDetach:true}));
  const { sessionId } = await openPage();
  await click(sessionId, '.control-card > summary');
  await click(sessionId, '.state-workbench > summary');
  await click(sessionId, '.telemetry-wrap > summary');
  let s = await readState(sessionId);
  const initialWorld = s.world;
  assert.equal(initialWorld.version, 1);
  assert.equal(s.bodyOverflow, false);
  await setControls(sessionId, {'flight-id':'DRAFT72','flight-x':-3.5,'flight-y':7.5,'flight-level':130,'flight-bearing':15,'flight-speed':155,'flight-climb':250});
  const draft = (await readState(sessionId)).draft;
  await runPlanner(sessionId);
  await click(sessionId, '#approve');
  const approved = await readState(sessionId);
  assert.match(approved.gates[1], /done/);
  assert.equal(approved.disabled.readback, false);
  checkpoints.approvedBeforeEdit = approved;
  pass('Actual local CPython planner creates an approvable world-bound proposal');

  await click(sessionId, '#edit-selected-track');
  s = await readState(sessionId);
  assert.equal(s.mode, 'EDIT TWR419'); assert.equal(s.idReadonly, true);
  assert.equal(s.active, 'flight-x'); assert.equal(s.draft['flight-bearing'], '270');
  assert.equal(s.draft['flight-speed'], '60');
  for (const id of ['run-planner','approve','readback','toggle-run','reset-world','policy-horizontal','load-world']) assert.equal(s.disabled[id], true, id);
  await key(sessionId, 'Tab', 'Tab', 9);
  assert.equal((await readState(sessionId)).active, 'flight-y');
  await key(sessionId, 'Tab', 'Tab', 9);
  assert.equal((await readState(sessionId)).active, 'flight-level');
  await key(sessionId, 'ArrowUp', 'ArrowUp', 38);
  assert.equal((await readState(sessionId)).draft['flight-level'], '110');
  await activateKeyboard(sessionId, '#preview-track-edit');
  s = await readState(sessionId);
  assert.deepEqual(s.world, initialWorld);
  assert.deepEqual(s.rows, [['TWR218 / TWR419','T+2.50–5.00 min','None']]);
  assert.equal(s.disabled['apply-track-edit'], false);
  checkpoints.altitudePreview = s;
  await activateKeyboard(sessionId, '#cancel-track-edit');
  s = await readState(sessionId);
  assert.deepEqual(s.world, initialWorld); assert.deepEqual(s.draft, draft);
  assert.equal(s.proposal, approved.proposal); assert.deepEqual(s.gates, approved.gates);
  assert.equal(s.disabled.readback, false); assert.equal(s.active, 'edit-selected-track');
  pass('Native Tab/ArrowUp/Enter previews analytic conflict removal; Cancel preserves exact world, draft and approval');

  await readback(sessionId, 4);
  s = await readState(sessionId);
  assert.equal(s.world.version, 2); assert.equal(s.audit.length, 4);
  assert.match(s.auditStatus, /VALID/);
  const actuated = s.world, auditPrefix = [...s.audit];
  checkpoints.firstActuation = s;
  pass('The proposal retained by Cancel actually passes Python readback and appends four valid audit events');

  await click(sessionId, '#edit-selected-track');
  await setControls(sessionId, {'flight-bearing':270,'flight-speed':60});
  await activateKeyboard(sessionId, '#preview-track-edit');
  s = await readState(sessionId);
  assert.match(s.preview, /0 current → 1 edited/);
  assert.deepEqual(s.world, actuated);
  await evaluate(sessionId, 'document.getElementById("flight-speed").focus()');
  await key(sessionId, 'ArrowUp', 'ArrowUp', 38);
  assert.equal((await readState(sessionId)).disabled['apply-track-edit'], true);
  await key(sessionId, 'ArrowDown', 'ArrowDown', 40);
  assert.equal((await readState(sessionId)).disabled['apply-track-edit'], true);
  await activateKeyboard(sessionId, '#preview-track-edit');
  await screenshot(sessionId, 'desktop-preview.png');
  await activateKeyboard(sessionId, '#apply-track-edit');
  s = await readState(sessionId);
  assert.equal(s.world.version, 3); assert.equal(s.world.observed_at, actuated.observed_at);
  assert.equal(s.world.aircraft[1].aircraft_id, 'TWR419');
  assert.deepEqual(s.world.aircraft[0], actuated.aircraft[0]);
  assert.equal(s.world.aircraft[1].vx_nm_min, -1);
  assert.ok(Math.abs(s.world.aircraft[1].vy_nm_min) < 1e-12);
  assert.deepEqual(s.audit, auditPrefix); assert.deepEqual(s.draft, draft);
  assert.equal(s.disabled.approve, true); assert.equal(s.disabled.readback, true);
  checkpoints.reintroducedConflict = s;
  pass('Apply advances one version, preserves the other track and audit, and rejects a preview after a native field change');

  await runPlanner(sessionId);
  await click(sessionId, '#approve');
  const staleProposal = await readState(sessionId);
  await click(sessionId, '#edit-selected-track');
  await setControls(sessionId, {'flight-x':5.5});
  await click(sessionId, '#preview-track-edit');
  await click(sessionId, '#apply-track-edit');
  s = await readState(sessionId);
  assert.equal(s.world.version, 4);
  assert.equal(s.world.aircraft[1].x_nm, 5.5);
  assert.deepEqual(s.world.aircraft[0], actuated.aircraft[0]);
  assert.deepEqual(s.audit, auditPrefix);
  assert.equal(s.proposalState, 'NEEDS REVIEW');
  assert.notEqual(s.proposal, staleProposal.proposal);
  assert.deepEqual(s.gates, ['gate-step wait','gate-step wait','gate-step wait']);
  assert.equal(s.disabled.approve, true); assert.equal(s.disabled.readback, true); assert.equal(s.disabled['run-planner'], false);
  checkpoints.clearedApprovedProposal = s;
  pass('Applying an edit while an approved proposal exists clears all previous proposal/approval gates without erasing history');

  await runPlanner(sessionId);
  s = await readState(sessionId);
  assert.notEqual(s.proposal, staleProposal.proposal);
  await click(sessionId, '#approve');
  await readback(sessionId, 8);
  s = await readState(sessionId);
  assert.equal(s.world.version, 5);
  assert.deepEqual(s.audit.slice(0,4), auditPrefix);
  await click(sessionId, '#verify-audit');
  await waitFor(sessionId, 'document.getElementById("audit-verdict").textContent==="HASH CHAIN VALID - 8 EVENTS"');
  checkpoints.finalActuation = await readState(sessionId);
  pass('Replanning the edited world runs actual Python actuation and retains the previous four-event audit prefix in an eight-event valid chain');

  const mobile = await openPage(390, 844);
  await click(mobile.sessionId, '.control-card > summary');
  await click(mobile.sessionId, '#edit-selected-track');
  await setControls(mobile.sessionId, {'flight-level':''});
  await activateKeyboard(mobile.sessionId, '#preview-track-edit');
  s = await readState(mobile.sessionId);
  assert.match(s.feedback, /NOT PREVIEWED: Every flight field must be a finite number/);
  assert.equal(s.disabled['apply-track-edit'], true);
  assert.deepEqual(s.world, initialWorld);
  await setControls(mobile.sessionId, {'flight-level':110});
  await activateKeyboard(mobile.sessionId, '#preview-track-edit');
  s = await readState(mobile.sessionId);
  assert.deepEqual(s.rows, [['TWR218 / TWR419','T+2.50–5.00 min','None']]);
  assert.equal(s.bodyOverflow, false);
  checkpoints.mobilePreview = s;
  await screenshot(mobile.sessionId, 'mobile-preview.png');
  await activateKeyboard(mobile.sessionId, '#apply-track-edit');
  s = await readState(mobile.sessionId);
  assert.equal(s.world.version, 2); assert.equal(s.world.aircraft[1].altitude_ft, 11000);
  assert.deepEqual(s.world.aircraft[0], initialWorld.aircraft[0]);
  assert.equal(s.active, 'edit-selected-track');
  pass('390px browser layout presents the interval table; invalid numeric input refuses Apply and corrected keyboard submission succeeds');

  assert.deepEqual(exceptions, []);
  assert.ok(requests.every(request => new URL(request).origin === new URL(url).origin));
  assert.ok(served.some(r => r.path.endsWith('/pyodide.asm.wasm')));
  assert.ok(served.some(r => r.path === '/python/towerops.py' && r.sha256 === before['towerops.py']));
  assert.deepEqual(await hashSources(), before);
  pass('Recorded page requests remain local, real Python/WASM assets were served, and all33 source files remain byte-identical');
  receipt = {status:'pass',receiver:'integration-72ac1419',browser:browserVersion,node:process.version,
    base:manifest.base,browserContextId,browserContextMode:'explicit disposable CDP context',checks,checkpoints,sourceSha256:before,served,requests,exceptions,
    viewports:[[1280,1000],[390,844]],actualBrowser:true,actualPythonWorker:true,
    serving:'isolated loopback static server',operationalAviationOrDeploymentClaimed:false};
} catch (error) {
  failure=error;
  receipt={status:'fail',receiver:'integration-72ac1419',browser:browserVersion,node:process.version,
    checks,checkpoints,error:String(error.stack||error),sourceSha256:before,served,requests,exceptions};
} finally {
  if (socket?.readyState === WebSocket.OPEN) await Promise.race([send('Browser.close').catch(() => {}), delay(3000)]);
  socket?.close();
  if (browser && browser.exitCode === null) {
    browser.kill('SIGTERM');
    await Promise.race([new Promise(resolve => browser.once('exit', resolve)), delay(4000)]);
    if (browser.exitCode === null) browser.kill('SIGKILL');
  }
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  await fs.rm(profile, {recursive:true,force:true,maxRetries:10,retryDelay:100});
  for (const task of pending.values()) clearTimeout(task.timer);
}
await fs.writeFile(path.join(evidenceDir,'browser-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({status:receipt.status,checks:receipt.checks,browser:browserVersion,error:receipt.error||null},null,2));
if (failure) throw failure;
