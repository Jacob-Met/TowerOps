"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const appPath = process.argv[2] || path.join(__dirname, "..", "web", "app.js");
const app = fs.readFileSync(appPath, "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
const copied = "Request settings copied. Run synthetic case to produce a new result; displayed result is unchanged.";
const catalog = {scenarios: [
  {id: "approved", label: "Approved", description: "Both synthetic fixtures"},
  {id: "missing_ack", label: "Missing acknowledgement", description: "No effective acknowledgement fixture"},
]};
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
const response = value => ({ok: true, json: async () => value});
const verdict = matches => ({matches, outcome: "rejected", note: "synthetic local reproduction"});
const saved = (request = {scenario: "missing_ack", include_approval: true, include_ack: true}) =>
  ({request, fixtures: {approval: {synthetic: true}, ack: null}, saved: "literal input"});
const file = (value, extra = {}) => ({size: 100, text: async () => JSON.stringify(value), ...extra});
function displayed(request = {scenario: "approved", include_approval: false, include_ack: false}) {
  return {request, label: "Retained A", disclaimer: "Synthetic only", outcome: "rejected",
    rejection_reason: "fixture missing", before_conflict: true, after_conflict: true,
    simulation_clock: {observed_sec: 1, dispatch_sec: 2}, before: {aircraft: []}, after: {aircraft: []},
    advisory: {literal: "retained"}, advisory_hash: "retained-hash", fixtures: {approval: null, ack: null},
    audit_valid: true, audit_head: "retained-head", audit_events: [{seq: 0, kind: "retained", payload: {a: 1}}]};
}

async function harness(options = {}) {
  const nodes = new Map(), calls = [], blobs = new Map(), downloads = [], revoked = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {
      id, textContent: "", value: "", checked: false, hidden: false, disabled: false,
      open: false, files: [], dataset: {}, attributes: {}, children: [], listeners: {},
      get options() { return this.children; },
      get selectedOptions() { return this.children.filter(item => item.value === this.value); },
      addEventListener(kind, listener) { this.listeners[kind] = listener; },
      append(...items) {
        this.children.push(...items);
        if (this.id === "scenario" && this.value === "" && this.children.length) this.value = this.children[0].value;
      },
      replaceChildren(...items) { this.children = items; },
      setAttribute(key, value) { this.attributes[key] = String(value); },
      click() { downloads.push({name: this.download, blob: blobs.get(this.href)}); },
      set innerHTML(_) { throw new Error("form settings are literal values, not markup"); },
    });
    return nodes.get(id);
  }
  const context = vm.createContext({document: {getElementById: node,
    createElement: () => node(Symbol()), createElementNS: () => node(Symbol()),
    createTextNode: text => ({textContent: text})},
    fetch: (url, init = {}) => {
      const body = init.body === undefined ? null : JSON.parse(init.body);
      if (url === "/api/scenarios") {
        calls.push({url, body});
        return options.catalogGate ? options.catalogGate.promise : Promise.resolve(response(catalog));
      }
      assert.ok(["/api/run", "/api/replay", "/api/replay/explain"].includes(url));
      const gate = deferred(); calls.push({url, body, gate}); return gate.promise;
    }, console, Blob,
    URL: {createObjectURL(blob) { const url = "blob:test-" + blobs.size; blobs.set(url, blob); return url; },
      revokeObjectURL(url) { revoked.push(url); }},
    setTimeout: listener => { listener(); return 0; }});
  vm.runInContext(app, context, {filename: appPath});
  await tick();
  // Exercise the production render/plot/export code for a retained completed run.
  context.initialDisplay = displayed();
  vm.runInContext("render(initialDisplay)", context);
  node("minute").value = "2.5"; node("minute").listeners.input();
  const choose = selected => {
    node("replay-file").files = selected ? [selected] : [];
    return node("replay-file").listeners.change();
  };
  const click = id => node(id).listeners.click();
  const last = () => calls.at(-1);
  async function accept(value = saved(), matches = true) {
    const pending = choose(file(value)); await tick();
    assert.equal(last().url, "/api/replay"); last().gate.resolve(response(verdict(matches))); await pending;
  }
  function plain(n) {
    return {text: n.textContent, value: n.value, checked: n.checked, hidden: n.hidden,
      disabled: n.disabled, open: n.open, className: n.className || "", attributes: n.attributes || {},
      children: (n.children || []).map(plain)};
  }
  const displayIds = ["result", "export", "minute", "minute-label", "before", "after", "outcome", "reason",
    "conflicts", "clock", "after-title", "advisory", "chain", "timeline", "status", "replay-status",
    "replay-explain", "replay-explain-status", "replay-differences", "replay-difference-summary",
    "replay-difference-list", "replay-difference-limit"];
  const snapshot = () => JSON.stringify({nodes: displayIds.map(id => [id, plain(node(id))]),
    current: vm.runInContext("JSON.stringify(current)", context)});
  const form = () => [node("scenario").value, node("approval").checked, node("ack").checked, node("description").textContent];
  async function exportText() {
    click("export"); const download = downloads.at(-1);
    assert.ok(download.blob); assert.equal(revoked.length, downloads.length);
    return {name: download.name, text: await download.blob.text()};
  }
  return {node, calls, context, choose, click, last, accept, snapshot, form, exportText};
}
function unavailable(h) {
  assert.equal(h.node("replay-use-settings").hidden, true);
  assert.equal(h.node("replay-use-settings").disabled, true);
  assert.equal(h.node("replay-settings-status").textContent, "");
}
function available(h) {
  assert.equal(h.node("replay-use-settings").hidden, false);
  assert.equal(h.node("replay-use-settings").disabled, false);
}

