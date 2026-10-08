"""Independent comparison receiving; frozen before candidate exposure."""
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import zlib

def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load_packet(path):
    packed = zlib.decompress(base64.b64decode(Path(path).read_text("ascii"), validate=False))
    packet = json.loads(packed)
    assert packet["format"] == "towerops.independent-comparison-fixtures.v1"
    for name, row in packet["files"].items():
        assert Path(name).name == name and name.endswith(".json")
        raw = bytes.fromhex(row["hex"])
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"]
    return packet

def verify_result(actual, expected):
    assert actual["format"] == "towerops.plan-comparison.v1"
    for key in ("world", "world_hash", "reviewed_at", "left", "right", "counts", "entries"):
        assert canonical(actual[key]) == canonical(expected[key]), key
    changes = actual["policy_changes"]
    assert len(changes) == len(expected["policy_changes"])
    by_field = {row["field"]: row for row in changes}
    assert len(by_field) == len(changes)
    for wanted in expected["policy_changes"]:
        got = by_field[wanted["field"]]
        assert isinstance(got["unit"], str) and got["unit"], "policy unit"
        for key in ("field", "left", "right"):
            assert canonical(got[key]) == canonical(wanted[key]), "policy " + key

def receive_api(compare_reports, packet):
    results = []
    for case in packet["cases"]:
        left = bytes.fromhex(packet["files"][case["left"]]["hex"])
        right = bytes.fromhex(packet["files"][case["right"]]["hex"])
        row = {"name": case["name"], "expected": case["kind"]}
        try:
            got = compare_reports(left, right)
        except (ValueError, TypeError) as error:
            row.update(observed="refuse", error_type=type(error).__name__, error=str(error))
            row["passed"] = case["kind"] == "refuse"
        except Exception as error:
            row.update(observed="unexpected_exception", error_type=type(error).__name__,
                       error=str(error), passed=False)
        else:
            row["observed"] = "accept"
            try:
                assert case["kind"] == "accept", "expected refusal"
                verify_result(got, case["expected"])
            except (AssertionError, KeyError, TypeError, ValueError) as error:
                row.update(passed=False, error_type=type(error).__name__, error=str(error))
            else:
                row.update(passed=True, counts=got["counts"], output_sha256=sha(canonical(got)))
        assert sha(left) == packet["files"][case["left"]]["sha256"]
        assert sha(right) == packet["files"][case["right"]]["sha256"]
        results.append(row)
    return {"case_count": len(results), "passed": all(row["passed"] for row in results), "results": results}

