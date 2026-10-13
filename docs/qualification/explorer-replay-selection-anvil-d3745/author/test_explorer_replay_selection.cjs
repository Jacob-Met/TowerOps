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
function file(value, overrides = {}) {
  return {name: "fixture.json", size: 20, text: async () => JSON.stringify(value), ...overrides};
}
function reply(matches, note = "current note") {
  return {matches, outcome: "rejected", note};
}
function response(data) {
  return {ok: true, json: async () => data};
}
async function harness() {
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {
      id, textContent: "", value: "", disabled: false, files: [], dataset: {},
      children: [], listeners: {}, selectedOptions: [{dataset: {description: "fixture"}}],
      addEventListener(kind, listener) { this.listeners[kind] = listener; },
      append(...items) { this.children.push(...items); },
      replaceChildren(...items) { this.children = items; },
      setAttribute() {},
    });
    return nodes.get(id);
  }
  const calls = [];
  const context = vm.createContext({
    document: {getElementById: node, createElement: () => node(Symbol()),
      createElementNS: () => node(Symbol())},
    fetch: (url, options) => {
      if (url === "/api/scenarios") return Promise.resolve(response({
        scenarios: [{id: "approved", label: "Approved", description: "fixture"}],
      }));
      assert.equal(url, "/api/replay");
      const gate = deferred();
      calls.push({url, body: JSON.parse(options.body), gate});
      return gate.promise;
    },
    console, setTimeout, URL, Blob,
  });
  vm.runInContext(app, context, {filename: appPath});
  await tick();
  const unrelated = () => JSON.stringify([...nodes].filter(([id]) =>
    typeof id === "string" && id !== "replay-file" && id !== "replay-status")
    .map(([id, n]) => [id, n.textContent, n.value, n.disabled, n.children.length]));
  const before = unrelated();
  return {
    calls, context,
    choose(selected) {
      node("replay-file").files = selected ? [selected] : [];
      return node("replay-file").listeners.change();
    },
    status: () => node("replay-status").textContent,
    preserve: () => {
      assert.equal(unrelated(), before, "replay does not alter other controls");
      assert.equal(vm.runInContext("current", context), null, "displayed run stays unchanged");
    },
  };
}

test("current match and mismatch keep their existing complete messages", async () => {
  const h = await harness();
  let pending = h.choose(file({id: "match"})); await tick();
  h.calls[0].gate.resolve(response(reply(true))); await pending;
  assert.equal(h.status(), "Replay MATCH: rejected. current note");
  pending = h.choose(file({id: "mismatch"})); await tick();
  h.calls[1].gate.resolve(response(reply(false))); await pending;
  assert.equal(h.status(), "Replay MISMATCH: export differs from the deterministic engine result. current note");
  h.preserve();
});

test("a superseded file read does not send a replay or replace the newer verdict", async () => {
  const h = await harness(), oldRead = deferred();
  const old = h.choose(file({}, {text: () => oldRead.promise}));
  const fresh = h.choose(file({id: "new"})); await tick();
  h.calls[0].gate.resolve(response(reply(false, "new file"))); await fresh;
  const accepted = h.status();
  oldRead.resolve(JSON.stringify({id: "old"})); await tick();
  // Settle an obsolete request if the original source issued it, without hanging the test.
  for (const call of h.calls.slice(1)) call.gate.resolve(response(reply(true, "old file")));
  await old;
  assert.equal(h.calls.length, 1, "old read must not reach the backend");
  assert.equal(h.status(), accepted);
  h.preserve();
});

test("a superseded file read error cannot replace current pending or completed status", async () => {
  const h = await harness(), oldRead = deferred();
  const old = h.choose(file({}, {text: () => oldRead.promise}));
  const fresh = h.choose(file({id: "new"})); await tick();
  oldRead.reject(new Error("old read error")); await old;
  assert.equal(h.status(), "Replaying locally…");
  h.calls[0].gate.resolve(response(reply(true))); await fresh;
  assert.equal(h.status(), "Replay MATCH: rejected. current note");
  h.preserve();
});

test("a superseded HTTP response cannot replace a newer mismatch", async () => {
  const h = await harness();
  const old = h.choose(file({id: "old"})); await tick();
  const fresh = h.choose(file({id: "new"})); await tick();
  h.calls[1].gate.resolve(response(reply(false, "new file"))); await fresh;
  const accepted = h.status();
  h.calls[0].gate.resolve(response(reply(true, "old file"))); await old;
  assert.equal(h.status(), accepted);
  h.preserve();
});

test("a superseded JSON body cannot replace a newer rejection", async () => {
  const h = await harness(), body = deferred();
  const old = h.choose(file({id: "old"})); await tick();
  h.calls[0].gate.resolve({ok: true, json: () => body.promise}); await tick();
  await h.choose(file({}, {text: async () => "{"}));
  const accepted = h.status();
  assert.match(accepted, /^Replay rejected:/);
  body.resolve(reply(true, "old body")); await old;
  assert.equal(h.status(), accepted);
  h.preserve();
});

test("a superseded transport error cannot replace a newer match", async () => {
  const h = await harness();
  const old = h.choose(file({id: "old"})); await tick();
  const fresh = h.choose(file({id: "new"})); await tick();
  h.calls[1].gate.resolve(response(reply(true))); await fresh;
  const accepted = h.status();
  h.calls[0].gate.reject(new Error("old network error")); await old;
  assert.equal(h.status(), accepted);
  h.preserve();
});

test("clearing selection retires an in-flight response and clears its status", async () => {
  const h = await harness();
  const old = h.choose(file({id: "old"})); await tick();
  await h.choose(null);
  assert.equal(h.status(), "");
  h.calls[0].gate.resolve(response(reply(true))); await old;
  assert.equal(h.status(), "");
  h.preserve();
});

test("selecting the same File again retires its earlier request", async () => {
  const h = await harness(), same = file({id: "same"});
  const old = h.choose(same); await tick();
  const fresh = h.choose(same); await tick();
  h.calls[1].gate.resolve(response(reply(false, "latest attempt"))); await fresh;
  const accepted = h.status();
  h.calls[0].gate.resolve(response(reply(true, "earlier attempt"))); await old;
  assert.equal(h.status(), accepted);
  h.preserve();
});

test("a current oversize or read failure refuses, and an explicit corrected selection recovers", async () => {
  const h = await harness();
  await h.choose(file({}, {size: 262145, text: () => { throw new Error("must not read"); }}));
  assert.equal(h.status(), "Replay rejected: Export exceeds 262144 bytes");
  assert.equal(h.calls.length, 0);
  await h.choose(file({}, {text: async () => { throw new Error("current read error"); }}));
  assert.equal(h.status(), "Replay rejected: current read error");
  const fresh = h.choose(file({id: "corrected"})); await tick();
  h.calls[0].gate.resolve(response(reply(true))); await fresh;
  assert.equal(h.status(), "Replay MATCH: rejected. current note");
  h.preserve();
});

test("a current backend refusal retains the existing error display", async () => {
  const h = await harness();
  const pending = h.choose(file({id: "current"})); await tick();
  h.calls[0].gate.resolve({ok: false, status: 400, json: async () => ({error: "current server refusal"})});
  await pending;
  assert.equal(h.status(), "Replay rejected: current server refusal");
  h.preserve();
});
