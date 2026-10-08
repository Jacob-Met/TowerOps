# Playback compatibility with the current native audit module

The unchanged frozen independent playback driver passes **10 of 10 controls** with the current native audit dependency. All eight source pins remain unchanged before and after this run. The original 39-file qualification packet and its historical results remain byte-for-byte intact.

## Exact composition

The parent-received native source observation identifies commit `5ae808749c8624d9e267d23997beaa3ae5220dbc`, tree `356e66716c8953a3c2aac8a23790ce6eeaba20d0`. All seven non-main files in this eight-file source closure match that tree's exact Git blobs. `src/main.ts` retains the reviewed private playback overlay, SHA256 `c5867cb7c293eb3f5f104b5f3a0e5d2c94a5b8bb42be833bd2f7df42085ac312`; the corresponding upstream main blob remains `2aabfdba1292f6db0890b2fb0b9bc8cf9e027636`.

The executed dependency change is `src/audit.ts`: former SHA256 `a3ec4bb0c29fcfa52475ab50772b44fc17746722ad9c7ac9d94ea2908705d787`, current SHA256 `80ba5c956cffa3ede818fc0eb3ed8e694962b9b2493f14062e09ac1c1e58e075`, current Git blob `abb707db69d866ff762f8bc2c40fde81fc3b7d3b`. The candidate main, core, world-tools, HTML and reference inputs are unchanged.

The dependency adds retained Python canonical audit bodies and checks their correspondence with displayed event bodies. The playback paths reviewed here create an empty unreceived `AuditLog` and call its actual native `verify()` during rendering. That empty-log behavior remains compatible. The received Python audit-preimage path and nonempty audit append/verification behavior remain with their native owner; this replay does not qualify them.

## Evidence and limits

[report.json](report.json) contains the ten full observations, source hashes and transformed-code digests. [verification.json](verification.json) pins the report, log, driver and source manifest and records preservation of the entire prior packet. [current-tree-observation.json](current-tree-observation.json) retains the relevant exact entry subset from the parent's received tree. [source-manifest.json](source-manifest.json) pins the complete local receiving closure.

The frozen driver is SHA256 `7803c72ba02684290b8bd93fb2ee7c2052a1201b222d8a28d59c11c47f3c501b`. Its same ten controls cover native rate progression, manual pause/resume, Reset from 3x paused and 0.5x running, automatic pauses, planner pending/rejection, and early refusal paths. No cases or assertions were added for this compatibility run.

This remains Node v24.19.0 syntax-stripped exact-module receiving with the previously documented small DOM, drawing and Python-promise boundaries. It is not native Vitest, real-browser, Vite build, Pyodide, gate/apply or deployed qualification. The older native audit results, including the separate failed-load supplement, remain historical in the sibling directory; they are not relabeled as this current dependency run.

## Replay

From this directory, use the unchanged driver in its parent and the included eight-file candidate closure. Choose a fresh output file to preserve the recorded result:

```sh
node --experimental-vm-modules ../review_playback.mjs --app candidate --pins source-manifest.json --label replay-current-native-5ae8087 --report replay-report.json
```

The preserved run exits 0. [raw.log](raw.log) retains the ten passing control lines and Node's experimental warnings. Author paths in source provenance are descriptive; replay requires only these relative captured files and the unchanged parent driver.
