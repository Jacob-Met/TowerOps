#!/usr/bin/env python3
"""Install the exact reviewed Synthetic Explorer on the designated ThinkPad."""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import shlex
import socket
import stat
import sys

VERSION = "c77e98e68d627c3ad75edc2d775ee8da018dbdcf"
PREFIX = Path("/home/jacob/.local")
PINS = {
    "EXPLORER.md": [
        9288,
        "135c46bab3ef61c90d88cf6599f129c36f446a164214a37099b0dba71ad399e3",
        420
    ],
    "explorer.py": [
        7604,
        "0d2d9ce308bb5a1648ae03fb3230d5f6beed629314c2a7a76b0bab187392c843",
        493
    ],
    "replay_explain.py": [
        5432,
        "bd717d3bd86f238e3f44c2710b56f88d142046cf02ec9049fd337a9a7db9fc7b",
        420
    ],
    "scenarios.py": [
        5989,
        "bda24452b41a9ec8b6a7a0865b2fb95217a4a304ecf17b1c5d72b2dab65f6a52",
        420
    ],
    "towerops.py": [
        19684,
        "b8bb4a15c70b0137e1c47aa614e6ed1b6f3cae096af9fb0c8810f3d900a48f70",
        420
    ],
    "web/app.js": [
        9430,
        "9e3d38e3dec59d0b4725771770c05a89afa0190fec8438cd61921b6d3b846739",
        420
    ],
    "web/index.html": [
        3934,
        "d616416300f809bce0b843b792a65f15f560bb8c543f49936744dfd95b46a0b1",
        420
    ],
    "web/style.css": [
        2566,
        "b0ee12c04e0b0bb4b7bb1e9ce0dc7dbc9e874966d9e326784f3728e42dc023c9",
        420
    ]
}


class InstallError(RuntimeError):
    def __init__(self, message, outcome=None):
        super().__init__(message)
        self.outcome = outcome


def require(condition, message):
    if not condition:
        raise InstallError(message)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("ascii")


def bytes_identity(raw):
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
    }


def stable(info):
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
        info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
    )


def stat_identity(info):
    return {
        "device": info.st_dev, "inode": info.st_ino,
        "mode": stat.S_IMODE(info.st_mode), "uid": info.st_uid,
        "gid": info.st_gid, "links": info.st_nlink,
        "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns,
    }


def absolute(path):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts,
            "explicit absolute path without '..' required")
    return path


def directories(path, owned_leaf=False):
    path = absolute(path)
    for entry in reversed([path, *path.parents]):
        info = entry.lstat()
        require(stat.S_ISDIR(info.st_mode), "symlink or non-directory ancestor: " + str(entry))
        require(info.st_uid in (0, os.getuid()), "unexpected directory owner: " + str(entry))
    if owned_leaf:
        require(path.lstat().st_uid == os.getuid(), "directory must belong to the current account")


def read_regular(path, limit):
    path = absolute(path)
    directories(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                and before.st_nlink == 1, "expected singly linked owned regular file: " + str(path))
        require(before.st_size <= limit, "file exceeds bound: " + str(path))
        chunks, remaining = [], limit + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        require(stable(before) == stable(os.fstat(fd)) == stable(path.lstat())
                and len(raw) == before.st_size, "file changed during read: " + str(path))
        return raw, {**bytes_identity(raw), **stat_identity(before)}
    finally:
        os.close(fd)


def capture_sources(source):
    directories(source, owned_leaf=True)
    bodies, identities = {}, {}
    for name, (size, digest, _mode) in PINS.items():
        raw, info = read_regular(source / name, size)
        require(info["bytes"] == size and info["sha256"] == digest, "unaccepted source: " + name)
        bodies[name], identities[name] = raw, info
    return bodies, identities


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_fd(fd, raw):
    view = memoryview(raw)
    while view:
        written = os.write(fd, view)
        require(written > 0, "short file write")
        view = view[written:]
    os.fsync(fd)


def write_new(path, raw, mode, created):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    created.append(str(path))
    try:
        os.fchmod(fd, mode)
        write_fd(fd, raw)
    finally:
        os.close(fd)
    sync_dir(path.parent)


def mkdir_new(path, created):
    path.mkdir(mode=0o755)
    created.append(str(path))
    path.chmod(0o755)
    sync_dir(path.parent)


def save_receipt(fd, path, value):
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    write_fd(fd, encoded(value))
    sync_dir(path.parent)


def installed_identity(release, expected):
    found = set()
    for path in release.rglob("*"):
        rel = path.relative_to(release).as_posix()
        info = path.lstat()
        require(not stat.S_ISLNK(info.st_mode), "linked installed entry: " + rel)
        if rel == "web":
            require(stat.S_ISDIR(info.st_mode), "installed web directory differs")
        else:
            require(stat.S_ISREG(info.st_mode), "nonregular installed entry: " + rel)
            found.add(rel)
    require(found == set(expected), "unexpected or missing version entry")
    result = {}
    for name, (raw, mode) in expected.items():
        body, identity = read_regular(release / name, len(raw))
        require(body == raw and identity["mode"] == mode, "installed file differs: " + name)
        result[name] = identity
    return result


