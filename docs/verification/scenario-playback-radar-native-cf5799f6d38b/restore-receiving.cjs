'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const [archiveArg,manifestArg,destinationArg]=process.argv.slice(2);
if(!archiveArg||!manifestArg||!destinationArg)throw new Error('node restore-receiving.cjs ARCHIVE MANIFEST NEW_DESTINATION');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const git=b=>crypto.createHash('sha1').update(Buffer.concat([Buffer.from('blob '+b.length+'\0'),b])).digest('hex');
const manifest=JSON.parse(fs.readFileSync(manifestArg)),bytes=fs.readFileSync(archiveArg);
if(bytes.length!==manifest.archive.bytes||hash(bytes)!==manifest.archive.sha256||git(bytes)!==manifest.archive.git_blob)throw new Error('Archive pin mismatch');
const packet=JSON.parse(zlib.gunzipSync(bytes)),destination=path.resolve(destinationArg);
if(fs.existsSync(destination))throw new Error('Destination must not exist');
if(packet.files.length!==manifest.members.length)throw new Error('Member count mismatch');
const validated=packet.files.map((item,index)=>{
 const expected=manifest.members[index],target=path.resolve(destination,item.path),data=Buffer.from(item.content_base64,'base64');
 if(item.path!==expected.path||!target.startsWith(destination+path.sep)||data.length!==expected.bytes||hash(data)!==expected.sha256||git(data)!==expected.git_blob)throw new Error('Member pin/path mismatch: '+item.path);
 return{target,data,mode:parseInt(expected.mode.slice(-3),8)};
});
fs.mkdirSync(destination);
for(const item of validated){fs.mkdirSync(path.dirname(item.target),{recursive:true});fs.writeFileSync(item.target,item.data,{flag:'wx',mode:item.mode});}
console.log(JSON.stringify({restored:validated.length,destination,archive_sha256:hash(bytes)}));
