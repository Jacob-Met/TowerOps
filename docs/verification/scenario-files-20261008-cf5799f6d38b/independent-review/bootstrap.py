from pathlib import Path
import hashlib,json,os,shutil,subprocess,datetime
root=Path(__file__).resolve().parent
owner=Path("/tmp/towerops-scenarios-cf5799f6d38b-ycfa66pv")
manifest_path=owner/"qualification/source-manifest.json"
raw=manifest_path.read_bytes()
if hashlib.sha256(raw).hexdigest()!="6bd45f0fb10763c300ea86ab64028b4cd03f3a5708ffabe1fb0622cfd8b41bbd":
    raise RuntimeError("manifest drift")
manifest=json.loads(raw)
source=root/"candidate"
source.mkdir(exist_ok=False)
rows=[]
for item in manifest["files"]:
    rel=Path(item["path"])
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError("unsafe source path")
    original=owner/"candidate"/rel
    if not original.is_file() or original.is_symlink():
        raise RuntimeError("unexpected source kind")
    value=original.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(value)).encode()+b"\0"+value).hexdigest()
    if len(value)!=item["bytes"] or hashlib.sha256(value).hexdigest()!=item["sha256"] or blob!=item["git_blob"]:
        raise RuntimeError("source drift "+str(rel))
    target=source/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(value);target.chmod(int(item["mode"],8)&0o777)
    rows.append(item)
dependencies=(owner/"candidate/web/airspace/node_modules").resolve()
(source/"web/airspace/node_modules").symlink_to(dependencies,target_is_directory=True)
(root/"source-manifest.json").write_bytes(raw)
report={"source_files":len(rows),"all_source_blobs_match":True,
        "source_root":str(source),"dependency_root":str(dependencies),
        "node":subprocess.check_output(["node","--version"],text=True).strip(),
        "npm":subprocess.check_output(["npm","--version"],text=True).strip(),
        "source_tree":manifest["source_tree"],"parent":manifest["parent"],
        "started_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
with (root/"build.stdout.log").open("xb") as out,(root/"build.stderr.log").open("xb") as err:
    run=subprocess.run(["npm","run","build"],cwd=source/"web/airspace",stdout=out,stderr=err,timeout=120)
report["build_returncode"]=run.returncode
report["tracked_source_unchanged_after_build"]=all(hashlib.sha256((source/x["path"]).read_bytes()).hexdigest()==x["sha256"] for x in rows)
(root/"bootstrap-receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report))
