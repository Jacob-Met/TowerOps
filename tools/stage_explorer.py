#!/usr/bin/env python3
"""Install an identified Explorer release alongside existing commands."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import sys

# Reuse the maintained filesystem routines without relying on sys.path or cwd.
_spec = importlib.util.spec_from_file_location(
    "towerops_install_helpers", Path(__file__).absolute().with_name("install_explorer.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

FILES = {name: (0o755 if name == "explorer.py" else 0o644) for name in (
    "EXPLORER.md", "explorer.py", "replay_explain.py", "scenarios.py",
    "towerops.py", "web/app.js", "web/index.html", "web/style.css")}
FILE_LIMIT = 1_048_576
TOTAL_LIMIT = 2_097_152


def capture(source):
    source = base.absolute(source)
    base.directories(source, owned_leaf=True)
    bodies, inputs, rows = {}, {}, []
    total = 0
    for name, mode in sorted(FILES.items()):
        raw, identity = base.read_regular(source / name, FILE_LIMIT)
        total += len(raw)
        base.require(total <= TOTAL_LIMIT, "selected sources exceed aggregate byte bound")
        bodies[name], inputs[name] = raw, identity
        rows.append({"path": name, "bytes": len(raw),
                     "sha256": identity["sha256"], "mode": mode})
    manifest = {"schema": "towerops.explorer-content.v1", "files": rows}
    digest = hashlib.sha256(base.encoded(manifest)).hexdigest()
    return bodies, inputs, manifest, digest


def require_separate(left, right, message):
    base.require(left != right and left not in right.parents
                 and right not in left.parents, message)


def inspect(source):
    _bodies, identities, manifest, digest = capture(source)
    base.require(capture(source)[1] == identities, "source custody changed during inspection")
    return {"ok": True, "digest": digest, "manifest": manifest}


def install(source_dir, prefix, expect_digest, receipt_new):
    source, prefix, receipt = map(base.absolute, (source_dir, prefix, receipt_new))
    base.require(isinstance(expect_digest, str)
                 and re.fullmatch(r"[0-9a-f]{64}", expect_digest) is not None,
                 "expected digest must be 64 lowercase hexadecimal characters")
    require_separate(source, prefix, "source and prefix must be disjoint")
    require_separate(receipt, source, "receipt must be outside the source")
    require_separate(receipt, prefix, "receipt must be outside the prefix")
    release = prefix / "share/towerops/explorer/releases" / expect_digest
    selector = prefix / "bin" / ("towerops-explorer-" + expect_digest[:12])
    wrapper = release / "towerops-explorer"
    outcome = {
        "schema": "towerops.explorer-stage.v1", "ok": False, "phase": "admission",
        "started": base.utc_now(), "digest": expect_digest, "release": str(release),
        "selector": str(selector), "receipt": str(receipt), "created": [],
        "server_started": False, "existing_commands_changed": False,
    }
    receipt_fd = None
    try:
        for path in (prefix, prefix / "bin", prefix / "share"):
            base.directories(path, owned_leaf=True)
        base.directories(receipt.parent, owned_leaf=True)
        bodies, inputs, manifest, digest = capture(source)
        base.require(digest == expect_digest, "source content does not match expected digest")
        base.require(not os.path.lexists(receipt), "receipt already exists; preserve it")
        base.require(not os.path.lexists(selector), "version command exists; preserve it")
        namespace_dirs = [prefix / "share/towerops", prefix / "share/towerops/explorer",
                          prefix / "share/towerops/explorer/releases"]
        missing = []
        for path in namespace_dirs:
            if os.path.lexists(path):
                base.directories(path, owned_leaf=True)
            else:
                missing.append(path)
        base.require(not os.path.lexists(release), "release exists; preserve and inspect it")
        base.require(capture(source)[1] == inputs, "source custody changed before installation")
        receipt_fd = os.open(receipt, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        outcome["created"].append(str(receipt))
        os.fchmod(receipt_fd, 0o600)
        outcome.update(inputs=inputs, phase="namespace")
        base.save_receipt(receipt_fd, receipt, outcome)
        for path in missing:
            base.mkdir_new(path, outcome["created"])
        base.mkdir_new(release, outcome["created"])
        base.mkdir_new(release / "web", outcome["created"])
        outcome["phase"] = "release"
        expected = {}
        for name, raw in bodies.items():
            mode = FILES[name]
            base.write_new(release / name, raw, mode, outcome["created"])
            expected[name] = (raw, mode)
        launcher = ("#!/bin/sh\nexec /usr/bin/python3 -B "
                    + shlex.quote(str(release / "explorer.py")) + ' serve "$@"\n').encode()
        base.write_new(wrapper, launcher, 0o755, outcome["created"])
        expected["towerops-explorer"] = (launcher, 0o755)
        provenance = {
            "schema": "towerops.explorer-staged-version.v1", "digest": digest,
            "manifest": manifest, "wrapper": base.bytes_identity(launcher),
            "python": "/usr/bin/python3", "installed_at": base.utc_now(),
            "purpose": "Additional foreground loopback Synthetic Explorer; content identity only.",
        }
        provenance_bytes = base.encoded(provenance)
        base.write_new(release / "installation.json", provenance_bytes, 0o644, outcome["created"])
        expected["installation.json"] = (provenance_bytes, 0o644)
        installed = base.installed_identity(release, expected)
        base.require(capture(source)[1] == inputs, "source custody changed before selector publication")
        outcome["phase"] = "selector"
        os.symlink(str(wrapper), selector)
        outcome["created"].append(str(selector))
        base.sync_dir(selector.parent)
        base.require(selector.is_symlink() and os.readlink(selector) == str(wrapper),
                     "new selector differs")
        base.require(base.installed_identity(release, expected) == installed,
                     "new version changed during selector publication")
        base.require(capture(source)[1] == inputs, "source custody changed after publication")
        outcome.update(ok=True, phase="complete", finished=base.utc_now(),
                       installed=installed, selector_target=str(wrapper))
        base.save_receipt(receipt_fd, receipt, outcome)
        return outcome
    except (OSError, base.InstallError) as exc:
        outcome.update(ok=False, error=str(exc), finished=base.utc_now())
        if receipt_fd is not None:
            try:
                base.save_receipt(receipt_fd, receipt, outcome)
            except (OSError, base.InstallError) as receipt_error:
                outcome["receipt_write_error"] = str(receipt_error)
        raise base.InstallError(str(exc), outcome) from exc
    finally:
        if receipt_fd is not None:
            os.close(receipt_fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    view = commands.add_parser("inspect", allow_abbrev=False)
    view.add_argument("--source-dir", type=Path, required=True)
    stage = commands.add_parser("install", allow_abbrev=False)
    stage.add_argument("--source-dir", type=Path, required=True)
    stage.add_argument("--prefix", type=Path, required=True)
    stage.add_argument("--expect-digest", required=True)
    stage.add_argument("--receipt-new", type=Path, required=True)
    args = parser.parse_args(argv)
    result = None
    try:
        base.require(sys.platform == "linux" and sys.version_info >= (3, 12),
                     "Linux and Python 3.12 or newer are required")
        if args.command == "inspect":
            summary = inspect(args.source_dir)
        else:
            result = install(args.source_dir, args.prefix, args.expect_digest, args.receipt_new)
            summary = {key: result[key] for key in ("ok", "digest", "release", "selector", "receipt")}
        print(base.encoded(summary).decode("ascii"), end="", flush=True)
        return 0
    except (base.InstallError, OSError, UnicodeError) as exc:
        if isinstance(exc, (OSError, UnicodeError)):
            sys.stdout = io.StringIO()
        detail = {"ok": False, "error": str(exc)}
        if isinstance(exc, base.InstallError) and exc.outcome is not None:
            detail["outcome"] = exc.outcome
        elif result is not None:
            detail.update(phase="console", installation_receipt=result["receipt"],
                          selector_may_exist=True)
        print(json.dumps(detail, ensure_ascii=True, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
