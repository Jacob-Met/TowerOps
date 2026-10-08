// Real-browser acceptance of the built Airspace Lab and bundled Pyodide.
// CI uses the existing Python Playwright driver; --chrome is a native override.
// node tools/verify_decision_trace.mjs --chrome /path/to/chrome \
//   --playwright /path/to/playwright/index.mjs --output /path/to/evidence
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile, writeFile, mkdir, readdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve, dirname, extname, sep} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, arg, index, all) => {
  if (index % 2 === 0) pairs.push([arg.replace(/^--/, ''), all[index + 1]]);
  return pairs;
}, []));
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = resolve(root, 'web/airspace/dist');
const output = resolve(args.output ?? 'decision-trace-browser-evidence');
const python = process.env.TOWEROPS_PYTHON ?? 'python3';
const {chromium} = await import(args.playwright ? pathToFileURL(resolve(args.playwright)).href : 'playwright');
await mkdir(output, {recursive: true});
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const receipt = {source_root: root, node: process.version, platform: process.platform, arch: process.arch, controls: [], page_errors: [], console_errors: [], requests_failed: [], served_files: []};
for (const file of ['audit_replay.py', 'decision_trace.py', 'towerops.py', 'web/airspace/src/python-worker.ts', 'web/airspace/src/python.ts', 'web/airspace/src/audit.ts', 'web/airspace/src/core.ts', 'web/airspace/src/main.ts', 'web/airspace/src/decision-trace.ts', 'web/airspace/src/decision-trace.css', 'web/airspace/index.html', 'web/airspace/package-lock.json', 'tools/verify_decision_trace.mjs']) {
  const bytes = await readFile(resolve(root, file));
  (receipt.source_files ??= []).push({path: file, bytes: bytes.length, sha256: sha256(bytes)});
}
async function files(directory, prefix = '') {
  const found = [];
  for (const entry of await readdir(directory, {withFileTypes: true})) {
    const relative = prefix + entry.name;
    if (entry.isDirectory()) found.push(...await files(resolve(directory, entry.name), relative + '/'));
    else {const bytes = await readFile(resolve(directory, entry.name)); found.push({path: relative, bytes: bytes.length, sha256: sha256(bytes)});}
  }
  return found;
}
receipt.served_files = await files(dist);
const mime = {'.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.wasm': 'application/wasm', '.json': 'application/json', '.py': 'text/plain', '.svg': 'image/svg+xml', '.zip': 'application/zip'};
const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
    const path = resolve(dist, '.' + (pathname.endsWith('/') ? pathname + 'index.html' : pathname));
    if (!path.startsWith(dist + sep)) throw new Error('outside built site');
    const bytes = await readFile(path);
    response.writeHead(200, {'content-type': mime[extname(path)] ?? 'application/octet-stream', 'content-length': bytes.length});
    response.end(bytes);
  } catch {response.writeHead(404); response.end('Not found');}
});
await new Promise(resolveReady => server.listen(0, '127.0.0.1', resolveReady));
const address = `http://127.0.0.1:${server.address().port}/`;
const browser = await chromium.launch({headless: true, executablePath: args.chrome || undefined});
receipt.browser = await browser.version();
receipt.url = address;
receipt.python = execFileSync(python, ['--version'], {encoding: 'utf8'}).trim();

async function pageFor(context, label) {
  const page = await context.newPage();
  page.setDefaultTimeout(30_000);
  page.on('pageerror', error => receipt.page_errors.push({page: label, message: String(error)}));
  page.on('console', message => {if (message.type() === 'error') receipt.console_errors.push({page: label, message: message.text(), location: message.location()});});
  page.on('requestfailed', request => receipt.requests_failed.push({page: label, url: request.url(), error: request.failure()?.errorText}));
  // Observe the real existing Worker; do not replace its execution or replies.
  await page.addInitScript(() => {
    const NativeWorker = window.Worker;
    window.__traceWorkerCalls = [];
    window.__traceWorkerCount = 0;
    window.Worker = class extends NativeWorker {
      constructor(...values) {
        super(...values); window.__traceWorkerCount++;
        this.addEventListener('message', event => {
          const call = window.__traceWorkerCalls.findLast(item => item.id === event.data.id && !item.response);
          if (call) call.response = structuredClone(event.data);
        });
      }
      postMessage(value, ...rest) {
        window.__traceWorkerCalls.push(structuredClone(value));
        return super.postMessage(value, ...rest);
      }
    };
  });
  await page.goto(address, {waitUntil: 'networkidle'});
  await page.locator('.telemetry-wrap > summary').click();
  return page;
}