def deploy(source_dir, receipt_new, prefix):
    """Create a fresh namespace; tests inject only their temporary owned prefix."""
    source, receipt, prefix = map(absolute, (source_dir, receipt_new, prefix))
    namespace = prefix / "share/towerops"
    versions = namespace / "explorer"
    release = versions / VERSION
    alias = prefix / "bin/towerops-explorer"
    wrapper = release / "towerops-explorer"
    outcome = {
        "schema": "towerops.explorer-install.v1", "ok": False, "phase": "admission",
        "started": utc_now(), "accepted_source": VERSION, "release": str(release),
        "selector": str(alias), "receipt": str(receipt), "created": [],
        "server_started": False, "path_edited": False,
    }
    receipt_fd = None
    try:
        for path in (prefix, prefix / "bin", prefix / "share"):
            directories(path, owned_leaf=True)
        directories(receipt.parent, owned_leaf=True)
        require(receipt != prefix and prefix not in receipt.parents,
                "receipt must be outside the installation prefix")
        bodies, inputs = capture_sources(source)
        require(not os.path.lexists(alias), "explorer selector exists; preserve and inspect it")
        require(not os.path.lexists(namespace), "TowerOps namespace exists; preserve and inspect it")
        receipt_fd = os.open(receipt, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        outcome["created"].append(str(receipt))
        os.fchmod(receipt_fd, 0o600)
        outcome.update(inputs=inputs, phase="namespace")
        save_receipt(receipt_fd, receipt, outcome)
        mkdir_new(namespace, outcome["created"])  # Exclusive reservation, not a shared lock.
        mkdir_new(versions, outcome["created"])
        mkdir_new(release, outcome["created"])
        mkdir_new(release / "web", outcome["created"])
        outcome["phase"] = "release"
        expected = {}
        for name, raw in bodies.items():
            mode = PINS[name][2]
            write_new(release / name, raw, mode, outcome["created"])
            expected[name] = (raw, mode)
        launcher = ("#!/bin/sh\nexec /usr/bin/python3 -B "
                    + shlex.quote(str(release / "explorer.py")) + ' serve "$@"\n').encode()
        write_new(wrapper, launcher, 0o755, outcome["created"])
        expected["towerops-explorer"] = (launcher, 0o755)
        provenance = {
            "schema": "towerops.explorer-version.v1", "source_repository": "Jacob-Met/TowerOps",
            "accepted_source": VERSION,
            "source_files": {name: {**bytes_identity(raw), "mode": PINS[name][2]}
                             for name, raw in bodies.items()},
            "wrapper": bytes_identity(launcher), "python": "/usr/bin/python3",
            "purpose": "Foreground loopback Synthetic Explorer; no automatic startup.",
            "installed_at": utc_now(),
        }
        provenance_bytes = encoded(provenance)
        write_new(release / "installation.json", provenance_bytes, 0o644, outcome["created"])
        expected["installation.json"] = (provenance_bytes, 0o644)
        installed = installed_identity(release, expected)
        require(capture_sources(source)[1] == inputs, "source custody changed")
        outcome["phase"] = "selector"
        os.symlink(str(wrapper), alias)  # Exclusive creation never replaces an existing command.
        outcome["created"].append(str(alias))
        sync_dir(alias.parent)
        require(alias.is_symlink() and os.readlink(alias) == str(wrapper), "new selector differs")
        require(installed_identity(release, expected) == installed,
                "new version changed during selector publication")
        require(capture_sources(source)[1] == inputs, "source custody changed after publication")
        outcome.update(ok=True, phase="complete", finished=utc_now(),
                       installed=installed, selector_target=str(wrapper))
        save_receipt(receipt_fd, receipt, outcome)
        return outcome
    except (OSError, InstallError) as exc:
        outcome.update(ok=False, error=str(exc), finished=utc_now())
        if receipt_fd is not None:
            try:
                save_receipt(receipt_fd, receipt, outcome)
            except (OSError, InstallError) as receipt_error:
                outcome["receipt_write_error"] = str(receipt_error)
        raise InstallError(str(exc), outcome) from exc
    finally:
        if receipt_fd is not None:
            os.close(receipt_fd)


def host_identity():
    account = pwd.getpwuid(os.getuid())
    require(sys.platform == "linux" and socket.gethostname() == "hamon-thinkpad"
            and os.getuid() == 1000 and account.pw_name == "jacob"
            and account.pw_dir == "/home/jacob",
            "this adoption is restricted to hamon-thinkpad / jacob uid1000")
    require(sys.version_info >= (3, 12), "Python 3.12 or newer is required")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--receipt-new", required=True, type=Path)
    args = parser.parse_args(argv)
    result = None
    try:
        host_identity()
        result = deploy(args.source_dir, args.receipt_new, PREFIX)
        print(encoded({
            "ok": True, "selector": result["selector"], "release": result["release"],
            "receipt": result["receipt"], "accepted_source": VERSION,
        }).decode("ascii"), end="", flush=True)
        return 0
    except (InstallError, OSError, UnicodeError) as exc:
        if isinstance(exc, (OSError, UnicodeError)):
            sys.stdout = io.StringIO()  # Do not repeat a failed flush at interpreter shutdown.
        detail = {"ok": False, "error": str(exc)}
        if isinstance(exc, InstallError) and exc.outcome is not None:
            detail["outcome"] = exc.outcome
        elif result is not None:
            detail.update(phase="console", installation_receipt=result["receipt"],
                          selector_may_exist=True)
        print(json.dumps(detail, ensure_ascii=True, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
