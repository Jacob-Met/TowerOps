import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,mkdir,writeFile,chmod} from 'node:fs/promises';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
const [archivePath,outputPath]=process.argv.slice(2);
assert(archivePath&&outputPath,'Usage: node restore-receiving.mjs ARCHIVE NEW_DIRECTORY');
const archive=JSON.parse(gunzipSync(await readFile(archivePath)).toString('utf8'));
assert.equal(archive.schema,'towerops.receiving-deduplicated-archive.v1');
const payloads=new Map();
for(const entry of archive.blobs){
 const data=Buffer.from(entry.content,entry.encoding);
 assert.equal(data.length,entry.bytes,entry.sha256+' length');
 assert.equal(createHash('sha256').update(data).digest('hex'),entry.sha256);
 assert.equal(createHash('sha1').update(Buffer.from('blob '+data.length+'\0')).update(data).digest('hex'),entry.git_blob);
 assert(!payloads.has(entry.sha256),'Duplicate blob key');
 payloads.set(entry.sha256,data);
}
const output=path.resolve(outputPath);
await mkdir(output);
const written=new Set();
for(const entry of archive.aliases){
 assert.equal(typeof entry.path,'string');
 assert(!path.isAbsolute(entry.path)&&!entry.path.split(/[\\/]/).includes('..'),'Unsafe alias path');
 const target=path.resolve(output,entry.path);
 assert(target.startsWith(output+path.sep)&&!written.has(target));
 const data=payloads.get(entry.sha256);assert(data,'Missing alias payload');
 assert(entry.mode==='100644'||entry.mode==='100755');
 await mkdir(path.dirname(target),{recursive:true});
 await writeFile(target,data,{flag:'wx'});
 await chmod(target,entry.mode==='100755'?0o755:0o644);
 written.add(target);
}
console.log(JSON.stringify({restored_aliases:written.size,unique_blobs:payloads.size,output}));
