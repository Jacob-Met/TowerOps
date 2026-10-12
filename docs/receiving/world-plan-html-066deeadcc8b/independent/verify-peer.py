#!/usr/bin/env python3
"""Cold verification of saved native evidence only. Never import/run product or browser."""
import argparse, ast, base64, copy, hashlib, io, json, tarfile
from pathlib import Path, PurePosixPath

PREFIX="/home/jacob/hamon-product-066deeadcc8b/towerops-review/"
def require(ok, label):
    if not ok: raise ValueError(label)
def pin(b):
    return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),
            "git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
def samepin(b,p,label):
    a=pin(b)
    require(all(a[k]==v for k,v in p.items() if k in a),label)
def relative(p):
    if p.startswith(PREFIX):return p[len(PREFIX):]
    require(not p.startswith("/") and ".." not in PurePosixPath(p).parts,"foreign artifact path")
    return p
def dump(x,**kw):return json.dumps(x,ensure_ascii=False,allow_nan=False,**kw)
def text(x):return x if isinstance(x,str) else dump(x)
def load_packet(folder):
    manifest=json.loads((folder/"native-manifest.json").read_text())
    samepin((folder/"native-peer.tar.xz").read_bytes(),json.loads((folder/"archive-freeze.json").read_text())["archive"],"archive freeze")
    files={}
    with tarfile.open(folder/"native-peer.tar.xz","r:xz") as t:
        for m in t:
            require(m.isfile() and m.name not in files and not m.name.startswith("/") and ".." not in PurePosixPath(m.name).parts,"nonordinary or duplicate archive member")
            require(m.name in manifest["files"] and ("100755" if m.mode & 0o111 else "100644")==manifest["files"][m.name]["mode"],"archive member mode")
            files[m.name]=t.extractfile(m).read()
    require(set(files)==set(manifest["files"]),"archive inventory")
    for n,b in files.items():samepin(b,manifest["files"][n],"archive bytes "+n)
    return files
