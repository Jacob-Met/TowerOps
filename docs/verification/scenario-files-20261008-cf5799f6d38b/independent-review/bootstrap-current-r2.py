from pathlib import Path
import hashlib,json,subprocess,difflib,os
root=Path(__file__).resolve().parent
owner=Path("/tmp/towerops-scenarios-cf5799f6d38b-ycfa66pv")
raw=(owner/"qualification-current-r2/source-manifest.json").read_bytes()
if hashlib.sha256(raw).hexdigest()!="50b09d63b2bec39ae6556e35e1347dd169558cffe7b16e8531c4d5fdbf76e1ef": raise RuntimeError("current manifest drift")
manifest=json.loads(raw); original=owner/"candidate-current-r2"
parent="09b96e31d2867af5b7a9738406d0431cf1010090"
tree="d6b4a1ec5757144f848e1d6ce851a766a7413f2c"
def git_tree(ref):
    value=subprocess.run(["git","-C",str(original),"ls-tree","-r","-z",ref],capture_output=True,check=True).stdout
    rows={}
    for raw in value.split(b"\0"):
        if not raw:continue
        head,name=raw.split(b"\t",1);mode,kind,blob=head.decode().split()
        if kind!="blob":raise RuntimeError("nonblob tree")
        rows[name.decode()]={"mode":mode,"git_blob":blob}
    return rows
base=git_tree(parent);staged=git_tree(tree)
feature={"web/airspace/"+name for name in ["src/scenario-file.ts","src/scenario-ui.ts","src/main.ts","index.html","style.css","tests/scenario-file.test.ts","README.md"]}
actual_change={name for name in set(base)|set(staged) if base.get(name)!=staged.get(name)}
if actual_change!=feature:raise RuntimeError("unexpected composition diff "+str(actual_change))
if set(staged)!={r["path"] for r in manifest["files"]}:raise RuntimeError("manifest incomplete")
target=root/"candidate-current-r2";target.mkdir(exist_ok=False)
changed=[]
for row in manifest["files"]:
    relative=Path(row["path"]);source=original/relative
    if relative.is_absolute() or ".." in relative.parts or source.is_symlink(): raise RuntimeError("invalid source")
    body=source.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest()
    if len(body)!=row["bytes"] or hashlib.sha256(body).hexdigest()!=row["sha256"] or blob!=row["git_blob"]:raise RuntimeError("current source drift "+str(relative))
    if staged[str(relative)]!={"mode":row["mode"],"git_blob":blob}:raise RuntimeError("staged source drift")
    if body!=(root/"candidate-current"/relative).read_bytes(): changed.append(str(relative))
    file=target/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(body);file.chmod(int(row["mode"],8)&0o777)
if changed!=["web/airspace/src/main.ts"]:raise RuntimeError("unexpected successor delta "+str(changed))
(target/"web/airspace/node_modules").symlink_to((root/"candidate/web/airspace/node_modules").resolve(),target_is_directory=True)
(root/"source-manifest-current-r2.json").write_bytes(raw)
with (root/"build-current-r2.stdout.log").open("xb") as out,(root/"build-current-r2.stderr.log").open("xb") as err:
    result=subprocess.run(["npm","run","build"],cwd=target/"web/airspace",stdout=out,stderr=err,timeout=120)
report={"source_tree":tree,"parent":parent,"source_files":len(manifest["files"]),"feature_files":len(feature),"unowned_files_preserved":len(staged)-len(feature),"feature_paths":sorted(feature),"only_changed_path_from_current":changed,"build_returncode":result.returncode,
        "source_unchanged_after_build":all(hashlib.sha256((target/r["path"]).read_bytes()).hexdigest()==r["sha256"] for r in manifest["files"])}
(root/"bootstrap-current-r2-receipt.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
