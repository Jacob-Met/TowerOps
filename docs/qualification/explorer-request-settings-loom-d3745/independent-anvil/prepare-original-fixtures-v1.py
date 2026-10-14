#!/usr/bin/env python3
"""Receive three public original CLI exports once before candidate exposure."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

base = Path(__file__).resolve().parent
source, output = map(Path, sys.argv[1:])
assert source.is_absolute() and output.is_absolute() and not output.exists()
criteria = json.loads((base / "criteria-v1.json").read_text())
tree = json.loads((base / "original-source-tree-v1.json").read_text())

def identity(p):
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode)
    b = p.read_bytes()
    return {"path": str(p), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest(),
            "mode": stat.S_IMODE(s.st_mode)}

before = [identity(source / r["path"]) for r in tree["rows"]]
for r, x in zip(tree["rows"], before):
    assert x["git_blob"] == r["sha"] and x["bytes"] == r["size"]
    assert x["mode"] == (0o755 if r["mode"] == "100755" else 0o644)
output.mkdir()
receipt = {"schema": "anvil.towerops-settings.original-fixtures.v1", "accepted": False,
           "started_ns": time.time_ns(), "candidate_exposure": False,
           "original_commit": criteria["baseline_commit"], "source_before": before,
           "commands": [], "files": []}
try:
    for name, request in criteria["request_oracles"].items():
        argv = [sys.executable, "-B", str(source / "explorer.py"), "run", request["scenario"]]
        if not request["include_approval"]:
            argv.append("--without-approval")
        if not request["include_ack"]:
            argv.append("--without-ack")
        stdout, stderr = output / (name + ".json"), output / (name + ".stderr")
        with stdout.open("xb") as out, stderr.open("xb") as err:
            done = subprocess.run(argv, cwd=source, stdout=out, stderr=err, timeout=15)
        row = {"argv": argv, "exit": done.returncode, "stdout": identity(stdout), "stderr": identity(stderr)}
        receipt["commands"].append(row)
        assert done.returncode == 0 and stderr.read_bytes() == b""
        value = json.loads(stdout.read_text())
        assert value["request"] == request and value["format"] == "towerops.synthetic-explorer.v1"
        receipt["files"].append({"name": name, **identity(stdout)})
    assert json.loads((output / "B.json").read_text())["fixtures"]["ack"] is None
    mismatch = json.loads((output / "C.json").read_text())
    mismatch["label"] = "Retained literal mismatch <settings> 東京"
    (output / "C-mismatch.json").write_text(json.dumps(mismatch, ensure_ascii=True, indent=2) + "\n")
    (output / "malformed.json").write_text('{"request":')
    for name in ["C-mismatch", "malformed"]:
        receipt["files"].append({"name": name, **identity(output / (name + ".json"))})
    receipt["source_after"] = [identity(source / r["path"]) for r in tree["rows"]]
    assert receipt["source_after"] == before
    receipt["accepted"] = True
finally:
    receipt["finished_ns"] = time.time_ns()
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"accepted": receipt["accepted"], "commands": len(receipt["commands"]), "files": len(receipt["files"]), "receipt": identity(output / "receipt.json")}))
