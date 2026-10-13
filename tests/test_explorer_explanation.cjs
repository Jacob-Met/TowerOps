"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const appPath = process.argv[2] || path.join(__dirname, "..", "web", "app.js");
const app = fs.readFileSync(appPath, "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
const response = value => ({ok: true, json: async () => value});
const verdict = matches => ({matches, outcome: "simulated_actuation", note: "local fixture"});
const comparison = (differences, truncated = false) => ({...verdict(false), differences,
  difference_limit: 32, differences_truncated: truncated});
const difference = {path: "/literal~1λ", kind: "unexpected", expected: {present: false},
  actual: {present: true, type: "object", value: {text: "<b>literal & λ</b>", flag: false, number: 1}}};

async function harness() {
  const nodes = new Map(), calls = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {id, textContent: "", value: "", hidden: false,
      disabled: false, open: false, files: [], dataset: {}, children: [], listeners: {},
      selectedOptions: [{dataset: {description: "fixture"}}],
      addEventListener(kind, listener) { this.listeners[kind] = listener; },
      append(...items) { this.children.push(...items); },
      replaceChildren(...items) { this.children = items; },
      setAttribute() {},
      set innerHTML(_) { throw new Error("literal values must not become markup"); },
    });
    return nodes.get(id);
  }
  const context = vm.createContext({document: {getElementById: node,
    createElement: () => node(Symbol()), createElementNS: () => node(Symbol()),
    createTextNode: text => ({textContent: text})},
    fetch: (url, options) => {
      if (url === "/api/scenarios") return Promise.resolve(response({scenarios: [
        {id: "approved", label: "Approved", description: "fixture"}]}));
      assert.ok(["/api/replay", "/api/replay/explain"].includes(url));
      const gate = deferred();
      calls.push({url, body: JSON.parse(options.body), gate});
      return gate.promise;
    }, console, setTimeout, URL, Blob});
  vm.runInContext(app, context, {filename: appPath});
  await tick();
  // A retained displayed run makes accidental clearing observable without a new run.
  vm.runInContext('current = {retained: "run"}', context);
  const unrelated = () => JSON.stringify([...nodes].filter(([id]) =>
    typeof id === "string" && !id.startsWith("replay-"))
    .map(([id, n]) => [id, n.textContent, n.value, n.disabled, n.hidden, n.children.length]));
  const before = unrelated();
  const choose = selected => {
    node("replay-file").files = selected ? [selected] : [];
    return node("replay-file").listeners.change();
  };
  async function accept(value, matches = false) {
    const pending = choose({size: 100, text: async () => JSON.stringify(value)});
    await tick(); calls.at(-1).gate.resolve(response(verdict(matches))); await pending;
  }
  return {calls, node, choose, accept,
    click: () => node("replay-explain").listeners.click(),
    status: () => node("replay-status").textContent,
    preserve() {
      assert.equal(unrelated(), before);
      assert.equal(vm.runInContext('JSON.stringify(current)', context), '{"retained":"run"}');
    }};
}
function flattened(node) {
  return [node, ...(node.children || []).flatMap(flattened)];
}
function cleared(h) {
  assert.equal(h.node("replay-explain").hidden, true);
  assert.equal(h.node("replay-explain").disabled, true);
  assert.equal(h.node("replay-explain-status").textContent, "");
  assert.equal(h.node("replay-differences").hidden, true);
  assert.equal(h.node("replay-differences").open, false);
  assert.equal(h.node("replay-difference-list").children.length, 0);
  assert.equal(h.node("replay-difference-limit").textContent, "");
}

