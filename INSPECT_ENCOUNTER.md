# Explain a saved encounter from the terminal

A saved pair can cross both separation thresholds at different times without
creating a native conflict. Inspect those intervals directly, without running
the planner or opening Airspace Lab:

```sh
python3 inspect_encounter.py world.json EAST WEST --at-min 1.5
cat world.json | python3 inspect_encounter.py - EAST WEST --horizon-min 4
```

The command reads the same raw synthetic WorldState accepted by
[plan_world.py](PLAN_WORLD.md). Aircraft IDs are exact and case-sensitive; select
two different IDs present in that saved world. It requires Python 3.12+ and only
the standard library. Run it from a complete repository checkout so the adjacent
native modules are available.

This is an offline constant-rate forecast for the research simulator. It does
not plan a maneuver, screen or approve a proposal, actuate a flight, update the
world, or establish operational aviation safety. The existing browser encounter
explorer, planner and policy functions remain unchanged.

## Inspect the cause, then a particular instant

For example, let A remain at x=0 NM, y=0 NM, altitude=10,000 FT. Let B start at
x=6 NM, y=0 NM, altitude=12,000 FT, move at vx=-4 NM/min, and descend at
1,000 FT/min. With the default 5 NM/1,000 FT envelope and five-minute horizon:

- Horizontal separation is below its threshold between 0.25 and 2.75 minutes.
- Vertical separation is below its threshold between 1 and 3 minutes.
- The intervals overlap between 1 and 2.75 minutes, so the native pair conflicts.
- At the requested 1.5-minute cursor, separation is 0 NM and 500 FT.

If B instead starts at 14,000 FT, the vertical interval is 3–5 minutes. Both
thresholds are crossed within the horizon, but their intervals do not overlap.
The native pair does not conflict. The cursor still reports each separation
independently; a clear cursor does not imply a clear whole horizon.

All times in this report are **minutes after the saved observation**. They are
not wall-clock timestamps. The saved `observed_at` and revision remain intact.
There is no freshness gate because this is historical geometry inspection,
not proposal admission. Changing `--at-min` neither advances traffic nor
refreshes a saved observation.

## Choose the pair, cursor and envelope

| Argument | Meaning | Default |
| --- | --- | --- |
| `world` | Raw WorldState JSON path; `-` reads stdin | Required |
| `first`, `second` | Exact different aircraft IDs in the saved world | Required |
| `--at-min` | Cursor offset in minutes, from zero through the horizon inclusive | 0 |
| `--horizontal-nm` | Horizontal separation minimum in nautical miles | 5 |
| `--vertical-ft` | Vertical separation minimum in feet | 1,000 |
| `--horizon-min` | Projection horizon in minutes | 5 |

Numeric flags use JSON numeric syntax. Boolean, string, null and non-finite
values are refused. The existing raw-world and numerical envelope is reused:
262,144 input bytes, at most 60 aircraft, numeric absolute values at most
1,000,000,000,000, and policy fields at least 0.000001. See
[the native input contract](PLAN_WORLD.md#input-envelope-and-refusal-behavior)
for complete identifier, version, field and duplicate-key rules. An empty or
single-flight world cannot supply the two selected IDs.

The Python API is:

```python
from inspect_encounter import inspect_encounter

report = inspect_encounter(raw_bytes, "EAST", "WEST", at_min=1.5)
```

A caller may supply `policy=SafetyPolicy(...)`; `None` selects native defaults.
All seven actual policy fields are recorded. Only the horizontal/vertical
minimum and horizon determine this pair forecast. Speed, climb and freshness
limits are not used to approve, reject or change the saved motion here.

## Read the complete report

Success writes one `towerops.encounter.v1` JSON object. The selected pair order
is retained, while the embedded world uses the native identifier ordering.

| Field | Meaning |
| --- | --- |
| `input_sha256` | Exact input bytes, including whitespace |
| `world`, `world_hash` | Complete admitted native world and its native identity |
| `policy` | Complete actual native policy |
| `aircraft_a`, `aircraft_b` | Exact selected identifiers, in caller order |
| `horizontal_window_min` | Native horizontal interval, or null |
| `vertical_window_min` | Native vertical interval, or null |
| `overlap_window_min` | Positive-duration intersection, or null |
| `native_pair_conflict` | The unchanged native pair predicate for the whole horizon |
| `closest_horizontal` | Earliest horizontal minimum within the horizon, with both separations there |
| `cursor` | Both separations and strict-threshold booleans at `--at-min` |

Each point records `minutes`, `horizontal_nm`, `vertical_ft`,
`horizontal_below`, `vertical_below` and `simultaneous`. The closest-horizontal
point is not a minimum of combined 3D separation, a collision prediction, or a
recommended maneuver. For stationary relative horizontal motion, its time is
zero; for a minimum beyond the horizon, it is clipped to the relevant endpoint.

Analytical windows call the existing native policy helpers, not a sampled
approximation. Each non-null window gives its two clipped bounds as a JSON
array. A threshold crossing itself is excluded because the native rule is
strictly **below**, not equal to, the minimum. A bound clipped to zero or the
horizon may already be below its threshold. Use the point booleans for exact
endpoint classification. Tangency and two windows that only touch do not
create a positive-duration overlap.

The native model uses ordinary floating-point arithmetic. This command reuses
that model and its documented numerical input envelope; it does not claim
exhaustive numerical accuracy or replace the safety policy. Relative motion is
used for point measurements, following the existing browser encounter consumer,
so common translation does not erase a small separation.

## Files and automation

The input is never written. No fallback file, browser, server, network call or
decision trace is created. Save the report with ordinary shell redirection to
a **different** path from the input:

```sh
python3 inspect_encounter.py world.json EAST WEST --at-min 1.5 > encounter.json
```

Exit 0 means a complete report, whether the pair conflicts or not; `--help`
also exits 0. Exit 2 means invalid arguments/input, unavailable selected IDs,
unreadable files or output failure. Read/admission failures produce no stdout
report. A failed output device can leave partial bytes, so check the exit code
before consuming redirected output.

## Receiving

```sh
python3 -m unittest discover -s tests -p test_inspect_encounter.py -v
```

The native tests exercise known simultaneous/disjoint intervals, strict
thresholds and tangency, touching windows, horizon clipping, stationary and
diverging motion, exact selected identity/order, input and policy provenance,
cursor refusal, file/stdin equivalence and output failure. A direct control
refuses any planner/menu/ControlRoom call during inspection. Existing native
planner and browser suites remain their own receiving gates.
