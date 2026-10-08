import { canonicalJson } from './core';
export const ZERO_HASH='0'.repeat(64);
export interface AuditEvent { seq:number; kind:string; payload:Record<string,unknown>; prev_hash:string; event_hash:string }

// Parsing JSON loses Python's int/float spelling. Keep the original hash inputs
// beside the received array, without adding transport fields to native events.
const receivedBodies = new WeakMap<AuditEvent[], unknown>();
export function rememberPythonAudit(events:AuditEvent[], canonicalBodies:unknown):void {
  receivedBodies.set(events, Array.isArray(canonicalBodies) ? [...canonicalBodies] : canonicalBodies);
}

async function digest(text:string):Promise<string> {
  const bytes=new TextEncoder().encode(text),raw=await globalThis.crypto.subtle.digest('SHA-256',bytes);
  return Array.from(new Uint8Array(raw),b=>b.toString(16).padStart(2,'0')).join('');
}
export class AuditLog {
  events:AuditEvent[]=[];
  async append(kind:string,payload:Record<string,unknown>):Promise<string> {
    const prev=this.events.at(-1)?.event_hash??ZERO_HASH;
    const body={seq:this.events.length,kind,payload,prev_hash:prev};
    const canonical=canonicalJson(body);
    const event_hash=await digest(prev+'\n'+canonical);
    this.events.push({...body,event_hash});
    const source=receivedBodies.get(this.events);
    if(Array.isArray(source)&&source.length===body.seq)source.push(canonical);
    return event_hash;
  }
  async verify():Promise<boolean> {
    const events=this.events;
    const received=receivedBodies.has(events),source=receivedBodies.get(events);
    if(received&&(!Array.isArray(source)||source.length!==events.length))return false;
    let prev=ZERO_HASH;
    try {
      for(let i=0;i<events.length;i++){
        const {event_hash,...body}=events[i]!;
        if(body.seq!==i||body.prev_hash!==prev) return false;
        let canonical=canonicalJson(body);
        if(received){
          const original=(source as unknown[])[i];
          if(typeof original!=='string')return false;
          // A valid preimage alone cannot vouch for an altered displayed payload.
          if(canonicalJson(JSON.parse(original))!==canonical)return false;
          canonical=original;
        }
        const actual=await digest(prev+'\n'+canonical);
        if(actual!==event_hash) return false;
        prev=actual;
      }
    } catch {
      return false;
    }
    return true;
  }
}