test("initial settings action is unavailable and cannot fetch or change the form", async () => {
  const h = await harness(), before = h.form(), calls = h.calls.length;
  unavailable(h); h.click("replay-use-settings"); unavailable(h);
  assert.deepEqual(h.form(), before); assert.equal(h.calls.length, calls);
});

test("MATCH copies request switches, not effective fixtures, without changing the displayed run or export", async () => {
  const h = await harness(), value = saved(); await h.accept(value); available(h);
  const before = h.snapshot(), exported = await h.exportText(), count = h.calls.length;
  h.node("replay-file").files = [{text() { throw new Error("copy must not reread the selected file"); }}];
  h.click("replay-use-settings");
  assert.deepEqual(h.form(), ["missing_ack", true, true, catalog.scenarios[1].description]);
  assert.equal(value.fixtures.ack, null); assert.equal(h.node("replay-settings-status").textContent, copied);
  assert.equal(h.calls.length, count); assert.equal(h.snapshot(), before);
  assert.deepEqual(await h.exportText(), exported);
});

test("MISMATCH copies exact false switches while retaining the complete open explanation", async () => {
  const h = await harness(), value = saved({scenario: "approved", include_approval: false, include_ack: false});
  await h.accept(value, false); const pending = h.click("replay-explain"); await tick();
  h.last().gate.resolve(response({differences: [{path: "/literal", kind: "unexpected", expected: {present: false},
    actual: {present: true, type: "string", value: "<b>literal λ</b>"}}], difference_limit: 32, differences_truncated: false}));
  await pending; const before = h.snapshot(), count = h.calls.length;
  h.node("approval").checked = true; h.node("ack").checked = true;
  h.click("replay-use-settings");
  assert.deepEqual(h.form(), ["approved", false, false, catalog.scenarios[0].description]);
  assert.equal(h.snapshot(), before); assert.equal(h.calls.length, count); available(h);
});

test("only explicit Run sends copied controls and the same accepted settings remain reusable", async () => {
  const h = await harness(); await h.accept(); h.click("replay-use-settings");
  assert.equal(h.calls.filter(call => call.url === "/api/run").length, 0);
  const pending = h.click("run"); await tick();
  assert.equal(h.last().url, "/api/run"); assert.deepEqual(h.last().body, saved().request);
  h.last().gate.resolve(response(displayed(saved().request))); await pending; available(h);
  h.node("scenario").value = "approved"; h.node("approval").checked = false; h.node("ack").checked = false;
  h.node("scenario").listeners.change(); const count = h.calls.length;
  h.click("replay-use-settings");
  assert.deepEqual(h.form(), ["missing_ack", true, true, catalog.scenarios[1].description]);
  assert.equal(h.calls.length, count); available(h);
});

