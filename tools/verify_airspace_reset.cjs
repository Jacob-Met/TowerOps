'use strict';
// Optional real-browser receiving: node tools/verify_airspace_reset.cjs DIST OUTPUT MAIN_TS CHROMIUM
// Requires an installed Playwright package and Chromium; it never reuses a user browser profile.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const { chromium } = require('playwright');
const [distArg, outputArg, sourceArg, browserPath] = process.argv.slice(2);
if (!distArg || !outputArg || !sourceArg || !browserPath) throw new Error('Provide DIST OUTPUT MAIN_TS CHROMIUM');
const dist = path.resolve(distArg), output = path.resolve(outputArg), source = path.resolve(sourceArg);
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
if (fs.existsSync(output)) throw new Error('Output directory already exists; preserve the previous receipt');
fs.mkdirSync(output, { recursive: true });
const sourceBytes = fs.readFileSync(source);
const receipt = { schema: 'towerops.reset-controls.browser.v1', source, source_sha256: sha(sourceBytes),
  harness_sha256: sha(fs.readFileSync(__filename)), dist, cases: [], errors: [],
  clock: 'Actual application requestAnimationFrame callbacks, stepped at 1000 and 1050 ms; no application state or calculation is replaced.' };
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.wasm': 'application/wasm', '.zip': 'application/zip', '.png': 'image/png' };
function filesIn(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(item => {
    const full = path.join(directory, item.name);
    return item.isDirectory() ? filesIn(full) : [{ path: path.relative(dist, full), sha256: sha(fs.readFileSync(full)) }];
  });
}
receipt.served_files = filesIn(dist);
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
  const file = path.resolve(dist, '.' + (pathname === '/' ? '/index.html' : pathname));
  if (!file.startsWith(dist + path.sep)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (error, data) => {
    if (error) { res.writeHead(404); return res.end('Missing'); }
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
});
async function snapshot(page) {
  return page.evaluate(() => {
    const value = id => document.getElementById(id).value;
    const text = id => document.getElementById(id).textContent;
    return { values: { speed: value('speed-range'), horizontal: value('policy-horizontal'),
      vertical: value('policy-vertical'), horizon: value('policy-horizon') },
      labels: { speed: text('speed-value'), horizontal: text('horizontal-value'),
        vertical: text('vertical-value'), horizon: text('horizon-value') },
      policy_stats: { horizontal: text('policy-stat-horizontal'), vertical: text('policy-stat-vertical'),
        horizon: text('policy-stat-horizon') }, run_button: text('toggle-run'),
      world: JSON.parse(value('world-json')) };
  });
}
async function advanceTraffic(page) {
  await page.locator('#toggle-run').click();
  await page.evaluate(() => window.__resetReceivingFrame(1000));
  await page.locator('#export-world').click();
  const origin = await snapshot(page); // Initial observations can predate the live simulation clock.
  await page.evaluate(() => window.__resetReceivingFrame(1050));
  await page.locator('#export-world').click();
  const current = await snapshot(page);
  current.frame_origin_observed_at = origin.world.observed_at;
  current.elapsed_seconds = current.world.observed_at - origin.world.observed_at;
  await page.locator('#toggle-run').click();
  return current;
}
async function openPage(browser, url, name) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'en-US' });
  page.on('pageerror', error => receipt.errors.push({ name, message: error.message }));
  page.on('response', response => {
    if (response.status() >= 400) receipt.errors.push({ name, status: response.status(), url: response.url() });
  });
  await page.addInitScript(() => {
    let next = 1;
    const callbacks = new Map();
    window.requestAnimationFrame = callback => { const id = next++; callbacks.set(id, callback); return id; };
    window.cancelAnimationFrame = id => callbacks.delete(id);
    window.__resetReceivingFrame = time => {
      const pending = [...callbacks.values()]; callbacks.clear();
      for (const callback of pending) callback(time);
    };
  });
  await page.goto(url);
  await page.waitForFunction(() => document.getElementById('world-json').value.startsWith('{'));
  await page.getByText('Shape the traffic', { exact: true }).click();
  await page.locator('.policy-editor > summary').click();
  await page.getByText('Inspect or load a WorldState', { exact: true }).click();
  return page;
}
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const url = 'http://127.0.0.1:' + server.address().port + '/';
  let browser;
  try {
    browser = await chromium.launch({ executablePath: browserPath, headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage'] });
    receipt.browser = browser.version();
    const control = await openPage(browser, url, 'fresh-control');
    const initial = await snapshot(control);
    const advanced = await advanceTraffic(control);
    const controlDelta = advanced.elapsed_seconds;
    receipt.cases.push({ name: 'fresh-control', initial, advanced, elapsed_seconds: controlDelta,
      checks: { default_controls: same(initial.values, { speed: '1', horizontal: '5', vertical: '1000', horizon: '5' }),
        default_labels: same(initial.labels, { speed: '1.0x', horizontal: '5.0 NM', vertical: '1,000 FT', horizon: '5.0 MIN' }),
        normal_traffic_projection: Math.abs(controlDelta - 3) < 1e-8 } });
    await control.close();
    for (const option of [{ name: 'fast-wide-policy', key: 'End', rate: 3 },
      { name: 'slow-narrow-policy', key: 'Home', rate: 0.5 }]) {
      const page = await openPage(browser, url, option.name);
      try {
        for (const id of ['speed-range', 'policy-horizontal', 'policy-vertical', 'policy-horizon']) {
          await page.locator('#' + id).focus();
          await page.locator('#' + id).press(option.key);
        }
        const tuned = await snapshot(page);
        const before = await advanceTraffic(page);
        const tunedDelta = before.elapsed_seconds;
        await page.locator('#reset-world').click();
        const reset = await snapshot(page);
        await page.locator('.speed-control').screenshot({ path: path.join(output, option.name + '-speed.png') });
        await page.locator('.policy-editor').screenshot({ path: path.join(output, option.name + '-policy.png') });
        const after = await advanceTraffic(page);
        const resetDelta = after.elapsed_seconds;
        receipt.cases.push({ name: option.name, tuned, tuned_elapsed_seconds: tunedDelta,
          reset, after, reset_elapsed_seconds: resetDelta,
          checks: { ordinary_rate_control_works: Math.abs(tunedDelta - 3 * option.rate) < 1e-8,
            sliders_reset: same(reset.values, initial.values), labels_reset: same(reset.labels, initial.labels),
            policy_resets: same(reset.policy_stats, initial.policy_stats),
            paused_after_reset: reset.run_button === 'Run traffic',
            world_resets: same(reset.world, initial.world),
            default_rate_restored: Math.abs(resetDelta - controlDelta) < 1e-8,
            default_traffic_projection_restored: same(after.world, advanced.world) } });
      } finally { await page.close(); }
    }
  } catch (error) { receipt.errors.push({ message: error.stack }); }
  finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  receipt.source_after_sha256 = sha(fs.readFileSync(source));
  if (receipt.source_after_sha256 !== receipt.source_sha256) receipt.errors.push({ message: 'Source changed during receiving' });
  for (const item of receipt.cases) item.passed = Object.values(item.checks).every(Boolean);
  receipt.passed = receipt.cases.filter(item => item.passed).length;
  receipt.failed = receipt.cases.length - receipt.passed;
  receipt.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(output, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify({ passed: receipt.passed, failed: receipt.failed,
    cases: receipt.cases.map(({ name, checks, elapsed_seconds, tuned_elapsed_seconds, reset_elapsed_seconds }) =>
      ({ name, checks, elapsed_seconds, tuned_elapsed_seconds, reset_elapsed_seconds })), errors: receipt.errors }, null, 2));
  process.exitCode = receipt.failed || receipt.errors.length || receipt.cases.length !== 3 ? 1 : 0;
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
