import {copyFileSync,mkdirSync} from 'node:fs';
// Deploy the exact repository source, not a fork or generated substitute.
mkdirSync('public/python',{recursive:true});
copyFileSync('../../towerops.py','public/python/towerops.py');
for(const name of ['audit_replay.py','decision_trace.py']) copyFileSync(`../../${name}`,`public/python/${name}`);
for(const name of ['pyodide.mjs','pyodide.asm.js','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json']) copyFileSync(`node_modules/pyodide/${name}`,`public/python/${name}`);