async function live(page) {
  return page.evaluate(() => ({
    world: document.getElementById('world-json').value,
    policy: ['policy-horizontal', 'policy-vertical', 'policy-horizon'].map(id => document.getElementById(id).value),
    proposal: document.getElementById('proposal-output').textContent,
    gates: ['gate-screen', 'gate-approval', 'gate-ack'].map(id => document.getElementById(id).textContent),
    audit: document.getElementById('audit-events').textContent,
    audit_status: document.getElementById('audit-status').textContent,
    clock: document.getElementById('sim-clock').textContent,
    selected: document.getElementById('edit-selected-track').textContent,
    readback_disabled: document.getElementById('readback').disabled,
  }));
}

async function lastReview(page) {
  const call = await page.evaluate(() => window.__traceWorkerCalls.findLast(item => item.request.op === 'review_trace'));
  assert.deepEqual(Object.keys(call.request).sort(), ['op', 'trace_json']);
  return call.response?.result;
}

function nativeReport(path) {
  return JSON.parse(execFileSync(python, ['-c', 'import json,sys; from decision_trace import review_trace; print(json.dumps(review_trace(open(sys.argv[1], encoding="utf-8").read()), ensure_ascii=False))', path], {cwd: root, encoding: 'utf8'}));
}

async function openAndReview(page, path, verdict) {
  await page.locator('#open-trace-file').setInputFiles(path);
  await page.waitForFunction(() => !document.getElementById('review-opened-trace').disabled);
  const before = await live(page);
  await page.locator('#review-opened-trace').click();
  if (verdict === 'error') await page.waitForFunction(() => document.getElementById('decision-trace-feedback').textContent.startsWith('NOT REVIEWED:'));
  else await page.waitForFunction(expected => document.getElementById('decision-trace-result').dataset.verdict === expected && document.getElementById('decision-trace-feedback').textContent.startsWith('Review complete'), verdict);
  assert.deepEqual(await live(page), before, 'trace review must preserve the paused live world, proposal, approval and audit');
  const result = await lastReview(page);
  if (verdict !== 'error') assert.deepEqual(result, nativeReport(path));
  else {assert.deepEqual(Object.keys(result), ['error']); assert(!result.error.includes('Traceback'));}
  return result;
}

async function control(name, run) {
  try {const detail = await run(); receipt.controls.push({name, passed: true, detail}); console.log(`PASS ${name}`);}
  catch (error) {receipt.controls.push({name, passed: false, error: String(error), stack: error.stack}); throw error;}
}

