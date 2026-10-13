#!/usr/bin/env python3
"""Frozen independent actual-install/relocation receiver; no browser replay."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
CRITERIA_SHA = "5c3835e230b9a8acc36653b5ba17b8e5bbee07b833032541e1f28229c3b5c26c"
ORACLE_SHA = "ee3d0afd77da9bd6c6d3c37517956b4ad48ce1928c5f48774ddfcfdead584181"
OUT = ROOT / "course-v2"
record = {"schema": "hamon.loom.towerops-installed-explorer-receiving.v2",
          "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "accepted": False, "checks": [], "commands": [], "http": [], "errors": [],
          "scope": "Actual create-only installation, existing PATH launcher, relocated static assets and three complete prior HTTP oracles. No browser replay."}
server = None
server_files = []
port = None
inputs_before = None
installed_before = None

def digest(b):
    return hashlib.sha256(b).hexdigest()

def identity(p):
    p = Path(p)
    s = p.lstat()
    if not stat.S_ISREG(s.st_mode):
        raise RuntimeError("Expected nonsymlink regular file: " + str(p))
    b = p.read_bytes()
    return {"path": str(p), "bytes": len(b), "sha256": digest(b),
            "mode": oct(stat.S_IMODE(s.st_mode)), "uid": s.st_uid,
            "inode": s.st_ino, "mtime_ns": s.st_mtime_ns}

def check(name, actual, expected):
    passed = actual == expected
    record["checks"].append({"name": name, "actual": actual, "expected": expected, "pass": passed})
    if not passed:
        raise RuntimeError("Comparison failed: " + name)

def supplied(p, row):
    got = identity(p)
    check("bytes " + str(p), got["bytes"], row["bytes"])
    check("sha256 " + str(p), got["sha256"], row["sha256"])
    if "mode" in row:
        check("mode " + str(p), got["mode"], row["mode"])
    return got

def command_identity(p):
    p = Path(p)
    result = {"path": str(p), "lexists": os.path.lexists(p)}
    if not result["lexists"]:
        return result
    s = p.lstat()
    result.update(mode=oct(stat.S_IMODE(s.st_mode)), symlink=stat.S_ISLNK(s.st_mode))
    if not result["symlink"]:
        raise RuntimeError("Expected existing selector symlink: " + str(p))
    target = p.resolve(strict=True)
    q = identity(target)
    result.update(link=os.readlink(p), resolved=str(target), bytes=q["bytes"],
                  sha256=q["sha256"], target_mode=q["mode"])
    return result

def namespace_snapshot(p):
    p = Path(p)
    if not os.path.lexists(p):
        return {"path": str(p), "exists": False}
    rows = []
    for q in [p] + sorted(p.rglob("*")):
        s = q.lstat()
        row = {"path": str(q.relative_to(p)) or ".", "mode": oct(stat.S_IMODE(s.st_mode)),
               "uid": s.st_uid, "inode": s.st_ino, "mtime_ns": s.st_mtime_ns}
        if stat.S_ISREG(s.st_mode):
            b = q.read_bytes()
            row.update(kind="file", bytes=len(b), sha256=digest(b))
        elif stat.S_ISLNK(s.st_mode):
            row.update(kind="symlink", link=os.readlink(q))
        elif stat.S_ISDIR(s.st_mode):
            row["kind"] = "directory"
        else:
            raise RuntimeError("Unexpected namespace entry type: " + str(q))
        rows.append(row)
    return {"path": str(p), "exists": True, "entries": rows}

def selected_inputs():
    paths = [ROOT / "criteria-v1.json", ROOT / "criteria-freeze-v1.json",
             ROOT / "receive-install-v2.py", ROOT / "driver-freeze-v2.json",
             ROOT / "original-stage.json", ROOT / "receive-install-v1.py",
             ROOT / "driver-freeze-v1.json", ROOT / "receiver-v1-to-v2.patch", spec_path, installer]
    paths += [source / r["path"] for r in criteria["runtime"]]
    paths += [Path(r["path"]) for r in criteria["original_oracles"]["fixtures"]]
    paths += [Path(criteria["original_oracles"]["receipt"])]
    return [identity(p) for p in paths]

def rawfile(name, body):
    p = OUT / name
    with p.open("xb") as f:
        f.write(body)
    return identity(p)

def run(label, argv):
    stdout = OUT / (label + ".stdout")
    stderr = OUT / (label + ".stderr")
    with stdout.open("xb") as so, stderr.open("xb") as se:
        child = subprocess.Popen(argv, cwd=work, env=env, stdout=so, stderr=se)
        try:
            code = child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.terminate()
            code = child.wait(timeout=5)
            raise RuntimeError("Owned installer process timed out; terminated. Return " + str(code))
    item = {"label": label, "argv": argv, "cwd": str(work), "pid": child.pid,
            "exit_code": code, "stdout": identity(stdout), "stderr": identity(stderr)}
    record["commands"].append(item)
    return item

def port_is_open():
    import socket
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0

def close_server():
    if server is None:
        return
    if server.poll() is None:
        server.send_signal(signal.SIGINT)
    try:
        code = server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        record["errors"].append("Own server did not close after SIGINT; sent SIGTERM")
        server.terminate()
        code = server.wait(timeout=5)
    for f in server_files:
        f.close()
    record["server"]["exit_code"] = code
    record["server"]["stdout"] = identity(OUT / "server.stdout")
    record["server"]["stderr"] = identity(OUT / "server.stderr")
    check("own server SIGINT closure", code, 0)
    if port is not None:
        deadline = time.monotonic() + 2
        while port_is_open() and time.monotonic() < deadline:
            time.sleep(0.05)
        check("own loopback port closed", port_is_open(), False)

def request(label, method, path, body, expected_status, expected):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Origin": "http://127.0.0.1:" + str(port), "Connection": "close"}
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body))
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        actual = response.read()
        status = response.status
        response_headers = list(response.getheaders())
    finally:
        connection.close()
    item = {"label": label, "method": method, "path": path, "status": status,
            "headers": response_headers,
            "request_body": rawfile(label + ".request", b"" if body is None else body),
            "response_body": rawfile(label + ".response", actual)}
    record["http"].append(item)
    check(label + " status", status, expected_status)
    check(label + " complete bytes", actual == expected, True)
    check(label + " response sha256", digest(actual), digest(expected))

try:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: receive-install-v1.py ABS_CANDIDATE_SPEC")
    spec_path = Path(sys.argv[1])
    if not spec_path.is_absolute() or spec_path.parent != ROOT:
        raise RuntimeError("Candidate spec must be an absolute direct child of own stage")
    if ROOT != Path("/home/jacob/hamon/receiving/loom-d3745-towerops-install"):
        raise RuntimeError("Unexpected receiver stage")
    criteria_raw = (ROOT / "criteria-v1.json").read_bytes()
    check("root original criteria bytes", digest(criteria_raw), CRITERIA_SHA)
    criteria = json.loads(criteria_raw)
    freeze = json.loads((ROOT / "driver-freeze-v2.json").read_text())
    check("frozen driver", digest(Path(__file__).read_bytes()), freeze["driver"]["sha256"])
    check("hostname", platform.node(), criteria["required_identity"]["hostname"])
    check("uid", os.getuid(), criteria["required_identity"]["uid"])
    check("user", pwd.getpwuid(os.getuid()).pw_name, criteria["required_identity"]["user"])
    check("real home", str(Path.home()), "/home/jacob")
    check("Python >=3.12", sys.version_info[:2] >= (3, 12), True)
    for p in [Path("/home"), Path("/home/jacob"), Path("/home/jacob/.local"),
              Path("/home/jacob/.local/bin"), Path("/home/jacob/.local/share")]:
        s = p.lstat()
        check("nonsymlink directory " + str(p), stat.S_ISDIR(s.st_mode), True)
        if str(p).startswith("/home/jacob"):
            check("owned prefix " + str(p), s.st_uid, 1000)
    source = ROOT / "source"
    spec = json.loads(spec_path.read_text())
    installer = Path(spec["installer"]["path"])
    if not installer.is_absolute():
        raise RuntimeError("Installer path must be absolute")
    supplied(installer, spec["installer"])
    for row in criteria["runtime"]:
        supplied(source / row["path"], row)
    source_names = sorted(str(p.relative_to(source)) for p in source.rglob("*") if not p.is_dir())
    check("exact eight source names", source_names, sorted(r["path"] for r in criteria["runtime"]))
    for row in criteria["original_oracles"]["fixtures"]:
        supplied(row["path"], row)
    check("prior original receipt", identity(criteria["original_oracles"]["receipt"])["sha256"], ORACLE_SHA)
    for row in criteria["original_oracles"]["http"]:
        b = row["expected_body"].encode()
        check("oracle bytes " + row["path"], len(b), row["expected_bytes"])
        check("oracle digest " + row["path"], digest(b), row["expected_sha256"])
    neighbors_before = [command_identity(x["path"]) for x in criteria["existing_commands"]]
    check("three prior Tsuka command bindings", neighbors_before, criteria["existing_commands"])
    namespace = Path(criteria["namespace"])
    selector = Path(criteria["selector"])
    release = Path(criteria["release"])
    check("new namespace absent", os.path.lexists(namespace), False)
    check("new selector absent", os.path.lexists(selector), False)
    check("original PATH has no TowerOps command", shutil.which("towerops-explorer"), None)
    check("existing local bin on PATH", "/home/jacob/.local/bin" in os.environ.get("PATH", "").split(os.pathsep), True)
    OUT.mkdir(mode=0o700)
    work = OUT / "unrelated-working-directory"
    work.mkdir(mode=0o700)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
    record["environment"] = {"python": sys.executable, "version": sys.version,
                             "PATH": env.get("PATH"), "cwd": str(work)}
    record["candidate_spec"] = spec
    inputs_before = selected_inputs()
    record["inputs_before"] = inputs_before
    first_receipt = OUT / "installation-receipt.json"
    check("first installer receipt absent", os.path.lexists(first_receipt), False)
    result = run("install-first", ["/usr/bin/python3", "-B", str(installer),
                 "--source-dir", str(source), "--receipt-new", str(first_receipt)])
    check("first install exit", result["exit_code"], 0)
    record["installer_receipt"] = supplied(first_receipt, {"bytes": first_receipt.stat().st_size,
                                                          "sha256": digest(first_receipt.read_bytes())})
    record["installer_receipt_object"] = json.loads(first_receipt.read_text())
    check("PATH resolves intended selector", shutil.which("towerops-explorer"), str(selector))
    installed_command = command_identity(selector)
    record["installed_command"] = installed_command
    check("wrapper resolves in fixed release", installed_command["resolved"], str(release / "towerops-explorer"))
    check("installed wrapper executable", os.access(selector, os.X_OK), True)
    for row in criteria["runtime"]:
        supplied(release / row["path"], row)
    check("exact release files", sorted(str(p.relative_to(release)) for p in release.rglob("*") if not p.is_dir()),
          sorted([r["path"] for r in criteria["runtime"]] + ["towerops-explorer", "installation.json"]))
    check("declared installation manifest mode", identity(release / "installation.json")["mode"], "0o644")
    installed_before = {"namespace": namespace_snapshot(namespace), "selector": command_identity(selector)}
    record["installed_before_use"] = installed_before
    so = (OUT / "server.stdout").open("xb")
    se = (OUT / "server.stderr").open("xb")
    server_files = [so, se]
    argv = ["towerops-explorer", "--port", "0"]
    server = subprocess.Popen(argv, cwd=work, env=env, stdout=so, stderr=se)
    record["server"] = {"argv": argv, "cwd": str(work), "pid": server.pid}
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        b = (OUT / "server.stdout").read_bytes()
        found = re.search(rb"^Synthetic explorer: http://127[.]0[.]0[.]1:([0-9]+)\n", b)
        if found:
            port = int(found.group(1))
            break
        if server.poll() is not None:
            raise RuntimeError("Installed command exited before loopback startup line")
        time.sleep(0.05)
    check("own startup identifies allocated loopback port", port is not None and 0 < port < 65536, True)
    record["server"]["port"] = port
    for path, leaf, label in [("/", "web/index.html", "static-index"),
                              ("/app.js", "web/app.js", "static-app"),
                              ("/style.css", "web/style.css", "static-style")]:
        request(label, "GET", path, None, 200, (source / leaf).read_bytes())
    for i, row in enumerate(criteria["original_oracles"]["http"]):
        request("prior-oracle-" + str(i + 1), row["method"], row["path"],
                row["request_body"].encode(), row["expected_status"], row["expected_body"].encode())
    close_server()
    check("installed bytes/modes/namespace unchanged after use",
          {"namespace": namespace_snapshot(namespace), "selector": command_identity(selector)}, installed_before)
    second_receipt = OUT / "repeat-receipt.json"
    check("repeat receipt initially absent", os.path.lexists(second_receipt), False)
    result = run("install-repeat", ["/usr/bin/python3", "-B", str(installer),
                 "--source-dir", str(source), "--receipt-new", str(second_receipt)])
    check("explicit repeat exit", result["exit_code"], criteria["public_interface"]["repeat_refuses"])
    if second_receipt.exists():
        record["repeat_receipt"] = identity(second_receipt)
        record["repeat_receipt_object"] = json.loads(second_receipt.read_text())
    record["installed_after_repeat"] = {"namespace": namespace_snapshot(namespace),
                                        "selector": command_identity(selector)}
    check("installed namespace/selector preserved by repeat", record["installed_after_repeat"], installed_before)
    check("all three Tsuka commands unchanged", [command_identity(x["path"]) for x in criteria["existing_commands"]], neighbors_before)
    check("source/control/spec/original fixtures/oracle unchanged", selected_inputs(), inputs_before)
    record["accepted"] = True
except BaseException as exc:
    record["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
finally:
    if server is not None and server.poll() is None:
        try:
            close_server()
        except BaseException as exc:
            record["errors"].append({"cleanup_error": str(exc)})
            record["accepted"] = False
    if inputs_before is not None:
        try:
            record["inputs_after"] = selected_inputs()
            if record["inputs_after"] != inputs_before:
                record["accepted"] = False
                record["errors"].append("Final input preservation comparison failed")
        except BaseException as exc:
            record["accepted"] = False
            record["errors"].append({"final_input_audit_error": str(exc)})
    if "namespace" in globals():
        record["final_namespace"] = namespace_snapshot(namespace)
    if record["errors"]:
        record["accepted"] = False
    record["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record["no_installation_cleanup"] = "No installation/selector removal or automatic retry was performed; failed partial state remains for explicit review."
    if OUT.is_dir():
        with (OUT / "receipt.json").open("x") as f:
            json.dump(record, f, indent=2, ensure_ascii=True)
            f.write("\n")
    else:
        with (ROOT / "admission-failure-v2.json").open("x") as f:
            json.dump(record, f, indent=2, ensure_ascii=True)
            f.write("\n")
    print(json.dumps({"accepted": record["accepted"], "checks": len(record["checks"]),
                      "http_requests": len(record["http"]), "errors": record["errors"]}))
sys.exit(0 if record["accepted"] else 1)
