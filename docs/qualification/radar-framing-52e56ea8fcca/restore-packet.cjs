const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const [packetFile,destination]=process.argv.slice(2);
if(!packetFile||!destination)throw Error('Usage: node restore-packet.cjs native-receiving.json.gz NEW_DIRECTORY');
if(fs.existsSync(destination))throw Error('Destination must not already exist');
const packet=JSON.parse(zlib.gunzipSync(fs.readFileSync(packetFile)));
if(packet.schema!=='towerops-radar-native-packet/1')throw Error('Unexpected packet schema');
const checked=[];
for(const f of packet.files){
 if(typeof f.path!=='string'||path.isAbsolute(f.path)||f.path.split(/[\\/]/).includes('..')||f.encoding!=='base64')throw Error('Unsafe member');
 const b=Buffer.from(f.data,'base64'),sha=crypto.createHash('sha256').update(b).digest('hex'),git=crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex');
 if(b.length!==f.bytes||sha!==f.sha256||git!==f.git_blob)throw Error('Hash mismatch: '+f.path);
 checked.push([f.path,b]);
}
for(const[p,b]of checked){const target=path.join(destination,p);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,b,{flag:'wx'});}
console.log('Verified and restored '+checked.length+' files to '+destination);
