const fs = require('node:fs');
const path = require('node:path');
const binding = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const body = fs.readFileSync(path.join(__dirname, 'receiver-body.cjs'), 'utf8');
Function('require', 'SOURCE', 'PIN', body)(require, binding.source, binding.pin);
