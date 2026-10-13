"""Temporary-layout controls for the fixed ThinkPad Explorer adoption."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "tools/install_explorer.py"
ACCEPTED = ROOT / "docs/qualification/explorer-install-anvil-d3745/accepted-source"
spec = importlib.util.spec_from_file_location("explorer_installer", INSTALLER)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def snapshot(root):
    if not os.path.lexists(root):
        return None
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        value = [info.st_mode, info.st_uid, info.st_gid, info.st_ino, info.st_mtime_ns]
        if stat.S_ISLNK(info.st_mode):
            value.append(os.readlink(path))
        elif stat.S_ISREG(info.st_mode):
            value.append(hashlib.sha256(path.read_bytes()).hexdigest())
        result[path.relative_to(root).as_posix()] = value
    return result


class ExplorerInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="towerops-install-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.prefix = self.work / "prefix with spaces"
        (self.prefix / "bin").mkdir(parents=True)
        (self.prefix / "share").mkdir()
        self.source = self.work / "accepted source"
        shutil.copytree(ACCEPTED, self.source)
        self.receipt = self.work / "install.json"
        self.namespace = self.prefix / "share/towerops"
        self.release = self.namespace / "explorer" / installer.VERSION
        self.alias = self.prefix / "bin/towerops-explorer"
        self.neighbor = self.prefix / "bin/unchanged-command"
        self.neighbor.write_bytes(b"untouched neighboring command\n")
        self.neighbor.chmod(0o755)
        self.source_before = snapshot(self.source)
        self.neighbor_before = snapshot(self.neighbor)

    def deploy(self, receipt=None):
        return installer.deploy(self.source, receipt or self.receipt, self.prefix)

    def assert_protected(self):
        self.assertEqual(snapshot(self.source), self.source_before)
        self.assertEqual(snapshot(self.neighbor), self.neighbor_before)

    def child(self, args=None, *, output=subprocess.PIPE, file_limit=None, wrong_host=False):
        flags = ["-B"] + (["-O"] if sys.flags.optimize else [])
        code = (
            "import importlib.util,sys,signal,resource; "
            f"s=importlib.util.spec_from_file_location('installer',{str(INSTALLER)!r}); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            f"m.PREFIX=m.Path({str(self.prefix)!r}); "
        )
        if wrong_host:
            code += "m.socket.gethostname=lambda:'different-host'; "
        else:
            code += "m.host_identity=lambda:None; "
        if file_limit is not None:
            code += (
                "signal.signal(signal.SIGXFSZ,signal.SIG_IGN); "
                f"resource.setrlimit(resource.RLIMIT_FSIZE,({file_limit},{file_limit})); "
            )
        arguments = args if args is not None else [
            "--source-dir", str(self.source), "--receipt-new", str(self.receipt)
        ]
        code += f"sys.exit(m.main({arguments!r}))"
        return subprocess.run(
            [sys.executable, *flags, "-c", code], cwd=self.work,
            stdout=output, stderr=subprocess.PIPE, timeout=20, check=False,
        )

    def test_install_exact_files_manifest_wrapper_and_repeat_refusal(self):
        result = self.deploy()
        self.assertTrue(result["ok"])
        self.assertFalse(result["server_started"])
        self.assertFalse(result["path_edited"])
        self.assertEqual(self.alias.readlink(), self.release / "towerops-explorer")
        files = {p.relative_to(self.release).as_posix() for p in self.release.rglob("*") if p.is_file()}
        self.assertEqual(files, set(installer.PINS) | {"installation.json", "towerops-explorer"})
        for name, (size, digest, mode) in installer.PINS.items():
            path = self.release / name
            self.assertEqual(path.read_bytes(), (self.source / name).read_bytes())
            self.assertEqual((path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest(),
                              stat.S_IMODE(path.stat().st_mode)), (size, digest, mode))
        provenance = json.loads((self.release / "installation.json").read_text())
        self.assertEqual(provenance["accepted_source"], installer.VERSION)
        self.assertEqual(set(provenance["source_files"]), set(installer.PINS))
        # Actual installed-style shell invocation from an unrelated cwd with spaces.
        command = subprocess.run([str(self.alias), "--help"], cwd=self.work,
                                 capture_output=True, timeout=10, check=False)
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertIn(b"--port", command.stdout)
        self.assertNotIn(b"__pycache__", b"\n".join(str(p).encode() for p in self.release.rglob("*")))
        previous = snapshot(self.prefix)
        second = self.work / "new-receipt.json"
        with self.assertRaises(installer.InstallError):
            self.deploy(second)
        self.assertFalse(second.exists())
        self.assertEqual(snapshot(self.prefix), previous)
        self.assert_protected()

    def test_wrong_source_refuses_without_writes_then_explicit_correction(self):
        target = self.source / "web/app.js"
        original = target.read_bytes()
        target.write_bytes(original[:-1] + b"!")
        before = snapshot(self.prefix)
        with self.assertRaisesRegex(installer.InstallError, "unaccepted source"):
            self.deploy()
        self.assertFalse(self.receipt.exists())
        self.assertEqual(snapshot(self.prefix), before)
        target.write_bytes(original)
        self.source_before = snapshot(self.source)
        self.assertTrue(self.deploy()["ok"])
        self.assert_protected()

    def test_missing_linked_hardlinked_and_fifo_sources_refuse(self):
        target = self.source / "web/app.js"
        original = target.read_bytes()
        for kind in ("missing", "symlink", "hardlink", "fifo"):
            with self.subTest(kind=kind):
                target.unlink()
                other = self.work / ("outside-" + kind)
                other.write_bytes(original)
                if kind == "symlink":
                    target.symlink_to(other)
                elif kind == "hardlink":
                    os.link(other, target)
                elif kind == "fifo":
                    os.mkfifo(target)
                before = snapshot(self.prefix)
                with self.assertRaises(installer.InstallError):
                    self.deploy()
                self.assertFalse(self.receipt.exists())
                self.assertEqual(snapshot(self.prefix), before)
                if os.path.lexists(target):
                    target.unlink()
                target.write_bytes(original)

    def test_occupied_selector_variants_preserve_everything(self):
        for kind in ("file", "directory", "symlink", "dangling"):
            with self.subTest(kind=kind):
                if kind == "file":
                    self.alias.write_bytes(b"existing owner\n")
                elif kind == "directory":
                    self.alias.mkdir()
                else:
                    self.alias.symlink_to(self.neighbor if kind == "symlink" else self.work / "absent")
                before = snapshot(self.prefix)
                with self.assertRaisesRegex(installer.InstallError, "selector exists"):
                    self.deploy()
                self.assertFalse(self.receipt.exists())
                self.assertEqual(snapshot(self.prefix), before)
                if self.alias.is_dir() and not self.alias.is_symlink():
                    self.alias.rmdir()
                else:
                    self.alias.unlink()
        self.assert_protected()

    def test_occupied_namespace_variants_preserve_everything(self):
        for kind in ("file", "directory", "symlink", "dangling"):
            with self.subTest(kind=kind):
                if kind == "file":
                    self.namespace.write_bytes(b"other version owner\n")
                elif kind == "directory":
                    self.namespace.mkdir()
                    (self.namespace / "old-version").write_bytes(b"working")
                else:
                    self.namespace.symlink_to(self.source if kind == "symlink" else self.work / "absent")
                before = snapshot(self.prefix)
                with self.assertRaisesRegex(installer.InstallError, "namespace exists"):
                    self.deploy()
                self.assertFalse(self.receipt.exists())
                self.assertEqual(snapshot(self.prefix), before)
                if kind == "directory":
                    shutil.rmtree(self.namespace)
                else:
                    self.namespace.unlink()
        self.assert_protected()

    def test_symlink_ancestry_and_receipt_placement_refuse_before_writes(self):
        linked = self.work / "linked-source-parent"
        linked.symlink_to(self.source.parent, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            installer.deploy(linked / self.source.name, self.receipt, self.prefix)
        with self.assertRaisesRegex(installer.InstallError, "outside"):
            self.deploy(self.prefix / "receipt.json")
        self.receipt.write_bytes(b"existing receipt")
        with self.assertRaises(installer.InstallError):
            self.deploy()
        self.assertEqual(self.receipt.read_bytes(), b"existing receipt")
        self.assertFalse(self.namespace.exists())
        self.receipt.unlink()
        self.receipt.symlink_to(self.work / "missing-receipt")
        with self.assertRaises(installer.InstallError):
            self.deploy()
        self.assertTrue(self.receipt.is_symlink())
        self.assertFalse((self.work / "missing-receipt").exists())
        self.assertFalse(self.namespace.exists())
        self.assert_protected()

    def test_source_change_after_capture_cannot_publish_selector(self):
        target = self.source / "web/app.js"
        original = target.read_bytes()
        real_write = installer.write_new
        changed = False

        def change_after_copy(path, raw, mode, created):
            nonlocal changed
            real_write(path, raw, mode, created)
            if not changed:
                changed = True
                target.write_bytes(original[:-1] + b"!")

        with mock.patch.object(installer, "write_new", side_effect=change_after_copy):
            with self.assertRaises(installer.InstallError):
                self.deploy()
        self.assertFalse(os.path.lexists(self.alias))
        self.assertEqual((self.release / "web/app.js").read_bytes(), original)
        self.assertFalse(json.loads(self.receipt.read_text())["ok"])
        self.assertEqual(snapshot(self.neighbor), self.neighbor_before)

    def test_namespace_sync_failure_retains_partial_receipt_without_selector(self):
        real_sync = installer.sync_dir

        def fail_new_namespace_parent(path):
            if path == self.prefix / "share" and self.namespace.exists():
                raise OSError("authored namespace sync refusal")
            real_sync(path)

        with mock.patch.object(installer, "sync_dir", side_effect=fail_new_namespace_parent):
            with self.assertRaises(installer.InstallError):
                self.deploy()
        self.assertTrue(self.namespace.is_dir())
        self.assertFalse(os.path.lexists(self.alias))
        report = json.loads(self.receipt.read_text())
        self.assertFalse(report["ok"])
        self.assertIn(str(self.namespace), report["created"])
        self.assertEqual(report["phase"], "namespace")
        self.assert_protected()

    def test_real_bounded_file_write_failure_keeps_partial_version_and_no_selector(self):
        result = self.child(file_limit=16384)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertFalse(os.path.lexists(self.alias))
        self.assertTrue(self.release.is_dir())
        partial = self.release / "towerops.py"
        self.assertTrue(partial.is_file())
        self.assertLess(partial.stat().st_size, installer.PINS["towerops.py"][0])
        report = json.loads(self.receipt.read_text())
        self.assertFalse(report["ok"])
        self.assertIn(str(partial), report["created"])
        before = snapshot(self.prefix)
        with self.assertRaises(installer.InstallError):
            self.deploy(self.work / "retry.json")
        self.assertEqual(snapshot(self.prefix), before)
        self.assert_protected()

    def test_selector_collision_is_never_replaced(self):
        real_symlink = os.symlink

        def competing_selector(source, destination):
            Path(destination).write_bytes(b"new neighboring owner")
            real_symlink(source, destination)

        with mock.patch.object(installer.os, "symlink", side_effect=competing_selector):
            with self.assertRaises(installer.InstallError):
                self.deploy()
        self.assertEqual(self.alias.read_bytes(), b"new neighboring owner")
        self.assertFalse(self.alias.is_symlink())
        self.assertFalse(json.loads(self.receipt.read_text())["ok"])
        self.assert_protected()

    def test_late_receipt_failure_reports_published_selector_without_rollback(self):
        real_save = installer.save_receipt

        def refuse_completed_receipt(fd, path, value):
            if value["ok"]:
                raise OSError("authored final receipt failure")
            real_save(fd, path, value)

        with mock.patch.object(installer, "save_receipt", side_effect=refuse_completed_receipt):
            with self.assertRaises(installer.InstallError):
                self.deploy()
        self.assertTrue(self.alias.is_symlink())
        report = json.loads(self.receipt.read_text())
        self.assertFalse(report["ok"])
        self.assertIn("final receipt failure", report["error"])
        self.assertEqual(self.alias.readlink(), self.release / "towerops-explorer")
        self.assert_protected()

    def test_real_stdout_failure_leaves_inspectable_successful_installation(self):
        if not Path("/dev/full").exists():
            self.skipTest("/dev/full unavailable")
        with open("/dev/full", "wb", buffering=0) as sink:
            result = self.child(output=sink)
        self.assertEqual(result.returncode, 2, result.stderr)
        detail = json.loads(result.stderr)
        self.assertTrue(detail["selector_may_exist"])
        self.assertEqual(detail["phase"], "console")
        self.assertTrue(json.loads(self.receipt.read_text())["ok"])
        self.assertTrue(self.alias.is_symlink())
        self.assertNotIn(b"Exception ignored", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assert_protected()

    def test_actual_main_success_and_argument_host_refusals(self):
        before = snapshot(self.prefix)
        wrong = self.child(wrong_host=True)
        self.assertEqual(wrong.returncode, 2, wrong.stderr)
        self.assertEqual(wrong.stdout, b"")
        self.assertIn(b"restricted", wrong.stderr)
        unknown = self.child(["--unknown-option"])
        self.assertEqual(unknown.returncode, 2)
        self.assertEqual(unknown.stdout, b"")
        self.assertFalse(self.receipt.exists())
        self.assertEqual(snapshot(self.prefix), before)
        result = self.child()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["accepted_source"], installer.VERSION)
        self.assertEqual(report["selector"], str(self.alias))
        self.assertEqual(report["receipt"], str(self.receipt))
        self.assertEqual(result.stderr, b"")
        self.assert_protected()


if __name__ == "__main__":
    unittest.main()