def semantic(files):
    def raw(n):return files[relative(n)]
    def obj(n):return json.loads(raw(n))
    result={"format":"towerops-independent-cold-verification-v1","product_execution":False,
            "browser_execution":False,"archive_members":len(files)}
    custody=obj("source-custody.json")
    require(custody["primary_commit"]=="89529c5459b1c3d52448e197de2b2f7fe8b6d128","baseline commit")
    for e in custody["primary_baseline_entries"]:
        samepin(raw("baseline-complete/"+e["path"]),e,"baseline primary blob "+e["path"])
    require(len(custody["primary_baseline_entries"])==33,"33 baseline files")
    scope=set(custody["scope_paths"])
    for e in custody["primary_baseline_entries"]:
        if e["path"] not in scope:
            require(raw("candidate/"+e["path"])==raw("baseline-complete/"+e["path"]),"unowned source "+e["path"])
    baseline=raw("baseline-complete/plan_world.py").decode()
    candidate=raw("candidate/plan_world.py").decode()
    def defs(s):
        lines=s.splitlines(keepends=True)
        return {n.name:"".join(lines[n.lineno-1:n.end_lineno]) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    bd,cd=defs(baseline),defs(candidate)
    require(set(bd)==set(cd) and all(bd[n]==cd[n] for n in bd if n!="main"),"unchanged producer definitions")
    result["source"]={"baseline_files":33,"candidate_files":36,"unowned_candidate_files":31,
                      "unchanged_nonmain_definitions":len(bd)-1,"canonical_explorer_mode":"100755",
                      "native_explorer_projection_mode":"100644"}
    for mode,checks,processes in [("baseline",64,16),("candidate",84,21)]:
        r=obj(mode+"-cli/report.json")
        require(len(r["checks"])==checks and all(x["pass"] is True for x in r["checks"]),"CLI checks "+mode)
        require(len(r["processes"])==processes,"CLI processes "+mode)
        require(r["source_before"]==r["source_after"],"CLI source stability "+mode)
        for n,p in r["source_before"].items():samepin(raw(mode+"/"+n),p,"actual source "+mode+"/"+n)
        for proc in r["processes"]:
            for stream in ("stdout","stderr"):
                samepin(raw(mode+"-cli/"+proc["label"]+"/"+stream),proc[stream],"process "+proc["label"]+" "+stream)
        result[mode+"_cli"]={"checks":checks,"processes":processes}
    cases=obj("candidate-cli/browser-input.json")["cases"]
    require(len(cases)==8,"seven native plus one renderer-only input")
    native=0
    for c in cases:
        b=raw(c["json"]);r=json.loads(b)
        require(b==(dump(r,indent=2)+"\n").encode(),"native JSON spelling "+c["name"])
        if c["name"]!="renderer-literals":
            require(b==raw("baseline-cli/"+c["name"]+"-json/stdout"),"default JSON unchanged "+c["name"])
            native+=1
    result["unchanged_native_json_outputs"]=native
    browser=obj("browser-v2/report.json")
    require(browser["accepted"] and browser["source_unchanged"],"browser accepted")
    require(len(browser["positive"])==9,"nine positive views")
    require(sum(len(v["checks"]) for v in browser["positive"])==6122,"browser check denominator")
    options=worldcells=componentcells=0
    for view in browser["positive"]:
        name=view["name"];observed=obj("browser-v2/"+name+"/observed.json")
        b=raw(view["source_json"]);r=json.loads(b);world=r["world"];ads=r["advisories"]
        expected={k:text(r[k]) for k in ("status","candidate_count","conflicting_aircraft","reviewed_at","input_sha256","world_hash")}
        expected.update(version=text(world["version"]),observed_at=text(world["observed_at"]),admitted_count=str(len(ads)))
        require(observed["summary"]==expected,name+" summary")
        require(observed["policy"]=={k:text(v) for k,v in r["policy"].items()},name+" policy")
        expectedworld=[{"aircraft_id":a["aircraft_id"],"fields":{k:text(v) for k,v in a.items()}} for a in world["aircraft"]]
        require(observed["world"]==expectedworld,name+" world")
        worldcells+=sum(len(x["fields"]) for x in expectedworld)
        require(len(observed["options"])==len(ads),name+" alternative count")
        byid={a["aircraft_id"]:a for a in world["aircraft"]}
        for i,(a,o) in enumerate(zip(ads,observed["options"]),1):
            require(o["rank"]==i and o["id"]=="alternative-"+str(i) and o["tag"]=="DETAILS" and o["aircraft_id"]==a["aircraft_id"],name+" option order")
            metadata={k:text(a[k]) for k in ("aircraft_id","advisory_hash","world_hash","issued_at","expires_at","rationale")}
            require(o["metadata"]==metadata,name+" option metadata")
            components={k:{"current":text(byid[a["aircraft_id"]][k]),"proposed":text(a["set_"+k])} for k in ("vx_nm_min","vy_nm_min","climb_ft_min")}
            require(o["components"]==components,name+" exact component values")
            require(o["advisory_json"]==dump(a,indent=2),name+" exact nine-field body")
            options+=1;componentcells+=6
        require(observed["report_json"]==b.decode(),name+" original JSON")
        require(base64.b64decode(observed["download_href"].split(",",1)[1],validate=True)==b,name+" embedded download")
        require(raw("browser-v2/"+name+"/download.json")==b,name+" actual download")
        samepin(b,view["download"],name+" download receipt")
        require(observed["scripts"]==0 and observed["interpreted_markers"]==0,name+" literal document")
        require(observed["document_width"]<=view["width"]+1,name+" phone fit")
        require(not view["errors"] and not view["requests"] and all(x["pass"] is True for x in view["checks"]),name+" browser outcome")
    require(browser["source_files"]==browser["source_after"],"browser original input stability")
    for n,p in browser["source_files"].items():samepin(raw(n),p,"browser input custody")
    rejected=[]
    for v in browser["negative"]:
        bad=[x["label"] for x in v["checks"] if not x["pass"]]
        expected=["ordered alternative count"] if v["mutation"]=="drop-last-alternative" else ["embedded download bytes","actual download bytes"]
        require(bad==expected and v["negative_control_rejected"],"negative control exact failure")
        o=obj("browser-v2/"+v["name"]+"/observed.json");b=raw(v["source_json"]);r=json.loads(b)
        if v["mutation"]=="drop-last-alternative":
            require(len(o["options"])==len(r["advisories"])-1 and raw("browser-v2/"+v["name"]+"/download.json")==b,"missing-option control bytes")
        else:
            require(raw("browser-v2/"+v["name"]+"/download.json")==b+b" " and base64.b64decode(o["download_href"].split(",",1)[1])==b+b" ","wrong-download control bytes")
        rejected.append(v["mutation"])
    require(len(rejected)==2,"two browser negative controls")
    old=obj("browser-v1/report.json")
    oldbad=[x["label"] for v in old["positive"] for x in v["checks"] if not x["pass"]]
    require(len(oldbad)==17 and oldbad.count("not complete-world resolution disclosure")==9 and oldbad.count("opened full body visible")==6 and oldbad.count("meaningful distinct empty outcome")==2,"preserved observer failures")
    correction=obj("browser-binding-correction.json")
    require(not correction["product_source_changed"],"observer-only correction")
    for n,key in [("receive_browser.mjs","original_driver_sha256"),("receive_browser_v2.mjs","successor_driver_sha256")]:
        require(pin(raw(n))["sha256"]==correction[key],"observer pin "+n)
    mobile=obj("mobile-alternative/report.json")
    require(mobile["failed"]==0 and len(mobile["checks"])==9 and all(x["pass"] for x in mobile["checks"]),"mobile alternative witness")
    require(mobile["source_before"]==mobile["source_after"]==pin(raw("candidate-cli/crossing-html/report.html"))["sha256"],"mobile HTML stability")
    vis=obj("visual-review.json")
    for n,p in vis["files"].items():
        b=raw(n);samepin(b,p,"reviewed PNG");require(b.startswith(b"\x89PNG\r\n\x1a\n"),"PNG signature")
    for n in ["baseline-command.json","candidate-command.json","browser-v2-command.json","mobile-alternative-command.json"]:
        require(obj(n)["returncode"]==0,"actual wrapper exit "+n)
    result["browser"]={"views":9,"checks":6122,"exact_positive_downloads":9,"separate_control_downloads":2,
                       "rendered_alternative_appearances":options,"world_data_cells":worldcells,"component_value_cells":componentcells,
                       "negative_controls_rejected":rejected,"preserved_first_observer_failures":17,
                       "mobile_alternative_checks":9,"visually_reviewed_pngs":len(vis["files"])}
    primary=obj("primary-current-parent.json");composition=obj("current-composition-review.json")
    require(primary["commit"]==composition["parent"]=="473d36f8135ced7c4000fefd8fc91c0128d3c106" and primary["blob_leaves"]==1144,"current primary identity")
    cp={x["path"]:x for x in primary["closure"]}
    for e in custody["primary_baseline_entries"]:
        if e["path"]!="README.md":require((e["git_blob"],"100755" if e["path"]=="explorer.py" else e["mode"])==(cp[e["path"]]["git_blob"],cp[e["path"]]["mode"]),"current runtime closure")
    for e in composition["scope"]:
        b=raw("publication-source/"+e["path"]);samepin(b,e,"publication source")
        if e["path"]!="README.md":require(b==raw("candidate/"+e["path"]),"unchanged published scope")
    inserted=composition["readme_insert"];final=raw("publication-source/README.md").decode()
    require(final.count(inserted)==1 and final.replace(inserted,"",1)==primary["readme"]["content"],"current README reconstruction")
    require(raw("candidate/README.md").decode().replace(inserted,"",1)==raw("baseline-complete/README.md").decode(),"original README reconstruction")
    result["source_only_current_parent"]={"commit":primary["commit"],"tree":primary["tree"],"closure_unchanged_except_readme":32,"scope_unchanged_except_readme":4,"native_rerun":False}
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("packet",type=Path);p.add_argument("--negative-controls",action="store_true");a=p.parse_args()
    files=load_packet(a.packet);result=semantic(files)
    if a.negative_controls:
        failures=[]
        for name,target,change,expected in [
          ("wrong-admitted-count","browser-v2/crossing-375/observed.json","count","crossing-375 summary"),
          ("wrong-saved-download","browser-v2/crossing-375/download.json","bytes","crossing-375 actual download")]:
            altered=dict(files)
            if change=="count":
                o=json.loads(altered[target]);o["summary"]["admitted_count"]="65";altered[target]=(dump(o,indent=2)+"\n").encode()
            else:altered[target]+=b" "
            try:semantic(altered)
            except ValueError as e:require(str(e)==expected,"negative detected wrong boundary");failures.append({"control":name,"rejected_at":str(e)})
            else:raise ValueError("negative control accepted")
        result={"format":"towerops-cold-semantic-negatives-v1","product_execution":False,"controls":failures}
    print(json.dumps(result,indent=2,ensure_ascii=False)+"\n",end="")
if __name__=="__main__":main()
