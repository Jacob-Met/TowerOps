# Unchanged author receiving after an incomplete native attempt

The unchanged seven-group scenario receiver passes on full source tree `8cd8023a2f676b2faa17d5d5120e3ae3e4fd54f4` and its frozen 16-asset production build. Its fresh native process finished in 13.206 seconds with exit 0, empty stderr, no timeout or wrapper exception, and no app errors or external app requests. All 1,017 source entries (bytes, mode, Git blob) and all 16 build assets match the root source/build pin both before and after.

This is a replay of the existing author predicates. No product, fixture predicate, browser receiver, dependency, or build change was made. The narrow question was whether an earlier incomplete attempt demonstrated a radar or native-planner hang. This replay does not reproduce such a hang; it does not establish the lost attempt's exact failure mechanism.

## Preserved incomplete attempt

The original root wrapper starts author7 before raw-draft4 using `subprocess.run(timeout=300)`. It has no outer exception receipt. Its tool PID was later unavailable, but that is not evidence of a particular exit code, timeout, or crash. The wrapper's stdout contains only the first group's pass at 2,619 ms; stderr is empty and no final browser report exists.

Read-only observation at 2026-10-08T16:12:01Z found no surviving process matching that wrapper, receiver, or profile and no response from the profile's recorded debugging port. Only its first 812-byte stationary-scenario download exists; the fixtures directory is empty. The exact second group opens a new page and saves the default scenario before invoking Run planner, so there is no confirmed second-group native-planner interaction in the surviving output. The profile's empty History database provides no usable page-history evidence. These observations narrow the available evidence, but do not identify a cause. The original directory, profile, source, build and partial output remain unchanged.

The raw archive preserves the original partial stdout, empty stderr, exact wrapper transcript, exact author bytes, first real download, initial observation and executed diagnosis/replay drivers. The new wrapper writes a running receipt before launch and captures completion, exceptions and bounded termination of only its own process group. That receiving change is separate from the unchanged browser predicates.

## Successful replay

The receiver is byte-exact with both existing repository copies:

- `docs/verification/scenario-files-20261008-cf5799f6d38b/composition-pr39-pr42/receivers/author.mjs`
- `docs/verification/scenario-files-20261008-cf5799f6d38b/current/scenario-browser-receiving.mjs`

Receiver SHA256: `3486cd53f70b44ec9d964d45d7e7688f2d3163cfd693af5beb951f583d65aab6`; Git blob: `2f84eac00c90d80f4f0470e43b654eb3a13dedc9`.

The source/build pin SHA256 is `c7a2fd2cee35e79b69fb74a520b15de0b2d697756ea60ac9b2ad68cbd86a2301`, already preserved by the separate playback/radar receiving contribution. Runtime was Node 26.3.0, Puppeteer 25.12.0, and Chrome 154.0.8037.98 on the authorized Mac.

All seven original groups passed: saved policy download/review/import; cancellation and two native Python approval/readback cycles with a fresh trace; changed-context invalidation; cancelled/superseded asynchronous reads; invalid-file preservation; legacy raw-world and selected-flight editing; and literal filename/keyboard/phone layout behavior. Group 2 finished in 2,449 ms. The complete raw receipt pins the genuinely served production worker, Pyodide and `towerops.py` bytes. Both actual downloads completed. The two screenshots were independently inspected: filename text stays literal, the phone review fits its width, and the explicit Load action remains visible.

The receiver serves the unchanged production build through an isolated loopback HTTP server and blocks external network requests with its existing proxy. The asynchronous-file group retains its documented File.text completion control. This is native local receiving, not qualification of the canonical public Pages deployment.

## Reproduction and archive

Run the already published author receiver against the exactly reconstructed source and normal production build:

```sh
NODE_PATH=/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules \
  node docs/verification/scenario-files-20261008-cf5799f6d38b/current/scenario-browser-receiving.mjs \
  EXACT_SOURCE_ROOT NEW_OUTPUT
```

Restore the byte archive using `node restore-receiving.mjs raw-receiving.json.gz NEW_DIRECTORY`. Each member is checked for length, SHA256 and Git blob. Executed Python setup files are archived under explicit `.py.txt` transport names; the archive mapping records their exact original paths and bytes. They are preserved historical drivers, not newly qualified Python modules. No dependency trees, profiles, caches or generated runtime bundles are included. Original and successful receipts retain their own identities.
