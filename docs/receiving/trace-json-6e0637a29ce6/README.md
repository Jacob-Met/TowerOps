# Saved-trace duplicate-field repair: receiving evidence

Issue: [TowerOps #98](https://github.com/Jacob-Met/TowerOps/issues/98).
Original source: `a86b661ee66c19c2617ed9ee75e193ed6d0f21a8`.

`original-witness.json` retains seven literal ambiguous documents and their
actual unchanged Python-adapter and stdin-CLI results. Every document was
accepted before the repair, including an overwritten failed lifecycle. The
initial focused run produced **21 failures and 4 passes**: all duplicate-field
checks failed, and the valid-history controls passed.

Candidate qualification used CPython 3.12.14 and pytest 8.3.5:

- The new regression module passed all **25 tests**.
- The combined duplicate-field, decision-trace, audit-replay and world-linkage
  modules passed **68 tests**.
- The complete Python suite passed **206 tests**.
- Ruff 0.16.10 passed on both changed modules and the new regression module.
  Its first check required only formatting the new test's multiline import.
- The unchanged TypeScript/Vite build succeeded and copied the exact candidate
  native source into the distribution.

`pyodide-receiving.json` records execution of those exact built Python bytes in
Pyodide 0.27.7 (Python 3.12.7), hosted by Node. All seven ambiguous documents
were rejected, while valid empty history and an unknown-kind event with a
large integer, float, signed zero and literal Unicode retained a valid chain.
This is a native WebAssembly-runtime check; no real browser interaction or
deployed-site acceptance is claimed.

`pyodide-initial-harness-failure.json` retains the earlier Node initialization
failure. Node classified the browser-distribution JavaScript as ES modules,
where that Emscripten wrapper expected `require`. The corrected receiver used
the installed package's Node runtime to load the unchanged built product
Python bytes. No product or workflow file changed to make that receiver pass.

The environment's shared primary Python was read-only. The initial pytest
installation attempt failed without modifying it; test dependencies were
installed in a separate local virtual environment. No dependency declaration,
workflow, deployment, device, user history or provider was changed.

## Independent review

Teammate `research_delivery` independently reviewed the two frozen production
modules and authored distinct escaped-name attacks. One hides an illegal
actuation history behind a second wrapper field; the other hides a rejected
decision behind a later approval value. Valid complete four-event histories,
changed metadata, repeated names in separate objects, integers above 2**63 and
Unicode provide positive controls.

Each normal and optimized Python course used the native adapter, file/stdin
loaders and real CLI: original **8/16**, candidate **16/16**. The reviewer
approved the candidate and verified all three source modules stayed unchanged.
The `independent/` directory contains their exact original/candidate receipts
and unmodified receiver script. Its `.py.txt` suffix keeps historical receiving
code outside ordinary test/lint discovery; it can be replayed explicitly:

```bash
python3 docs/receiving/trace-json-6e0637a29ce6/independent/review_towerops.py.txt .
python3 -O docs/receiving/trace-json-6e0637a29ce6/independent/review_towerops.py.txt .
```

The reviewed production SHA-256 values are
`f31da5028a27ee51d389869db2a27cdaf82c102965c64e3381430fa69c627622`
for `audit_replay.py` and
`d85ad8b76eb43a8925c8fd16f9233928c5f6e7c8ae481d3754329ea33d683a97`
for `decision_trace.py`.
