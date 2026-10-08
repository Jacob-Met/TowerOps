from pathlib import Path
import hashlib,json,subprocess,difflib,os
root=Path(__file__).resolve().parent
owner=Path("/tmp/towerops-scenarios-cf5799f6d38b-ycfa66pv")
raw=(owner/"qualification-current/source-manifest.json").read_bytes()
if hashlib.sha256(raw).hexdigest()!="be525ef56c42052a56702f6735b11d06f0de63dc7a176192d66278c898c8a2ca": raise RuntimeError("current manifest drift")
manifest=json.loads(raw); original=owner/"candidate-current"
parent="09b96e31d2867af5b7a9738406d0431cf1010090"
tree="317ddf06e84c6b08f2e06ce634f5a64b264effd5"
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
target=root/"candidate-current";target.mkdir(exist_ok=False)
for row in manifest["files"]:
    relative=Path(row["path"]);source=original/relative
    if relative.is_absolute() or ".." in relative.parts or source.is_symlink(): raise RuntimeError("invalid source")
    body=source.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest()
    if len(body)!=row["bytes"] or hashlib.sha256(body).hexdigest()!=row["sha256"] or blob!=row["git_blob"]:raise RuntimeError("current source drift "+str(relative))
    if staged[str(relative)]!={"mode":row["mode"],"git_blob":blob}:raise RuntimeError("staged source drift")
    if str(relative) in feature and body!=(root/"candidate-r2"/relative).read_bytes():raise RuntimeError("feature changed "+str(relative))
    file=target/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(body);file.chmod(int(row["mode"],8)&0o777)
(target/"web/airspace/node_modules").symlink_to((root/"candidate/web/airspace/node_modules").resolve(),target_is_directory=True)
(root/"source-manifest-current.json").write_bytes(raw)
with (root/"build-current.stdout.log").open("xb") as out,(root/"build-current.stderr.log").open("xb") as err:
    result=subprocess.run(["npm","run","build"],cwd=target/"web/airspace",stdout=out,stderr=err,timeout=120)
report={"source_tree":tree,"parent":parent,"source_files":len(manifest["files"]),"feature_files":len(feature),"unowned_files_preserved":len(staged)-len(feature),"feature_paths":sorted(feature),"feature_bytes_match_r2":True,"build_returncode":result.returncode,
        "source_unchanged_after_build":all(hashlib.sha256((target/r["path"]).read_bytes()).hexdigest()==r["sha256"] for r in manifest["files"])}
(root/"bootstrap-current-receipt.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