test("only an explicit current mismatch click compares the captured parsed value", async () => {
  const h = await harness(); cleared(h); await h.click(); assert.equal(h.calls.length, 0);
  await h.accept({selected: "match"}, true); cleared(h); await h.click();
  assert.equal(h.calls.length, 1);
  const value = {selected: "mismatch", literal: "<b>λ</b>", flag: false};
  await h.accept(value); const status = h.status();
  assert.equal(h.calls.length, 2); assert.equal(h.node("replay-explain").hidden, false);
  h.node("replay-file").files = [{text: () => { throw new Error("must not reread"); }}];
  const pending = h.click(); await tick();
  assert.equal(h.node("replay-explain").disabled, true);
  await h.click(); assert.equal(h.calls.length, 3, "pending double click is ignored");
  assert.equal(h.calls[2].url, "/api/replay/explain"); assert.deepEqual(h.calls[2].body, value);
  h.calls[2].gate.resolve(response(comparison([difference]))); await pending;
  const row = h.node("replay-difference-list").children[0];
  const find = name => flattened(row).find(n => n.className === name).textContent;
  assert.equal(find("replay-path"), "/literal~1λ"); assert.equal(find("replay-kind"), "unexpected");
  assert.equal(find("replay-expected"), JSON.stringify({present: false}, null, 2));
  assert.equal(find("replay-actual"), JSON.stringify(difference.actual, null, 2));
  assert.equal(h.node("replay-differences").hidden, false);
  assert.equal(h.node("replay-differences").open, true);
  assert.equal(h.node("replay-explain").disabled, false);
  assert.equal(h.status(), status); h.preserve();
});

test("new file selection immediately retires old explanation success and finally", async () => {
  const h = await harness(); await h.accept({selected: "old"});
  const old = h.click(); await tick(); const oldCall = h.calls.at(-1);
  const fresh = h.choose({size: 20, text: async () => '{"selected":"new"}'});
  cleared(h); await tick(); h.calls.at(-1).gate.resolve(response(verdict(true))); await fresh;
  const status = h.status();
  oldCall.gate.resolve(response(comparison([difference]))); await old;
  cleared(h); assert.equal(h.status(), status); h.preserve();
});

test("clearing retires an old explanation failure without restoring controls", async () => {
  const h = await harness(); await h.accept({selected: "old"});
  const old = h.click(); await tick(); const oldCall = h.calls.at(-1);
  await h.choose(null); cleared(h); assert.equal(h.status(), "");
  oldCall.gate.reject(new Error("retired transport failure")); await old;
  cleared(h); assert.equal(h.status(), ""); h.preserve();
});

test("a current failure keeps the mismatch and permits an explicit same-selection retry", async () => {
  const h = await harness(), value = {selected: "retry"}; await h.accept(value);
  const status = h.status(); let pending = h.click(); await tick();
  h.calls.at(-1).gate.resolve({ok: false, status: 503, json: async () => ({error: "try again"})});
  await pending; assert.equal(h.status(), status);
  assert.match(h.node("replay-explain-status").textContent, /try again.*retry/);
  assert.equal(h.node("replay-explain").disabled, false);
  assert.equal(h.node("replay-differences").hidden, true);
  assert.equal(h.calls.length, 2);
  pending = h.click(); await tick(); assert.deepEqual(h.calls.at(-1).body, value);
  h.calls.at(-1).gate.resolve(response(comparison([difference]))); await pending;
  assert.equal(h.calls.length, 3); assert.equal(h.status(), status);
  assert.equal(h.node("replay-differences").hidden, false); h.preserve();
});

test("ordered typed rows retain full envelopes and expose the observed truncation", async () => {
  const h = await harness(); await h.accept({selected: "many"});
  const rows = Array.from({length: 32}, (_, i) => ({path: "/value/" + i, kind: "type",
    expected: {present: true, type: "boolean", value: false},
    actual: {present: true, type: "number", value: i}}));
  const pending = h.click(); await tick();
  h.calls.at(-1).gate.resolve(response(comparison(rows, true))); await pending;
  const rendered = h.node("replay-difference-list").children;
  assert.equal(rendered.length, 32);
  rendered.forEach((row, i) => {
    const values = flattened(row);
    assert.equal(values.find(n => n.className === "replay-path").textContent, rows[i].path);
    for (const side of ["expected", "actual"])
      assert.equal(values.find(n => n.className === "replay-" + side).textContent,
        JSON.stringify(rows[i][side], null, 2));
  });
  assert.equal(h.node("replay-difference-summary").textContent, "Field differences (32+)");
  assert.equal(h.node("replay-difference-limit").textContent, "Showing the first 32 differences; more were found.");
  await h.choose(null); cleared(h); h.preserve();
});
