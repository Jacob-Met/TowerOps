import { canonicalJson } from './core';
export const ZERO_HASH='0'.repeat(64);
export interface AuditEvent { seq:number; kind:string; payload:Record<string,unknown>; prev_hash:string; event_hash:string }
async function digest(text:string):Promise<string> {
  const bytes=new TextEncoder().encode(text),raw=await globalThis.crypto.subtle.digest('SHA-256',bytes);
  return Array.from(new Uint8Array(raw),b=>b.toString(16).padStart(2,'0')).join('');
}
export class AuditLog {
  events:AuditEvent[]=[];
  async append(kind:string,payload:Record<string,unknown>):Promise<string> {
    const prev=this.events.at(-1)?.event_hash??ZERO_HASH;
    const body={seq:this.events.length,kind,payload,prev_hash:prev};
    const event_hash=await digest(prev+'\n'+canonicalJson(body));
    this.events.push({...body,event_hash}); return event_hash;
  }
  async verify():Promise<boolean> {
    let prev=ZERO_HASH;
    for(let i=0;i<this.events.length;i++){
      const {event_hash,...body}=this.events[i]!;
      if(body.seq!==i||body.prev_hash!==prev) return false;
      const actual=await digest(prev+'\n'+canonicalJson(body)); if(actual!==event_hash) return false; prev=actual;
    }
    return true;
  }
}
