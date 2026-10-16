"""Receive complete, exclusive saved reports through the native CLI."""

from __future__ import annotations

import errno
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import plan_world
from towerops import Aircraft, WorldState

CLI = Path(__file__).resolve().parents[1] / "plan_world.py"


def world_bytes(kind: str = "options") -> bytes:
    aircraft = (
        Aircraft("EAST", -8.0, 1.0, 12000.0, 2.0, 0.0),
        Aircraft("WEST", 8.0, 1.0, 12000.0, -2.0, 0.0),
    )
    if kind == "empty":
        aircraft = ()
    elif kind == "overlap":
        aircraft = tuple(Aircraft(name, 0.0, 0.0, 12000.0, 0.0, 0.0)
                         for name in ("ONE", "TWO"))
    return (json.dumps(WorldState(7, 120.0, aircraft).to_dict(), indent=2) + "\n").encode()


def run_cli(source: Path | str, *args: str | Path, raw: bytes | None = None):
    return subprocess.run(
        [sys.executable, "-B", str(CLI), str(source), *map(str, args)],
        input=raw, capture_output=True, timeout=15, check=False,
    )


def snapshot(directory: Path) -> dict:
    result = {}
    for path in directory.rglob("*"):
        info = path.lstat()
        value = ("link", os.readlink(path)) if path.is_symlink() else (
            ("file", path.read_bytes()) if path.is_file() else ("directory",)
        )
        result[str(path.relative_to(directory))] = (info.st_ino, info.st_mode, value)
    return result


