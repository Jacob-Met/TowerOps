"""Focused tests for additional Explorer releases and retained failure state."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stage_explorer", ROOT / "tools/stage_explorer.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class Releases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="towerops-release-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        (self.source / "web").mkdir(parents=True)
        for name in stage.FILES:
            (self.source / name).write_text("retained source " + name + "\n")
        # This deliberately tiny fixture runs only when the installed command is invoked.
        (self.source / "explorer.py").write_text(
            "import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
        self.prefix = self.root / "prefix with ' quote"
        (self.prefix / "bin").mkdir(parents=True)
        (self.prefix / "share/towerops/explorer/old").mkdir(parents=True)
        self.old = self.prefix / "share/towerops/explorer/old/towerops-explorer"
        self.old.write_text("old bytes\n")
        self.default = self.prefix / "bin/towerops-explorer"
        self.default.symlink_to(self.old)
        self.receipt = self.root / "receipt.json"

    def digest(self):
        # Build the specified content identity without the candidate capture/encoding helpers.
        rows = []
        for name in sorted(stage.FILES):
            raw = (self.source / name).read_bytes()
            rows.append(dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                             mode=493 if name == "explorer.py" else 420))
        manifest = {"schema": "towerops.explorer-content.v1", "files": rows}
        raw = (json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("ascii")
        return hashlib.sha256(raw).hexdigest(), manifest

    def install(self, digest=None, receipt=None):
        return stage.install(self.source, self.prefix, digest or self.digest()[0], receipt or self.receipt)

    def unchanged_default(self, before):
        self.assertEqual(self.retained(), before)

    @staticmethod
    def identity(path, follow=True):
        info = path.stat() if follow else path.lstat()
        # Reading a file or symlink can update atime; preserve modification/custody fields.
        return tuple(getattr(info, key) for key in (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size",
            "st_mtime_ns", "st_ctime_ns"))

    def retained(self):
        return os.readlink(self.default), self.identity(self.default, False), self.old.read_bytes()

    def test_inspect_content_identity_and_ignored_extra(self):
        (self.source / "unselected.py").write_text("raise RuntimeError('never executed')\n")
        expected, manifest = self.digest()
        result = stage.inspect(self.source)
        self.assertEqual(result, {"ok": True, "digest": expected, "manifest": manifest})
        (self.source / "web/app.js").write_text("changed\n")
        self.assertNotEqual(stage.inspect(self.source)["digest"], expected)
        self.assertFalse(self.receipt.exists())

    def test_two_releases_and_quote_safe_real_launcher_preserve_default(self):
        old = self.retained()
        first = self.install()
        self.assertEqual(first["phase"], "complete")
        self.assertTrue(first["ok"])
        self.assertEqual(len(first["installed"]), 10)
        self.assertEqual(stat.S_IMODE(self.receipt.stat().st_mode), 0o600)
        self.assertEqual(json.loads(self.receipt.read_text()), first)
        run = subprocess.run([first["selector"], "--port", "0", "literal ' value"],
                             capture_output=True, timeout=5, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), ["serve", "--port", "0", "literal ' value"])
        first_files = {p.relative_to(first["release"]).as_posix(): (p.read_bytes(), self.identity(p))
                       for p in Path(first["release"]).rglob("*") if p.is_file()}
        (self.source / "web/app.js").write_text("second release\n")
        second = self.install(receipt=self.root / "second.json")
        self.assertNotEqual(first["selector"], second["selector"])
        self.assertEqual(first_files, {p.relative_to(first["release"]).as_posix(): (p.read_bytes(), self.identity(p))
                                     for p in Path(first["release"]).rglob("*") if p.is_file()})
        self.unchanged_default(old)
        self.assertFalse((Path(first["release"]) / "__pycache__").exists())

    def test_wrong_digest_writes_nothing_then_corrected_install(self):
        old = self.retained()
        with self.assertRaises(stage.base.InstallError):
            self.install("0" * 64)
        self.assertFalse(self.receipt.exists())
        self.assertFalse((self.prefix / "share/towerops/explorer/releases").exists())
        self.assertTrue(self.install()["ok"])
        self.unchanged_default(old)

    def test_repeat_and_dangling_selector_preserve_existing_entries(self):
        first = self.install()
        original_receipt = self.receipt.read_bytes()
        repeat_receipt = self.root / "repeat.json"
        with self.assertRaises(stage.base.InstallError):
            self.install(receipt=repeat_receipt)
        self.assertFalse(repeat_receipt.exists())
        self.assertEqual(self.receipt.read_bytes(), original_receipt)
        (self.source / "web/app.js").write_text("new composition\n")
        digest = self.digest()[0]
        alias = self.prefix / "bin" / ("towerops-explorer-" + digest[:12])
        alias.symlink_to(self.root / "missing")
        with self.assertRaises(stage.base.InstallError):
            self.install(receipt=repeat_receipt)
        self.assertFalse(repeat_receipt.exists())
        self.assertTrue(alias.is_symlink())
        self.assertTrue(Path(first["release"]).is_dir())

    def test_selected_symlink_and_symlink_ancestor_refuse(self):
        selected = self.source / "web/app.js"
        selected.unlink(); selected.symlink_to(self.old)
        with self.assertRaises((stage.base.InstallError, OSError)):
            stage.inspect(self.source)
        selected.unlink(); selected.write_text("restored\n")
        linked = self.root / "linked-source"; linked.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(stage.base.InstallError):
            stage.inspect(linked)
        self.assertFalse(self.receipt.exists())

    def test_source_bounds_and_singly_linked_requirement(self):
        file = self.source / "web/app.js"
        file.write_bytes(b"x" * (1_048_576 + 1))
        with self.assertRaises(stage.base.InstallError):
            stage.inspect(self.source)
        file.write_bytes(b"x" * 1_048_576)
        (self.source / "web/index.html").write_bytes(b"y" * 1_048_576)
        with self.assertRaises(stage.base.InstallError):
            stage.inspect(self.source)
        file.write_text("small\n"); (self.source / "web/index.html").write_text("small\n")
        os.link(file, self.root / "hardlink")
        with self.assertRaises(stage.base.InstallError):
            stage.inspect(self.source)

    def test_overlapping_paths_and_existing_receipt_refuse_without_write(self):
        digest = self.digest()[0]
        for prefix, receipt in [(self.source, self.receipt),
                                (self.prefix, self.source / "receipt.json"),
                                (self.prefix, self.prefix / "receipt.json")]:
            with self.assertRaises(stage.base.InstallError):
                stage.install(self.source, prefix, digest, receipt)
            self.assertFalse(receipt.exists())
        self.receipt.write_text("retained receipt\n")
        with self.assertRaises(stage.base.InstallError):
            self.install()
        self.assertEqual(self.receipt.read_text(), "retained receipt\n")

    def test_partial_write_retained_and_selector_absent(self):
        original = stage.base.write_new
        def fail_after_first(path, raw, mode, created):
            original(path, raw, mode, created)
            raise OSError("deliberate after first completed write")
        with patch.object(stage.base, "write_new", side_effect=fail_after_first):
            with self.assertRaises(stage.base.InstallError) as caught:
                self.install()
        outcome = caught.exception.outcome
        self.assertEqual(outcome["phase"], "release")
        self.assertFalse(outcome["ok"])
        self.assertTrue((Path(outcome["release"]) / "EXPLORER.md").is_file())
        self.assertFalse(os.path.lexists(outcome["selector"]))
        self.assertEqual(json.loads(self.receipt.read_text()), outcome)

    def test_late_directory_sync_failure_retains_selected_release(self):
        original = stage.base.sync_dir
        def fail_once(path):
            if path == self.prefix / "bin":
                raise OSError("deliberate selected directory sync failure")
            return original(path)
        with patch.object(stage.base, "sync_dir", side_effect=fail_once):
            with self.assertRaises(stage.base.InstallError) as caught:
                self.install()
        outcome = caught.exception.outcome
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["phase"], "selector")
        self.assertEqual(os.readlink(outcome["selector"]), str(Path(outcome["release"]) / "towerops-explorer"))
        self.assertEqual(json.loads(self.receipt.read_text()), outcome)

    def test_input_change_after_write_refuses_selector_and_keeps_receipt(self):
        original = stage.base.write_new
        changed = False
        def mutate_after_write(path, raw, mode, created):
            nonlocal changed
            original(path, raw, mode, created)
            if not changed:
                changed = True
                (self.source / "web/app.js").write_text("external change during staging\n")
        with patch.object(stage.base, "write_new", side_effect=mutate_after_write):
            with self.assertRaises(stage.base.InstallError) as caught:
                self.install()
        self.assertIn("source custody changed", str(caught.exception))
        self.assertFalse(os.path.lexists(caught.exception.outcome["selector"]))
        self.assertFalse(json.loads(self.receipt.read_text())["ok"])

    def test_console_failure_reports_successful_receipt_and_keeps_command(self):
        class BrokenOutput:
            def write(self, _value):
                raise OSError("deliberate stdout failure")
            def flush(self):
                pass
        stderr = io.StringIO()
        with contextlib.redirect_stdout(BrokenOutput()), contextlib.redirect_stderr(stderr):
            code = stage.main(["install", "--source-dir", str(self.source), "--prefix", str(self.prefix),
                               "--expect-digest", self.digest()[0], "--receipt-new", str(self.receipt)])
        self.assertEqual(code, 2)
        error = json.loads(stderr.getvalue())
        self.assertTrue(error["selector_may_exist"])
        result = json.loads(self.receipt.read_text())
        self.assertTrue(result["ok"])
        self.assertTrue(Path(result["selector"]).is_symlink())


if __name__ == "__main__":
    unittest.main(verbosity=2)
