# Read-only synthetic sector contact report

`sector_report.py` finds when constant-velocity tracks from a saved native
`WorldState` contact one **closed, axis-aligned rectangle** in the same local
Cartesian nautical-mile coordinates as the Airspace Lab radar. It is a bounded
research/viewing tool, not live surveillance, navigation, certified conflict
prediction, or clearance issuance. It does not alter a world or invoke the
planner, approval gate, acknowledgement or actuator.

```sh
python3 sector_report.py world.json --west-nm 0 --east-nm 10 --south-nm 0 --north-nm 10
cat world.json | python3 sector_report.py - --west-nm 0 --east-nm 10 --south-nm 0 --north-nm 10 --horizon-min 8
```

Use a raw WorldState exported from Airspace Lab, not a world-plan report. File
reads, stdin size limit, duplicate-field admission, valid aircraft and world
version follow the existing `plan_world.parse_world`/bounded reader contract.
Python 3.12+ and no third-party libraries are required.

The sector requires finite JSON numeric edges and `west < east`, `south < north`;
`--horizon-min` is a nonnegative number, default 5. Bounds and horizon must
have absolute value at most 1,000,000,000,000. The rectangle includes its edges.
The horizon is **minutes after** the world's recorded synthetic observation
time (`observed_at` is in synthetic seconds). No live clock is consulted. A
straight track crosses a convex rectangle at most once; exact point contacts
at a corner or horizon endpoint are retained as zero-duration intervals.

On success, a single `towerops.sector-report.v1` JSON object includes native
`world_hash`, `input_sha256` (exact input bytes), world version/observation,
sector/horizon, and `contacts` sorted by entry offset then case-sensitive
callsign. Each contact has `entry_after_min`, `exit_after_min`,
`inside_at_observation` (inclusive boundary) and `contact_only` (zero-duration).
Absent aircraft have no intersection in the chosen horizon and are omitted.

Both offsets describe the intersection of the trajectory's contact interval
with the **requested observation window**, not necessarily the actual first
entry or final exit from the rectangle. Each row additionally reports:
- `entry_window_clipped: true` when the track was already within the
  rectangle *before* observation (the actual ingress precedes offset 0).
- `exit_window_clipped: true` when the track remains within the rectangle
  *past* the requested horizon (the actual egress follows the horizon).

An exact entry on the rectangle edge at offset 0 is *not* entry-clipped; an
exact exit on its edge at the horizon is *not* exit-clipped. A stationary
interior flight has both flags true. A track that first reaches the rectangle
at the final horizon instant can legitimately have `contact_only: true`
**and** `exit_window_clipped: true`: it continues inside *after* the report
ends. These flags do not project beyond the declared straight-line model.
Altitude is intentionally **not** filtered: this is planar occupancy, not a
3D controlled airspace or aviation separation rule. Counts are not risks.

A successful empty list is exit 0. Invalid arguments, unsupported world JSON,
nonregular named files, and write/read errors are exit 2; no report is emitted
on input failure. An output device error may have written partial bytes, so
consumers must check exit status. No files are written by the tool. Slow stdin
has no wall-clock time limit; very small speeds, long horizons and near-boundary
floating-point inputs retain normal finite-precision limitations.

```sh
python3 -m unittest discover -s tests -p test_sector_report.py -v
```
