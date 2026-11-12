# Read-only proximity ranking for a saved synthetic world

`proximity_report.py` helps a scenario author spot both native conflicts and
**near misses** in an explicitly supplied, complete `WorldState` JSON file.
For each pair, it reports the time of closest *combined normalized proximity*,
actual horizontal and vertical separations at that time, and the separate times
of closest horizontal and vertical approach. A pair can be horizontally close
while vertically far away; its combined score captures both dimensions.

```bash
python3 proximity_report.py saved-world.json > proximity.json
python3 proximity_report.py saved-world.json --horizon-min 10 --limit 40
python3 proximity_report.py - < saved-world.json
```

The input uses the existing strict native `plan_world.parse_world` admission
rules: at most 262,144 bytes, 0–60 uniquely identified synthetic aircraft,
complete finite kinematic fields, no duplicate JSON object keys, and a native
valid world version. No files are created or overwritten. Output goes only to
stdout. Errors go to stderr with exit 2 and no partial JSON output. `--limit`
selects 1–1,770 returned pairs (20 by default). The report retains the total
number of pairs and native conflict count even when rows are truncated. The
horizon is explicit and bounded to 0.000001–120 minutes (default 5).

The pair rows are ordered **native conflicts first**, then by ascending
proximity ratio and exact callsigns. `native_conflict` is computed by the
existing `SafetyPolicy._pair_conflict` algorithm. The diagnostic proximity
ratio is the minimum, over the same constant-velocity horizon, of:

```text
max(horizontal separation / configured horizontal minimum,
    vertical separation / configured vertical minimum)
```

The minimum is approximated by a fixed 96-iteration convex one-dimensional
search with boundaries and individual horizontal/vertical extrema checked.
The ratio is for research visualization and ranking **only**; it never
replaces the native strict-interval safety decision. In particular, a tangent
at ratio 1 does not imply a native conflict. `horizontal_cpa_time_min` and
`vertical_cpa_time_min` are individually optimal times and need not equal the
combined proximity time. Times are offsets in minutes from `observed_at`;
positions use nautical miles, altitudes feet, rates nautical miles/minute and
feet/minute. No numerical convergence or operational assurance is claimed.

The JSON report includes `format: towerops.proximity-report.v1`, the original
input SHA-256, the native canonical world hash and version, observation time,
thresholds, horizon, total/conflict/returned pair counts, and a truncation
flag. It preserves native case-sensitive aircraft IDs and has no actuation,
approval, readback, advisory, network, model, real-aircraft, or live-data path.

## Verify from a complete TowerOps checkout

```bash
python3 -m pytest tests/test_proximity_report.py -q
python3 proximity_report.py - --limit 1 < saved-world.json
```

This is **synthetic research simulation only**, not operational air traffic
control, flight guidance, safety assurance or certification. Do not use it for
actual separation decisions.
