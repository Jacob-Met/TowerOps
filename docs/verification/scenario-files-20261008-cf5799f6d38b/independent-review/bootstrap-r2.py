from pathlib import Path
import hashlib,json,subprocess,difflib,os
root=Path(__file__).resolve().parent
owner=Path("/tmp/towerops-scenarios-cf5799f6d38b-ycfa66pv")
raw=(owner/"qualification-r2/source-manifest.json").read_bytes()
if hashlib.sha256(raw).hexdigest()!="a0fc7af66738686f1eeb4e099b95e4b17a8da2fdbd9738a16a7a74ddd8d2eed1":
    raise RuntimeError("r2 manifest drift")
manifest=json.loads(raw); target=root/"candidate-r2";target.mkdir(exist_ok=False)
changed=[]
for row in manifest["files"]:
    relative=Path(row["path"]); original=owner/"candidate-r2"/relative
    if relative.is_absolute() or ".." in relative.parts or original.is_symlink(): raise RuntimeError("invalid source")
    body=original.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest()
    if len(body)!=row["bytes"] or hashlib.sha256(body).hexdigest()!=row["sha256"] or blob!=row["git_blob"]: raise RuntimeError("r2 source drift "+str(relative))
    before=(root/"candidate"/relative).read_bytes()
    if body!=before: changed.append(str(relative))
    file=target/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(body);file.chmod(int(row["mode"],8)&0o777)
if changed!=["web/airspace/src/main.ts"]:raise RuntimeError("unreviewed source delta "+str(changed))
(target/"web/airspace/node_modules").symlink_to((root/"candidate/web/airspace/node_modules").resolve(),target_is_directory=True)
(root/"source-manifest-r2.json").write_bytes(raw)
delta="".join(difflib.unified_diff((root/"candidate/web/airspace/src/main.ts").read_text().splitlines(True),(target/"web/airspace/src/main.ts").read_text().splitlines(True),fromfile="original/src/main.ts",tofile="r2/src/main.ts"))
(root/"r2-source.delta").write_text(delta)
with (root/"build-r2.stdout.log").open("xb") as out,(root/"build-r2.stderr.log").open("xb") as err:
    result=subprocess.run(["npm","run","build"],cwd=target/"web/airspace",stdout=out,stderr=err,timeout=120)
report={"source_tree":manifest["source_tree"],"source_files":len(manifest["files"]),"changed_paths":changed,"build_returncode":result.returncode,
        "source_unchanged_after_build":all(hashlib.sha256((target/r["path"]).read_bytes()).hexdigest()==r["sha256"] for r in manifest["files"])}
(root/"bootstrap-r2-receipt.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
