# Read-only synthetic sector occupancy timeline

A saved `towerops.sector-report.v1` contains one interval per track. This separate
consumer answers when reported tracks **overlap in one synthetic rectangular
sector**, without recomputing geometry or changing the native planner:

```sh
python3 sector_report.py world.json --west-nm 0 --east-nm 10 --south-nm 0 --north-nm 10 > contacts.json
python3 sector_occupancy.py contacts.json > occupancy.json
python3 sector_occupancy.py contacts.json --format html > occupancy.html
```

Open `occupancy.html` locally in a browser for a portable, responsive, script-free
timeline. The producer already determines contact from the real native
`WorldState`; this consumer admits saved report bytes and builds an interval
sweep, including tracked occupancy windows, an exact-boundary event register,
peak concurrent counts and per-track bars or point-contact dots. It does not
call the native planner, evaluate aviation separation, create advisories,
authorize flights, or touch any input.

## Important distinction

Sector contacts are **closed** intervals. Two different tracks that meet at
minute 3 are simultaneously present at that exact *instant* even if one exits
and the other enters, but they need not overlap over any positive-duration
period. A tangent contact can have zero duration. Therefore the output exposes
**two explicitly different metrics**:

- `peak_open_interval_count` and `peak_open_windows`: busiest strictly-between-
  event intervals, ignoring contacts only at a point; each window lists exactly
  the aircraft occupying its entire positive-duration interior.
- `peak_instantaneous_count` and `peak_instantaneous_times_min`: busiest exact
  event instants, counting boundary exits, entries, and zero-duration touches.

`segments` lists all positive-duration windows, including idle periods;
`boundary_events` lists all distinct endpoints plus 0 and the horizon, with
callsign IDs, each sorted case-sensitively. A zero-minute horizon legitimately
has **no** positive-duration segments. `contact_only_count` counts saved
zero-duration contacts. The HTML is a visual view of the same admitted report;
it does not recalculate native contact trajectories.

The emitted `source_sector_report_sha256` identifies the exact saved-report
bytes; `source_world_input_sha256` and `source_world_hash` **repeat unverified
claims** from that saved report. `source_verified: false` is intentional. This
is NOT producer authentication or an operational assessment. All times are
minutes after the source world’s synthetic `observed_at`, not wall-clock time.
Altitude is not filtered by the planar sector. Inputs are synthetic only.

## Admission, limits and failures

- One UTF-8 JSON file or `-` for stdin, maximum **262,144 bytes**, maximum **60**
  unique callsigns (1–10 ASCII letters/digits/underscore/hyphen). Named inputs
  must resolve to regular files; symlinks to regular files are allowed.
- Reject duplicate JSON keys, nonfinite numbers, booleans in numeric fields,
  malformed SHA-256 identifiers, inconsistent `contact_count`, intervals outside
  `[0,horizon_min]`, contradictory `contact_only` / clipped-window flags,
  missing native report fields, and invalid rectangle/clock/version metadata.
  Unknown outer metadata is ignored for forward compatibility.
- Success writes one complete JSON or HTML document to **stdout** and returns
  0. Admission/read/output errors return 2; no stdout is emitted on input
  errors. An output-stream failure can leave partial bytes in a caller-managed
  redirect; check exit status. The consumer itself never creates or overwrites
  a path and does not access the network.
- Output is deterministic for identical input bytes. Intervals use the native
  producer’s finite-precision endpoints without inferred interpolation between
  additional trajectories. No scientific uncertainty bounds are implied.

Check locally from the repository root:

```sh
python3 -m unittest discover -s tests -p test_sector_occupancy.py -v
python3 -m ruff check sector_occupancy.py tests/test_sector_occupancy.py
```

The tests include seeded independent interval baselines and an actual native
`sector_report.py` -> occupancy acceptance course when run in the real repo.
The latter is explicitly skipped in an isolated runner without that producer.
