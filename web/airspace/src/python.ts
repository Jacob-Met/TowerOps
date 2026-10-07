let worker:Worker|null=null,seq=0;
const calls=new Map<number,{resolve:(value:any)=>void;reject:(error:Error)=>void;timer:ReturnType<typeof setTimeout>}>();
export function towerPython(request:unknown):Promise<any>{
 if(!worker){worker=new Worker(new URL('./python-worker.ts',import.meta.url),{type:'module'});worker.onmessage=({data})=>{const call=calls.get(data.id);if(!call)return;clearTimeout(call.timer);calls.delete(data.id);if(data.error)call.reject(new Error(data.error));else call.resolve(data.result);};worker.onerror=()=>{for(const call of calls.values()){clearTimeout(call.timer);call.reject(new Error('Python worker could not start'));}calls.clear();worker?.terminate();worker=null;};}
 const id=++seq;
 return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{calls.delete(id);reject(new Error('Python load timed out. Retry when your connection is ready.'));},90000);calls.set(id,{resolve,reject,timer});worker!.postMessage({id,base:new URL('./',document.baseURI).href,request});});
}
