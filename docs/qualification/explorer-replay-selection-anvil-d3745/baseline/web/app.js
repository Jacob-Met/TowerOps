"use strict";
const $ = id => document.getElementById(id);
let current = null;
async function request(path, value) {
  const options = value === undefined ? {} : {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(value)};
  const response = await fetch(path, options), data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function svgElement(tag, attrs, text) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k,v] of Object.entries(attrs)) node.setAttribute(k,v);
  if (text !== undefined) node.textContent = text;
  return node;
}
function plot(id, state, minute) {
  const svg = $(id); svg.replaceChildren();
  const X = x => 50 + (x+6)*35, Y = y => 325-y*26;
  for (let x=-6;x<=6;x+=2) {
    svg.append(svgElement("line",{x1:X(x),y1:25,x2:X(x),y2:325,stroke:"#293952"}));
    svg.append(svgElement("text",{x:X(x),y:348,"text-anchor":"middle"},x));
  }
  for (let y=0;y<=10;y+=2) {
    svg.append(svgElement("line",{x1:50,y1:Y(y),x2:470,y2:Y(y),stroke:"#293952"}));
    svg.append(svgElement("text",{x:34,y:Y(y)+5,"text-anchor":"end"},y));
  }
  svg.append(svgElement("text",{x:255,y:377,"text-anchor":"middle"},"x / nautical miles (synthetic)"));
  svg.append(svgElement("text",{x:50,y:18},"y / nm • both at 10,000 fixture ft"));
  state.aircraft.forEach((a,index) => {
    const color = index===0 ? "#74d7cf" : "#eec277";
    svg.append(svgElement("line",{x1:X(a.x_nm),y1:Y(a.y_nm),x2:X(a.x_nm+a.vx_nm_min*5),y2:Y(a.y_nm+a.vy_nm_min*5),stroke:color,"stroke-width":3,"stroke-dasharray":"6 5"}));
    const x=X(a.x_nm+a.vx_nm_min*minute),y=Y(a.y_nm+a.vy_nm_min*minute);
    svg.append(svgElement("circle",{cx:x,cy:y,r:8,fill:color}));
    svg.append(svgElement("text",{x:Math.min(430,Math.max(60,x+12)),y:Math.max(42,y-14),fill:color},a.aircraft_id));
  });
}
function plots() {
  if (!current) return;
  const minute = Number($("minute").value);
  $("minute-label").value = `${minute.toFixed(1)} min`;
  plot("before", current.before, minute); plot("after", current.after, minute);
}
function render(data) {
  current=data; $("result").hidden=false; $("export").disabled=false;
  $("outcome").textContent = data.outcome==="rejected" ? "Rejected · no simulated actuation" : "Fixture accepted · simulated actuation only";
  $("outcome").className = data.outcome==="rejected" ? "rejected" : "";
  $("reason").textContent = data.rejection_reason ? `Engine reason: ${data.rejection_reason}` : "Exact-hash fixture approval and acknowledgement passed the engine gates.";
  $("conflicts").textContent = `Projected conflict: before ${data.before_conflict} → after ${data.after_conflict}`;
  $("clock").textContent = `Observation ${data.simulation_clock.observed_sec}s · dispatch ${data.simulation_clock.dispatch_sec}s (synthetic)`;
  $("after-title").textContent = data.outcome==="rejected" ? "After rejection · unchanged world" : "After simulated advisory";
  $("advisory").textContent=JSON.stringify({advisory:data.advisory,advisory_hash:data.advisory_hash,fixtures:data.fixtures},null,2);
  $("chain").textContent=`Local chain valid: ${data.audit_valid} · head ${data.audit_head}`;
  $("timeline").replaceChildren();
  data.audit_events.forEach(event => {
    const li=document.createElement("li"),title=document.createElement("strong"),payload=document.createElement("pre");
    title.textContent=`${event.seq+1}. ${event.kind}`; payload.textContent=JSON.stringify(event.payload,null,2);
    li.append(title,payload); $("timeline").append(li);
  });
  $("minute").value=0; plots();
}
$("scenario").addEventListener("change",()=> {
  $("description").textContent=$("scenario").selectedOptions[0].dataset.description;
  $("status").textContent="Selection changed. Run to produce a new result; displayed result still belongs to the previous run.";
});
$("minute").addEventListener("input",plots);
$("run").addEventListener("click",async()=> {
  $("run").disabled=true; $("status").textContent="Running local deterministic fixture…";
  try {
    const data=await request("/api/run",{scenario:$("scenario").value,include_approval:$("approval").checked,include_ack:$("ack").checked});
    render(data); $("status").textContent=`Result: ${data.label}. ${data.disclaimer}`;
  } catch(e) {$("status").textContent=`Run failed: ${e.message}`;}
  finally {$("run").disabled=false;}
});
$("export").addEventListener("click",()=> {
  if (!current) return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:"application/json"}));
  const a=document.createElement("a"); a.href=url; a.download=`towerops-${current.request.scenario}.json`; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$("replay-file").addEventListener("change",async()=> {
  const file=$("replay-file").files[0]; if (!file) return;
  $("replay-status").textContent="Replaying locally…";
  try {
    if(file.size>262144) throw new Error("Export exceeds 262144 bytes");
    const value=JSON.parse(await file.text()),reply=await request("/api/replay",value);
    $("replay-status").textContent = reply.matches ? `Replay MATCH: ${reply.outcome}. ${reply.note}` : `Replay MISMATCH: export differs from the deterministic engine result. ${reply.note}`;
  } catch(e) {$("replay-status").textContent=`Replay rejected: ${e.message}`;}
});
request("/api/scenarios").then(data=> {
  data.scenarios.forEach(item=> {const option=document.createElement("option"); option.value=item.id;option.textContent=item.label;option.dataset.description=item.description;$("scenario").append(option);});
  $("description").textContent=data.scenarios[0].description;
  $("status").textContent="Ready. Choose a case, then run the simulated fixtures.";
}).catch(e=> {$("status").textContent=`Load failed: ${e.message}`;$("run").disabled=true;});
