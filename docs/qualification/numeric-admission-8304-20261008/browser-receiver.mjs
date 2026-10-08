// Exercise the built product worker and visible application, without source edits.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { createRequire } from 'node:module';

const [projectArg, casesArg, outputArg] = process.argv.slice(2);
const project = path.resolve(projectArg);
const dist = path.join(project, 'web/airspace/dist');
const input = JSON.parse(await fs.readFile(casesArg, 'utf8'));
const require = createRequire(import.meta.url);
const { chromium } = require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES, 'playwright'));
const localTmp = '/dev/shm/towerops-receiving-8304/tmp';
await fs.mkdir(localTmp, { recursive: true });
process.env.TMPDIR = localTmp;
const served = [], pageErrors = [], externalRequests = [], cases = [];
const mime = {'.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript', '.css':'text/css',
  '.json':'application/json', '.wasm':'application/wasm', '.zip':'application/zip', '.svg':'image/svg+xml'};
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const sourceBytes = await fs.readFile(path.join(project, 'towerops.py'));
const deployedBytes = await fs.readFile(path.join(dist, 'python/towerops.py'));
assert.deepEqual(deployedBytes, sourceBytes, 'build must deploy the exact native source');
const workerName = (await fs.readdir(path.join(dist, 'assets'))).find(n => /^python-worker-.*\.js$/.test(n));
assert.ok(workerName, 'compiled product worker exists');
const server = http.createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = path.resolve(dist, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!file.startsWith(dist + path.sep)) throw Error('outside receiver');
    const bytes = await fs.readFile(file);
    served.push({ path: pathname, size: bytes.length, sha256: hash(bytes) });
    res.writeHead(200, {'content-type': mime[path.extname(file)] || 'application/octet-stream', 'cache-control':'no-store'});
    res.end(bytes);
  } catch { res.writeHead(404); res.end('Unavailable'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const url = `http://127.0.0.1:${server.address().port}/`;
let browser, page, failure;
const receipt = { project, url, source_sha256: hash(sourceBytes), worker:workerName,
  worker_sha256:hash(await fs.readFile(path.join(dist, 'assets', workerName))), cases,
  page_errors:pageErrors, external_requests:externalRequests, served };
try {
  browser = await chromium.launch({ executablePath:'/dev/shm/towerops-receiving-8304/chromium',
    headless:true, args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'] });
  receipt.browser = browser.version();
  const context = await browser.newContext({ viewport:{width:1280,height:1000} });
  await context.route('**/*', async route => {
    const requestUrl = route.request().url();
    if (!requestUrl.startsWith(url)) { externalRequests.push(requestUrl); await route.abort(); }
    else await route.continue();
  });
  page = await context.newPage();
  page.on('pageerror', e => pageErrors.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('#world-json')?.value.includes('aircraft'));
  await page.evaluate(name => {
    const worker = new Worker('./assets/' + name, {type:'module'});
    let id = 0;
    const calls = new Map();
    worker.onmessage = ({data}) => { const done = calls.get(data.id); if(done){calls.delete(data.id); done(data);} };
    window.receivingCall = request => new Promise(resolve => { const n=++id; calls.set(n,resolve); worker.postMessage({id:n,base:location.href,request}); });
  }, workerName);
  for (const row of input.cases) {
    const result = await page.evaluate(async row => {
      if (row.numeric_wire) row.request.advisory.set_vx_nm_min = NaN;
      return await Promise.race([window.receivingCall(row.request), new Promise((_, reject) => setTimeout(() => reject(Error('worker timeout')), 90000))]);
    }, row);
    if (row.valid) assert.deepEqual(result.result, row.expected, row.name + ' native oracle parity');
    cases.push({ name:row.name, valid_control:row.valid, numeric_wire:row.numeric_wire, response:result });
    console.log(JSON.stringify({case:row.name,outcome:result.result?.error || (result.result?.state?'accepted':result.error)}));
  }
  // Normal UI import remains a separate admission boundary from direct worker calls.
  await page.locator('details.state-workbench > summary').click();
  const before = JSON.parse(await page.locator('#world-json').inputValue());
  const invalid = structuredClone(before);
  invalid.aircraft[0].x_nm = 'NaN';
  await page.locator('#world-json').fill(JSON.stringify(invalid));
  await page.locator('#load-world').click();
  await page.waitForFunction(() => document.querySelector('#world-json-feedback').textContent.startsWith('NOT LOADED:'));
  const invalidFeedback = await page.locator('#world-json-feedback').innerText();
  await page.locator('#export-world').click();
  assert.deepEqual(JSON.parse(await page.locator('#world-json').inputValue()), before, 'invalid UI import preserves world');
  assert.equal(await page.locator('#audit-events li').count(),0,'invalid UI import does not create an actuation');
  // Exercise the same worker through the actual app planner -> approve -> readback controls.
  await page.locator('#run-planner').click();
  await page.waitForFunction(() => !document.querySelector('#approve').disabled, null, {timeout:90000});
  const proposal = await page.locator('#proposal-output').innerText();
  await page.locator('#approve').click();
  await page.locator('#readback').click();
  await page.waitForFunction(() => document.querySelector('#python-status').textContent.includes('ControlRoom.apply'), null, {timeout:90000});
  const after = JSON.parse(await page.locator('#world-json').inputValue());
  assert.equal(after.version,before.version+1);
  assert.equal(await page.locator('#pair-count').innerText(),'0');
  assert.equal(await page.locator('#audit-events li').count(),4);
  await page.locator('details.telemetry-wrap > summary').click();
  await page.locator('#verify-audit').click();
  await page.waitForFunction(() => document.querySelector('#audit-verdict').textContent.includes('HASH CHAIN VALID'));
  receipt.ui = { invalid_import_feedback:invalidFeedback, invalid_import_preserves_state:true,
    before, after, proposal, audit:await page.locator('#audit-events li').allInnerTexts(),
    audit_status:await page.locator('#audit-status').innerText(), audit_verdict:await page.locator('#audit-verdict').innerText(),
    python_status:await page.locator('#python-status').innerText() };
  assert.deepEqual(pageErrors,[]);
  assert.deepEqual(externalRequests,[]);
  assert.ok(served.some(x => x.path === '/python/towerops.py' && x.sha256 === hash(sourceBytes)));
  console.log(JSON.stringify({ui:'valid native actuation and audit; invalid import preserved state',browser:receipt.browser}));
} catch (error) {
  failure=error;receipt.failure=String(error.stack||error);
  if(page) receipt.failure_ui = await page.evaluate(() => Object.fromEntries(
    ['python-status','proposal-output','world-json-feedback','audit-status'].map(id => [id,document.getElementById(id)?.textContent]))).catch(String);
}
finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
  receipt.source_unchanged = hash(await fs.readFile(path.join(project,'towerops.py'))) === hash(sourceBytes);
  await fs.writeFile(outputArg, JSON.stringify(receipt,null,2)+'\n');
}
if (failure) throw failure;
