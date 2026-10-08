import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,mkdir,writeFile,chmod,stat} from 'node:fs/promises';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
const [archiveArg,outArg]=process.argv.slice(2);
assert(archiveArg&&outArg,'Usage: node restore-receiving.mjs ARCHIVE NEW_OUTPUT');
const archive=JSON.parse(gunzipSync(await readFile(archiveArg)).toString('utf8'));
assert.equal(archive.schema,'towerops.receiving-byte-archive.v1');
const out=path.resolve(outArg);
await mkdir(out);
let count=0;
for(const entry of archive.entries){
 assert.equal(typeof entry.path,'string');
 assert(!path.isAbsolute(entry.path)&&!entry.path.split(/[\\/]/).includes('..'),'Unsafe archive path');
 const dest=path.resolve(out,entry.path);
 assert(dest.startsWith(out+path.sep));
 const body=Buffer.from(entry.content,entry.encoding);
 assert.equal(body.length,entry.bytes,entry.path+' length');
 assert.equal(createHash('sha256').update(body).digest('hex'),entry.sha256,entry.path+' SHA256');
 assert.equal(createHash('sha1').update(Buffer.from('blob '+body.length+'\0')).update(body).digest('hex'),entry.git_blob,entry.path+' Git blob');
 await mkdir(path.dirname(dest),{recursive:true});
 await writeFile(dest,body,{flag:'wx'});
 await chmod(dest,entry.mode==='100755'?0o755:0o644);
 assert.equal((await stat(dest)).size,entry.bytes);
 count++;
}
console.log(JSON.stringify({archive_schema:archive.schema,restored:count,out}));