class SavedWorldPlanOutput(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "world.json"
        self.source.write_bytes(world_bytes())
        self.target = self.root / "review.json"

    def call_main(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = plan_world.main([str(self.source), "--output", str(self.target)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_saved_bytes_match_ordinary_report_for_native_outcomes_and_options(self):
        cases = (
            ("options", (), "options_available"),
            ("empty", (), "no_conflict"),
            ("overlap", (), "no_admitted_option"),
            ("options", ("--now", "125", "--horizontal-nm", "3",
                         "--vertical-ft", "800", "--horizon-min", "4"), "options_available"),
        )
        for index, (kind, args, status) in enumerate(cases):
            with self.subTest(kind=kind, args=args):
                raw = world_bytes(kind)
                self.source.write_bytes(raw)
                before = snapshot(self.root)
                ordinary = run_cli(self.source, *args)
                self.assertEqual((ordinary.returncode, ordinary.stderr), (0, b""))
                self.assertEqual(snapshot(self.root), before)
                self.assertEqual(json.loads(ordinary.stdout)["status"], status)
                target = self.root / f"review-{index}.json"
                saved = run_cli(self.source, *args, "--output", target)
                self.assertEqual((saved.returncode, saved.stdout, saved.stderr), (0, b"", b""))
                self.assertEqual(target.read_bytes(), ordinary.stdout)
                self.assertEqual(self.source.read_bytes(), raw)
                self.assertEqual(set(snapshot(self.root)), set(before) | {target.name})

    def test_stdin_can_save_the_same_complete_report(self):
        raw = world_bytes()
        ordinary = run_cli("-", raw=raw)
        saved = run_cli("-", "--output", self.target, raw=raw)
        self.assertEqual((ordinary.returncode, ordinary.stderr), (0, b""))
        self.assertEqual((saved.returncode, saved.stdout, saved.stderr), (0, b"", b""))
        self.assertEqual(self.target.read_bytes(), ordinary.stdout)

    def test_occupied_files_links_directories_and_input_aliases_are_retained(self):
        def make_target(kind, directory, source):
            target = directory / "review.json"
            if kind == "input":
                return source
            if kind == "alias":
                (directory / "nested").mkdir()
                return directory / "nested" / ".." / source.name
            if kind == "directory":
                target.mkdir()
            elif kind == "symlink":
                target.symlink_to(source)
            elif kind == "dangling":
                target.symlink_to(directory / "absent.json")
            elif kind == "hardlink":
                os.link(source, target)
            else:
                target.write_bytes(b"" if kind == "empty" else b"previous report\n")
            return target

        for kind in ("empty", "nonempty", "directory", "input", "alias",
                     "symlink", "dangling", "hardlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                source = directory / "world.json"
                source.write_bytes(world_bytes())
                try:
                    target = make_target(kind, directory, source)
                except (NotImplementedError, OSError) as exc:
                    if kind in ("symlink", "dangling", "hardlink"):
                        self.skipTest(f"Filesystem cannot create {kind}: {exc}")
                    raise
                before = snapshot(directory)
                result = run_cli(source, "--output", target)
                self.assertEqual((result.returncode, result.stdout), (2, b""))
                self.assertIn(b"already exists", result.stderr)
                self.assertEqual(snapshot(directory), before)

    def test_occupied_destination_is_refused_before_stdin_read(self):
        self.target.write_bytes(b"retained")
        with patch.object(plan_world.sys, "stdin") as stdin:
            stdin.buffer.read.side_effect = AssertionError("must not read stdin")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = plan_world.main(["-", "--output", str(self.target)])
            stdin.buffer.read.assert_not_called()
        self.assertEqual(code, 2)
        self.assertEqual(self.target.read_bytes(), b"retained")

    def test_invalid_inputs_and_arguments_create_no_report(self):
        cases = (
            (b"{", (), 2),
            (b'{"version":7,"version":8,"observed_at":120,"aircraft":[]}', (), 2),
            (world_bytes(), ("--now", "131"), 1),
            (world_bytes(), ("--horizontal-nm", "0"), 2),
            (world_bytes(), ("--now", "not-a-number"), 2),
            (world_bytes(), ("--unknown-plan-option",), 2),
        )
        for raw, args, code in cases:
            with self.subTest(args=args, raw=raw[:20]):
                self.source.write_bytes(raw)
                before = snapshot(self.root)
                result = run_cli(self.source, *args, "--output", self.target)
                self.assertEqual((result.returncode, result.stdout), (code, b""))
                self.assertTrue(result.stderr)
                self.assertEqual(snapshot(self.root), before)

    def test_missing_parent_is_not_created_and_missing_output_argument_is_refused(self):
        before = snapshot(self.root)
        for args in (("--output", self.root / "missing" / "review.json"), ("--output",)):
            with self.subTest(args=args):
                result = run_cli(self.source, *args)
                self.assertEqual((result.returncode, result.stdout), (2, b""))
                self.assertTrue(result.stderr)
                self.assertEqual(snapshot(self.root), before)

    def test_publication_exposes_only_the_complete_flushed_report(self):
        expected = run_cli(self.source).stdout
        real_link, real_fsync = os.link, os.fsync
        events = []

        def receive_flush(descriptor):
            self.assertFalse(os.path.lexists(self.target))
            real_fsync(descriptor)
            events.append("flushed")

        def receive_link(temporary, target):
            self.assertEqual(events, ["flushed"])
            self.assertFalse(os.path.lexists(target))
            self.assertEqual(Path(temporary).parent, self.target.parent)
            self.assertEqual(Path(temporary).read_bytes(), expected)
            real_link(temporary, target)
            self.assertEqual(Path(target).read_bytes(), expected)
            events.append("published")

        with patch.object(plan_world.os, "fsync", side_effect=receive_flush), \
                patch.object(plan_world.os, "link", side_effect=receive_link):
            self.assertEqual(self.call_main(), (0, "", ""))
        self.assertEqual(events, ["flushed", "published"])
        self.assertEqual(set(snapshot(self.root)), {"world.json", "review.json"})

    def test_creator_at_publication_cannot_be_overwritten(self):
        real_link = os.link
        winner = b"another creator owns this file\n"

        def racing_link(temporary, target):
            with Path(target).open("xb") as stream:
                stream.write(winner)
            real_link(temporary, target)

        with patch.object(plan_world.os, "link", side_effect=racing_link):
            code, stdout, stderr = self.call_main()
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("cannot write report", stderr)
        self.assertEqual(self.target.read_bytes(), winner)
        self.assertEqual(self.source.read_bytes(), world_bytes())
        self.assertEqual(set(snapshot(self.root)), {"world.json", "review.json"})

    def test_two_processes_publish_exactly_one_complete_report(self):
        expected = run_cli(self.source).stdout
        command = [sys.executable, "-B", str(CLI), str(self.source), "--output", str(self.target)]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for _ in range(2)]
        try:
            results = [(process, process.communicate(timeout=15)) for process in processes]
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        self.assertEqual(sorted(process.returncode for process in processes), [0, 2])
        for process, (stdout, stderr) in results:
            self.assertEqual(stdout, b"")
            self.assertEqual(bool(stderr), process.returncode != 0)
        self.assertEqual(self.target.read_bytes(), expected)
        self.assertEqual(set(snapshot(self.root)), {"world.json", "review.json"})

    def test_partial_stage_write_is_cleaned_without_publishing(self):
        real_fdopen = os.fdopen

        class PartialWrite:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def write(self, text):
                self.stream.write(text[:17])
                self.stream.flush()
                raise OSError(errno.ENOSPC, "injected partial staging write")

        def partial_fdopen(descriptor, mode, **kwargs):
            stream = real_fdopen(descriptor, mode, **kwargs)
            return PartialWrite(stream) if mode == "w" else stream

        before = snapshot(self.root)
        with patch.object(plan_world.os, "fdopen", side_effect=partial_fdopen), \
                patch.object(plan_world.os, "link") as link:
            code, stdout, stderr = self.call_main()
            link.assert_not_called()
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("partial staging write", stderr)
        self.assertEqual(snapshot(self.root), before)

    def test_flush_and_unsupported_link_failures_leave_no_output_or_temporary(self):
        for function, error in (("fsync", errno.ENOSPC), ("link", errno.EPERM)):
            with self.subTest(function=function):
                before = snapshot(self.root)
                with patch.object(plan_world.os, function,
                                  side_effect=OSError(error, "injected publication refusal")):
                    code, stdout, stderr = self.call_main()
                self.assertEqual((code, stdout), (2, ""))
                self.assertIn("publication refusal", stderr)
                self.assertEqual(snapshot(self.root), before)

    def test_stream_conversion_failure_closes_the_staging_descriptor(self):
        descriptor = None
        real_fdopen = os.fdopen

        def fail_fdopen(fd, mode, **kwargs):
            nonlocal descriptor
            if mode != "w":
                return real_fdopen(fd, mode, **kwargs)
            descriptor = fd
            raise OSError(errno.EMFILE, "injected stream conversion refusal")

        before = snapshot(self.root)
        with patch.object(plan_world.os, "fdopen", side_effect=fail_fdopen):
            code, stdout, stderr = self.call_main()
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("stream conversion refusal", stderr)
        self.assertEqual(snapshot(self.root), before)
        with self.assertRaises(OSError) as caught:
            os.fstat(descriptor)
        self.assertEqual(caught.exception.errno, errno.EBADF)

    def test_cleanup_refusal_retains_the_complete_published_report(self):
        expected = run_cli(self.source).stdout
        with patch.object(plan_world.Path, "unlink",
                          side_effect=PermissionError("injected cleanup refusal")):
            code, stdout, stderr = self.call_main()
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("cleanup refusal", stderr)
        self.assertEqual(self.target.read_bytes(), expected)
        self.assertEqual(self.source.read_bytes(), world_bytes())
        remaining = list(self.root.glob(".towerops-plan-*.tmp"))
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].read_bytes(), expected)
        remaining[0].unlink()


if __name__ == "__main__":
    unittest.main()