def receive_cli(source, root, packet):
    root.mkdir(parents=True, exist_ok=False)
    fixtures = root / "fixtures"
    fixtures.mkdir()
    for name, row in packet["files"].items():
        (fixtures / name).write_bytes(bytes.fromhex(row["hex"]))
    result = []
    python = sys.executable
    def run(name, left, right, expected=None, *, json_mode=True, output_target=None):
        command = [python, "-B", str(source), str(left), str(right)]
        if json_mode:
            command.append("--json")
        before = {}
        for p in (left, right):
            if p.is_file() and not p.is_symlink():
                before[str(p)] = sha(p.read_bytes())
        started = time.monotonic()
        try:
            proc = subprocess.run(command, stdin=subprocess.DEVNULL,
                                  stdout=output_target if output_target is not None else subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=20, check=False)
        except subprocess.TimeoutExpired:
            row = {"name": name, "passed": False, "error": "timeout", "command": command}
        else:
            stdout = proc.stdout if proc.stdout is not None else b""
            stderr = proc.stderr
            row = {"name": name, "command": command, "exit": proc.returncode,
                   "stdout_bytes": len(stdout), "stdout_sha256": sha(stdout),
                   "stderr_bytes": len(stderr), "stderr": stderr.decode("utf-8", "replace"),
                   "elapsed_seconds": time.monotonic() - started}
            (root / (name + ".stdout")).write_bytes(stdout)
            (root / (name + ".stderr")).write_bytes(stderr)
            try:
                if expected is None:
                    assert proc.returncode == 2, "refusal exit"
                    if output_target is None:
                        assert stdout == b"", "refusal emitted stdout"
                else:
                    assert proc.returncode == 0, "success exit"
                    assert stderr == b"", "success stderr"
                    if json_mode:
                        parsed = json.loads(stdout)
                        verify_result(parsed, expected)
                        assert parsed["sources"] == {"left": str(left), "right": str(right)}, "source paths"
                    else:
                        assert stdout and b"Traceback" not in stdout
                for name, value in before.items():
                    assert sha(Path(name).read_bytes()) == value, "input changed"
            except (AssertionError, ValueError, TypeError, KeyError) as error:
                row.update(passed=False, error_type=type(error).__name__, error=str(error))
            else:
                row["passed"] = True
        result.append(row)
    for case in packet["cases"]:
        if case["cli"]:
            run(case["name"], fixtures / case["left"], fixtures / case["right"], case.get("expected"))
    five = fixtures / "five.json"
    six = fixtures / "six.json"
    first = next(x for x in packet["cases"] if x["name"] == "tighten_policy_loses_four")["expected"]
    run("text_output", five, six, first, json_mode=False)
    run("missing_input", fixtures / "missing.json", five)
    run("directory_input", fixtures, five)
    link = fixtures / "linked.json"
    link.symlink_to(five)
    run("symlink_input", link, five)
    dangling = fixtures / "dangling.json"
    dangling.symlink_to(fixtures / "absent.json")
    run("dangling_symlink_input", dangling, five)
    fifo = fixtures / "fifo.json"
    os.mkfifo(fifo)
    run("fifo_input", fifo, five)
    large = fixtures / "bad_over_four_mib.json"
    assert large.stat().st_size == 4 * 1024 * 1024 + 1
    if Path("/dev/full").exists():
        with open("/dev/full", "wb", buffering=0) as sink:
            run("output_device_failure", five, six, output_target=sink)
    else:
        result.append({"name": "output_device_failure", "passed": False,
                       "error": "Required Linux /dev/full is unavailable"})
    for name, row in packet["files"].items():
        assert sha((fixtures / name).read_bytes()) == row["sha256"]
    return {"case_count": len(result), "process_count": sum("command" in row for row in result),
            "passed": all(row["passed"] for row in result), "results": result}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    packet = load_packet(args.fixtures)
    source_before = sha(source.read_bytes())
    sys.path.insert(0, str(source.parent))
    spec = importlib.util.spec_from_file_location("reviewed_compare_plans", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # The consumer may admit/construct/hash native objects, but must not plan,
    # screen, apply, or create a native audit event while comparing saved bytes.
    import towerops
    import plan_world
    import advisory_options
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Comparison called native planning, screening or actuation")
    plan_world.review_world = forbidden
    advisory_options.review_advisory_options = forbidden
    towerops.AdvisoryPlanner.plan = forbidden
    towerops.AdvisoryPlanner._maneuver_candidates = forbidden
    towerops.ControlRoom.screen_batch = forbidden
    towerops.ControlRoom.apply = forbidden
    towerops.AuditLog.append = forbidden
    api = receive_api(module.compare_reports, packet)
    cli = receive_cli(source, args.work, packet)
    receipt = {"format": "towerops.independent-comparison-receiving.v1",
               "source_sha256": source_before, "python": sys.version,
               "github_sha": os.environ.get("GITHUB_SHA"),
               "github_run_id": os.environ.get("GITHUB_RUN_ID"),
               "api": api, "cli": cli,
               "source_unchanged": sha(source.read_bytes()) == source_before,
               "passed": api["passed"] and cli["passed"] and sha(source.read_bytes()) == source_before}
    (args.work / "RECEIVING.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0 if receipt["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
