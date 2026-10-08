# Maintained PR48 receiving on the scenario composition

The exact maintained `tools/check_advisory_options_browser.py` passed all ten of its predicates on both existing root builds. The independent receiver worker did not check out, rebuild, install, or edit either candidate.

| Existing source tree | Purpose | Maintained predicates | Receiver process |
| --- | --- | --- | --- |
| `f4bc1ce05953dde6a33cea8588033fea9e18c5c4` | Initial PR48/scenario composition | 10/10 | exit 0; 8.63 seconds |
| `74ca2a2c29e09eb3c9d0c8b896eb81afcc418993` | Separate alternatives-reset successor | 10/10 | exit 0; 8.86 seconds |

Both compositions derive from main commit `093f88b29d6e1ede778f967528c7e010b7689ab1`. The initial composition is not an unmodified checkout of that commit. These results do not claim receiving of pure upstream 093f88.

## Exact runtime and receiver

The runs used existing Python 3.12.8, Playwright 1.63.0, and installed Chrome 154.0.8037.98 on macOS 26.6.2 arm64. Python optimization was zero, preserving every assertion.

The maintained receiver is 9,902 bytes, Git blob `9746bd30b3ca2fb2b0a56db45a461c0f2884afaa`, SHA256 `e5862ba28e8e23354eaa635175759e67c5d929ebda871f96d0df116729e3049f`. It was executed directly from each frozen candidate with identical bytes.

For an already-built source tree, the public replay command is:

```sh
/path/to/existing/playwright-python -B /path/to/TowerOps/tools/check_advisory_options_browser.py \
  --chrome "/path/to/installed/Chrome" \
  --output-dir /new/isolated/receiving-output
```

Use normal Python 3.12 or newer with assertions enabled. The maintained tool serves that source tree's existing `web/airspace/dist` on loopback and runs the real browser/Pyodide worker. The build must contain the real `advisory_options.py` source. Its explicit helper-unavailable control substitutes a 503 only for that helper request. No other response or Worker message is replaced.

The ten named predicates cover native first-choice identity; preserved approval/world during review; native ordering, pagination, and flight filtering; authorization reset on selection; exact selected native proposal through the real apply request; audit verification; changed-snapshot invalidation; complete empty review; mobile fit; and the original planner remaining available after the helper fails. Both raw receipts have zero page errors and zero external application requests.

## Source and build custody

Each run records every one of 251 source leaves and 16 build files before and after execution. All recorded bytes and modes match; all expected source and build pins match the root-supplied manifest. The build path set is also unchanged. Raw manifests, process logs, receiver receipts, and screenshots are retained separately for initial and successor runs.

The read-only shared-seam review checked main.ts, README, index.html and the CSS combination. The initial 251 source leaves matched root's pin. The CSS retains the exact PR48 prefix followed by the exact frozen scenario suffix: 1,058 bytes, SHA256 `52eea13c07a42dcf2d1bf55ce922623dad739bec391e3f14b760f83aa75c144c`. Raw-draft ownership, encounter refresh, scenario review context, and guarded audit-verification completion remain present.

The narrow successor changes only `web/airspace/src/main.ts` and `web/airspace/README.md`; all other 249 source leaves match the initial composition. Its exact patch is included. It explicitly clears old alternatives when a reviewed saved scenario is loaded, including a scenario with identical values, and makes the load feedback agree with that behavior.

The maintained receiver does not exercise the new same-value scenario-load lifecycle control. That independent two-case review is owned and recorded separately by the memory receiver worker. Source inspection corroborated its initial finding: equality of state/policy/clock values let an old options review survive a scenario load. Approval was cleared; no old-approval bypass is claimed.

## Preserved receiving observations

An earlier attempt to prepare a separate pure-093f88 baseline shared clone hit ENOSPC while writing the checkout command's output. Its original directory remains frozen; checkout completion, a build, or a browser run was not qualified. The exact exposed failure is retained as `prior-baseline-enospc.txt`. Root then authorized the direct read-only receiving recorded here once capacity recovered. This packet does not turn that incomplete attempt into a passing baseline.

The new outer custody wrapper was executed without changing maintained receiver predicates. A later packaging-only Ruff check reported SIM117 for its nested stdout/stderr contexts and BLE001 for catching and recording subprocess exceptions. Those raw diagnostics remain. The unchanged executed wrapper is archived as `receive_existing.py.txt`, with an explicit original-to-published path, byte count, and SHA256 mapping. This is a historical execution transcript, not a newly qualified Python module or an application lint exemption. Replay uses the maintained repository tool above.

Both maintained browser runs passed on their first attempt. No rerun or receiver correction was required. The final manifest excludes temporary browser profiles, caches, dependency trees, and copied source/build trees. Each declared file has its original bytes, mode, SHA256, and Git blob.