try {
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}, acceptDownloads: true});
  const page = await pageFor(context, 'main');
  const downloaded = resolve(output, 'downloaded-native-trace.json');
  await control('actual planner approval readback, native review and exact download', async () => {
    await page.locator('#run-planner').click();
    await page.waitForFunction(() => !document.getElementById('approve').disabled);
    await page.locator('#approve').click(); await page.locator('#readback').click();
    await page.waitForFunction(() => document.getElementById('gate-ack').textContent.includes('ACCEPTED') && document.getElementById('audit-status').textContent.includes('4 EVENTS / VALID'));
    const applied = await page.evaluate(() => window.__traceWorkerCalls.findLast(item => item.request.op === 'apply').response.result);
    await page.locator('#verify-audit').click();
    await page.waitForFunction(() => document.getElementById('audit-verdict').textContent === 'HASH CHAIN VALID - 4 EVENTS');
    const before = await live(page);
    await page.locator('#review-current-trace').click();
    await page.waitForFunction(() => document.getElementById('decision-trace-result').dataset.verdict === 'valid' && document.getElementById('decision-trace-feedback').textContent.startsWith('Review complete'));
    assert.deepEqual(await live(page), before);
    const download = page.waitForEvent('download');
    await page.locator('#download-current-trace').click(); await (await download).saveAs(downloaded);
    assert.equal(await readFile(downloaded, 'utf8'), applied.audit_json);
    assert.deepEqual(await lastReview(page), nativeReport(downloaded));
    const cli = JSON.parse(execFileSync(python, ['audit_replay.py', downloaded], {cwd: root, encoding: 'utf8'}));
    assert(cli.ok && cli.chain_valid && cli.actuated === 1);
    return {events: applied.events.length, visible_chain_verdict: await page.locator('#audit-verdict').textContent(), downloaded_sha256: sha256(await readFile(downloaded)), native_cli: cli};
  });

  execFileSync(python, ['-c', `
import copy,json,pathlib,sys
from towerops import AuditLog
events=json.loads(pathlib.Path(sys.argv[1]).read_text()); output=pathlib.Path(sys.argv[2])
def save(name, data): (output/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
def rehash(items):
    log=AuditLog()
    for e in items: log.append(e['kind'],e['payload'])
    return log.events
save('unapproved.json',rehash([e for e in events if e['kind']!='approval']))
changed=copy.deepcopy(events);changed[3]['payload']['before_world_hash']='f'*64;save('wrong-world.json',rehash(changed))
save('wrong-order.json',rehash([events[0],events[2],events[1],events[3]]))
changed=copy.deepcopy(events);changed[1]['payload']['approver']='changed without rehash';save('tampered.json',changed)
changed=copy.deepcopy(events);changed[1]['payload']['approver']='<img src=x onerror="window.__traceInjected=true">';save('literal-label.json',rehash(changed))
save('native-demo.json',{'audit_events':events,'scenario':'saved native demo'})
save('malformed.json',[None]);save('too-many.json',[{}]*5001)
(output/'too-large.json').write_text(' '*(2*1024*1024+1),encoding='utf-8')
`, downloaded, output], {cwd: root, encoding: 'utf8'});

  await control('saved file reopened while another world-bound approval remains pending', async () => {
    await page.locator('#reset-world').click();
    await page.locator('.control-card > summary').click();
    await page.locator('#perturb-track').click();
    await page.locator('#run-planner').click(); await page.waitForFunction(() => !document.getElementById('approve').disabled);
    await page.locator('#approve').click();
    assert.equal((await live(page)).readback_disabled, false);
    await openAndReview(page, downloaded, 'valid');
    const download = page.waitForEvent('download'); await page.locator('#download-current-trace').click();
    const currentPath = resolve(output, 'live-trace-after-reopen.json'); await (await download).saveAs(currentPath);
    assert.equal(await readFile(currentPath, 'utf8'), '[]');
    return {opened_events: (await lastReview(page)).event_count, retained_live_trace: '[]', pending_readback_preserved: true};
  });
  for (const name of ['unapproved.json', 'wrong-world.json', 'wrong-order.json']) {
    await control(`hash-valid decision issue: ${name}`, async () => {
      const result = await openAndReview(page, resolve(output, name), 'semantic-invalid');
      assert(result.chain_valid && !result.ok && result.issues.length);
      return {issues: result.issues};
    });
  }
  await control('tampered hash chain', async () => {
    const result = await openAndReview(page, resolve(output, 'tampered.json'), 'chain-invalid');
    assert(!result.chain_valid && !result.ok && !result.advisories.length);
    return result.issues;
  });
  await control('malformed and excessive event files return short errors without state adoption', async () => {
    const errors = [];
    for (const name of ['malformed.json', 'too-many.json']) errors.push((await openAndReview(page, resolve(output, name), 'error')).error);
    return errors;
  });
  await control('file byte limit refuses before a native request', async () => {
    const before = await live(page), calls = await page.evaluate(() => window.__traceWorkerCalls.length);
    await page.locator('#open-trace-file').setInputFiles(resolve(output, 'too-large.json'));
    await page.waitForFunction(() => document.getElementById('decision-trace-feedback').textContent.startsWith('NOT OPENED:'));
    assert(await page.locator('#review-opened-trace').isDisabled());
    assert.equal(await page.evaluate(() => window.__traceWorkerCalls.length), calls);
    assert.deepEqual(await live(page), before);
    return {native_requests_started: 0};
  });
  await control('native labels stay literal and mobile review fits', async () => {
    await openAndReview(page, resolve(output, 'literal-label.json'), 'valid');
    const result = page.locator('#decision-trace-result');
    await result.locator('details > summary').first().click();
    assert((await result.textContent()).includes('<img src=x onerror="window.__traceInjected=true">'));
    assert.equal(await result.locator('img,script').count(), 0);
    assert.equal(await page.evaluate(() => window.__traceInjected ?? false), false);
    await page.locator('.audit-panel').screenshot({path: resolve(output, 'desktop-trace.png')});
    await page.setViewportSize({width: 390, height: 844});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await page.locator('.audit-panel').screenshot({path: resolve(output, 'mobile-trace.png')});
    await page.setViewportSize({width: 1440, height: 1000});
    return {literal_text: true, viewport: {width: 390, height: 844}};
  });
  await control('demo document compatibility and later native apply retain the live audit', async () => {
    await openAndReview(page, resolve(output, 'native-demo.json'), 'valid');
    await page.locator('#readback').click();
    await page.waitForFunction(() => document.getElementById('gate-ack').textContent.includes('ACCEPTED') && document.getElementById('audit-status').textContent.includes('4 EVENTS / VALID'));
    const actual = await page.evaluate(() => window.__traceWorkerCalls.findLast(item => item.request.op === 'apply').response.result);
    await page.locator('#verify-audit').click();
    await page.waitForFunction(() => document.getElementById('audit-verdict').textContent === 'HASH CHAIN VALID - 4 EVENTS');
    assert.equal(actual.events.length, 4); assert.equal(actual.events[0].seq, 0);
    assert.equal(await readFile(downloaded, 'utf8'), await page.evaluate(() => window.__traceWorkerCalls.find(item => item.request.op === 'apply').response.result.audit_json));
    return {new_live_events: actual.events.length, imported_history_adopted: false, visible_chain_verdict: await page.locator('#audit-verdict').textContent()};
  });
  await context.close();

  await control('missing optional replay source preserves planning and an explicit retry succeeds', async () => {
    const retryContext = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const route = '**/python/audit_replay.py';
    await retryContext.route(route, request => request.abort('failed'));
    const retryPage = await pageFor(retryContext, 'missing-replay-source');
    const before = await live(retryPage);
    await retryPage.locator('#review-current-trace').click();
    await retryPage.waitForFunction(() => document.getElementById('decision-trace-feedback').textContent.startsWith('NOT REVIEWED:'));
    assert.deepEqual(await live(retryPage), before);
    await retryPage.locator('#run-planner').click(); await retryPage.waitForFunction(() => !document.getElementById('approve').disabled);
    await retryContext.unroute(route);
    const pending = await live(retryPage);
    await retryPage.locator('#review-current-trace').click();
    await retryPage.waitForFunction(() => document.getElementById('decision-trace-result').dataset.verdict === 'empty' && document.getElementById('decision-trace-feedback').textContent.startsWith('Review complete'));
    assert.deepEqual(await live(retryPage), pending);
    const workers = await retryPage.evaluate(() => window.__traceWorkerCount);
    assert.equal(workers, 1);
    await retryContext.close();
    return {real_workers: workers, planner_available: true, retry_report: 'empty trace'};
  });
  assert.deepEqual(receipt.page_errors, []);
  assert(receipt.requests_failed.every(item => item.page === 'missing-replay-source' && item.url.endsWith('/python/audit_replay.py')));
  assert(receipt.console_errors.every(item => item.page === 'missing-replay-source' && item.location?.url.endsWith('/python/audit_replay.py')));
  receipt.passed = true;
} catch (error) {
  receipt.passed = false; receipt.error = String(error); process.exitCode = 1;
} finally {
  await browser.close();
  await new Promise(resolveClosed => server.close(resolveClosed));
  await writeFile(resolve(output, 'browser-receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify({passed: receipt.passed, controls: receipt.controls.length, output, error: receipt.error}));
}
