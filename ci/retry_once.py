#!/usr/bin/env python3
"""retry_once.py -- flaky-test detection wrapper for CI.

Runs the test suite once. Every test that FAILS is re-run exactly once in
isolation. A test that passes on retry is recorded as FLAKY -- it is NOT
trusted, and the wrapper exits non-zero so CI stays red until the flake is
triaged and quarantined (see FLAKY.md).

Exit codes:
    0 -- all tests green on the first run (clean)
    1 -- one or more tests failed consistently (real failure; retry also failed)
    2 -- one or more tests passed ONLY on retry (flaky detected; recorded)

Writes a machine-readable report to ci/flaky-report.json (or $FLAKY_REPORT).
No third-party pytest plugins required -- parses pytest's own summary.
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

FAILED_RE = re.compile(r"^FAILED\s+(\S+?)(?:\s+-.*)?$")
ERROR_RE = re.compile(r"^ERROR\s+(\S+?)(?:\s+-.*)?$")
REPORT_PATH = os.environ.get("FLAKY_REPORT", "ci/flaky-report.json")
RETRY_TIMEOUT_S = int(os.environ.get("FLAKY_RETRY_TIMEOUT_S", "300"))


def run_pytest(args, timeout=1200):
    """Run pytest, return (returncode, combined_output)."""
    cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"] + args
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s: {' '.join(cmd)}"


def parse_failures(output):
    """Extract failed/errored node IDs from pytest's short summary."""
    ids = []
    in_summary = False
    for line in output.splitlines():
        if "short test summary info" in line:
            in_summary = True
            continue
        if in_summary:
            m = FAILED_RE.match(line) or ERROR_RE.match(line)
            if m:
                ids.append(m.group(1))
            elif line.strip() and not line.startswith(("FAILED", "ERROR", "PASSED", "SKIPPED", "XFAIL", "XPASS", "WARNING", "ERROR ")):
                # summary section ended (next section header or blank-adjacent)
                if line.startswith("="):
                    break
    # de-dup, preserve order
    seen, ordered = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered


def main():
    started = datetime.now(timezone.utc).isoformat()
    extra_args = sys.argv[1:]

    rc, first_out = run_pytest(["--tb=short", "-q", "-rfE"] + extra_args)
    first_failures = parse_failures(first_out)

    report = {
        "tool": "retry_once.py",
        "started_utc": started,
        "first_run": {
            "exit_code": rc,
            "failed_tests": first_failures,
        },
        "retries": [],
        "verdict": None,
    }

    if rc != 0 and not first_failures:
        # Collection error / infra failure -- nothing sane to retry.
        report["verdict"] = "error"
        write_report(report)
        print("retry_once: first run failed with no attributable test "
              "failures (collection/infra error). NOT retried.")
        print(first_out[-4000:])
        return 1

    if not first_failures:
        report["verdict"] = "green"
        write_report(report)
        print("retry_once: all tests passed on first run. Clean.")
        return 0

    flaky, still_failing = [], []
    for node_id in first_failures:
        rrc, rout = run_pytest(["--tb=short", "-q", node_id],
                               timeout=RETRY_TIMEOUT_S)
        passed = (rrc == 0)
        report["retries"].append({
            "test": node_id,
            "retry_exit_code": rrc,
            "retry_passed": passed,
        })
        (flaky if passed else still_failing).append(node_id)
        tail = "\n".join(rout.splitlines()[-15:])
        print(f"--- retry {'PASS' if passed else 'FAIL'}: {node_id}\n{tail}\n")

    os.makedirs(os.path.dirname(REPORT_PATH) or ".", exist_ok=True)

    if still_failing:
        report["verdict"] = "failed"
        write_report(report)
        print(f"retry_once: {len(still_failing)} test(s) failed consistently "
              f"(real failure, not flaky):")
        for t in still_failing:
            print(f"  FAIL  {t}")
        if flaky:
            print(f"retry_once: additionally {len(flaky)} flaky test(s) "
                  f"(passed only on retry) recorded in {REPORT_PATH}:")
            for t in flaky:
                print(f"  FLAKY {t}")
        return 1

    report["verdict"] = "flaky"
    write_report(report)
    print(f"retry_once: {len(flaky)} test(s) passed ONLY on retry -- "
          f"FLAKY, recorded in {REPORT_PATH}, NOT trusted:")
    for t in flaky:
        print(f"  FLAKY {t}")
    print("Triage per FLAKY.md: open a tracking issue, quarantine with "
          "skip/xfail + issue link, or fix the root cause.")
    return 2


def write_report(report):
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    d = os.path.dirname(REPORT_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = REPORT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(report, f, indent=2)
    os.replace(tmp, REPORT_PATH)


if __name__ == "__main__":
    sys.exit(main())
