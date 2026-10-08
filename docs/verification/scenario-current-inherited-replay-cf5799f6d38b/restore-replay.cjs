'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const [archiveArg,manifestArg,destinationArg]=process.argv.slice(2);
if(!archiveArg||!manifestArg||!destinationArg)throw Error('node restore-replay.cjs ARCHIVE MANIFEST NEW_DIRECTORY');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const git=b=>crypto.createHash('sha1').update(Buffer.concat([Buffer.from('blob '+b.length+'\0'),b])).digest('hex');
const bytes=fs.readFileSync(archiveArg),manifest=JSON.parse(fs.readFileSync(manifestArg));
if(bytes.length!==manifest.archive.bytes||sha(bytes)!==manifest.archive.sha256||git(bytes)!==manifest.archive.git_blob)throw Error('Archive pin mismatch');
const packet=JSON.parse(zlib.gunzipSync(bytes)),destination=path.resolve(destinationArg),seen=new Set();
if(fs.existsSync(destination))throw Error('Destination must not exist');
if(packet.files.length!==manifest.members.length)throw Error('Member count mismatch');
const prepared=packet.files.map((item,index)=>{
 const expected=manifest.members[index],target=path.resolve(destination,item.path);
 if(!['utf8','base64'].includes(item.encoding))throw Error('Unknown byte encoding');
 const body=Buffer.from(item.content,item.encoding);
 if(item.path!==expected.path||seen.has(item.path)||!target.startsWith(destination+path.sep)||body.length!==expected.bytes||sha(body)!==expected.sha256||git(body)!==expected.git_blob)throw Error('Member pin/path mismatch: '+item.path);
 seen.add(item.path);return{target,body,mode:parseInt(expected.mode.slice(-3),8)};
});
fs.mkdirSync(destination);
for(const item of prepared){fs.mkdirSync(path.dirname(item.target),{recursive:true});fs.writeFileSync(item.target,item.body,{flag:'wx',mode:item.mode});}
console.log(JSON.stringify({restored:prepared.length,destination,archive_sha256:sha(bytes)}));