test("new pending, clear, malformed and oversized selections retire copying without undoing prior form values", async () => {
  const h = await harness(); await h.accept(); h.click("replay-use-settings"); const copiedForm = h.form();
  const read = deferred(), pending = h.choose(file({}, {text: () => read.promise}));
  unavailable(h); assert.deepEqual(h.form(), copiedForm); h.click("replay-use-settings");
  await h.choose(null); unavailable(h); assert.deepEqual(h.form(), copiedForm);
  read.resolve(JSON.stringify(saved())); await pending; unavailable(h);
  await h.choose(file({}, {text: async () => "{"})); unavailable(h);
  await h.choose(file({}, {size: 262145, text() { throw new Error("oversized input must not be read"); }}));
  unavailable(h); assert.deepEqual(h.form(), copiedForm);
  assert.equal(h.calls.filter(call => call.url === "/api/replay").length, 1);
});

test("an old replay JSON body cannot restore settings after clear or supersede a newer accepted selection", async () => {
  for (const clear of [true, false]) {
    const h = await harness(), body = deferred();
    const old = h.choose(file(saved())); await tick();
    h.last().gate.resolve({ok: true, json: () => body.promise}); await tick();
    if (clear) await h.choose(null);
    else await h.accept(saved({scenario: "approved", include_approval: false, include_ack: true}), false);
    const status = h.node("replay-status").textContent, count = h.calls.length;
    body.resolve(verdict(true)); await old;
    assert.equal(h.node("replay-status").textContent, status); assert.equal(h.calls.length, count);
    if (clear) unavailable(h);
    else {
      available(h); h.click("replay-use-settings");
      assert.deepEqual(h.form(), ["approved", false, true, catalog.scenarios[0].description]);
    }
  }
});

test("late catalog readiness admits only the still-current accepted request", async () => {
  for (const clear of [false, true]) {
    const gate = deferred(), h = await harness({catalogGate: gate});
    await h.accept(); unavailable(h); const count = h.calls.length;
    if (clear) await h.choose(null);
    gate.resolve(response(catalog)); await tick(); assert.equal(h.calls.length, count);
    if (clear) unavailable(h);
    else { available(h); h.click("replay-use-settings"); assert.equal(h.node("scenario").value, "missing_ack"); }
  }
});

test("failed catalog, unknown scenarios and non-native request types never expose usable settings", async () => {
  const gate = deferred(), failed = await harness({catalogGate: gate}); await failed.accept();
  gate.reject(new Error("catalog unavailable")); await tick(); unavailable(failed);
  const h = await harness();
  for (const value of [
    {}, {request: null}, {request: []}, saved({scenario: "absent", include_approval: true, include_ack: true}),
    saved({scenario: "approved", include_approval: 1, include_ack: true}),
    saved({scenario: "approved", include_approval: true, include_ack: "false"}),
    saved({scenario: "approved", include_approval: true}),
    saved({scenario: "approved", include_approval: true, include_ack: true, extra: 0}),
  ]) {
    await h.accept(value); unavailable(h); const before = h.form(), count = h.calls.length;
    h.click("replay-use-settings"); assert.deepEqual(h.form(), before); assert.equal(h.calls.length, count);
  }
  await h.accept(saved(), "true"); unavailable(h);
});

test("current read and backend failures retire copying and corrected explicit selection recovers", async () => {
  const h = await harness(); await h.accept(); h.click("replay-use-settings");
  await h.choose(file({}, {text: async () => { throw new Error("read failed"); }})); unavailable(h);
  const pending = h.choose(file(saved())); await tick();
  h.last().gate.resolve({ok: false, status: 400, json: async () => ({error: "request refused"})});
  await pending; unavailable(h); assert.match(h.node("replay-status").textContent, /request refused/);
  await h.accept(); available(h); h.click("replay-use-settings");
  assert.equal(h.node("replay-settings-status").textContent, copied);
});

test("a retired replay transport error cannot hide or replace the newer usable request", async () => {
  const h = await harness(), old = h.choose(file(saved())); await tick(); const oldCall = h.last();
  await h.accept(saved({scenario: "approved", include_approval: false, include_ack: true}), false);
  const status = h.node("replay-status").textContent;
  oldCall.gate.reject(new Error("old transport failed")); await old;
  available(h); assert.equal(h.node("replay-status").textContent, status);
  h.click("replay-use-settings"); assert.deepEqual(h.form(), ["approved", false, true, catalog.scenarios[0].description]);
});
