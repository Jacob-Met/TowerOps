# Author synthetic traffic in CSV

Use a spreadsheet or text editor to prepare multiple aircraft, then convert them
to the existing raw WorldState JSON without editing a JSON array by hand:

```sh
python3 world_from_csv.py examples/traffic.csv --observed-at 1000 > world.json
python3 plan_world.py world.json
# Or pass the complete converted world directly to the existing planner:
python3 world_from_csv.py examples/traffic.csv --observed-at 1000 | python3 plan_world.py -
```

Open `world.json` as text and paste it into Airspace Lab's existing raw WorldState
editor, then use its ordinary Load workflow. This command produces a raw world,
not a complete saved scenario: policy, clock, selection, proposals, approvals and
audit history are not included. Loading and planning retain their existing
behavior. The example is synthetic research traffic, not operational aviation
data or safety assurance.

The output goes to stdout only. The command never edits its input or creates a
file itself. Shell redirection can overwrite a destination, so choose a new
output name and never redirect onto the input CSV. Diagnostics go to stderr;
admission or output failures return exit 2. A failed input produces no JSON on
stdout. A broken output pipe can have received a prefix before the write fails;
no completed delivery is claimed in that case.

## Columns and values

Use a comma-delimited UTF-8 file; a leading UTF-8 BOM is accepted. The header must
contain each exact name below once, in any order. Fields may use ordinary CSV
quoting, and line endings may be LF or CRLF. Missing, repeated or unknown columns,
extra/missing cells, blank records and malformed quoting are refused. A header
with no following records explicitly creates an empty world.

| Column | Meaning |
| --- | --- |
| `aircraft_id` | Native identity: 1–10 ASCII letters, digits, `_` or `-`; unique and case-sensitive |
| `x_nm` | Horizontal x position, nautical miles |
| `y_nm` | Horizontal y position, nautical miles |
| `altitude_ft` | Altitude, feet |
| `vx_nm_min` | Horizontal x velocity, nautical miles per minute |
| `vy_nm_min` | Horizontal y velocity, nautical miles per minute |
| `climb_ft_min` | Vertical velocity, feet per minute |

No latitude/longitude, heading, knots or altitude/flight-level conversion is
inferred. Enter every kinematic field explicitly, including zero. Numeric cells
use JSON number syntax and interpretation (including decimal/exponent notation
and surrounding whitespace). Empty cells, formulas, comma-grouped numbers,
quoted JSON strings, booleans and nonfinite numbers are refused. IDs and header
names are not trimmed, case-folded or guessed.

`--observed-at` is required and supplies synthetic observation seconds. It is not
read from the wall clock. `--version` defaults to integer 0; if supplied, it must
be a native nonnegative JSON integer no greater than 9007199254740991. Use `7`,
not `7.0`, for a revision. Both arguments are passed through the same native
WorldState admission as JSON input.

Every row is read before output. The existing `plan_world.parse_world` validates
the complete world, including finite kinematics with absolute value at most
10^12, unique IDs and at most 60 aircraft. The CSV shares the native 262,144-byte
input limit. Python's ordinary JSON integer/float representation is retained:
integer cells stay integers, `-0.0` stays a signed floating zero, and decimal
floats have the same binary approximation as the JSON consumer. Original text
spellings and spreadsheet formatting are not archived. Native serialization
orders aircraft by exact ID. Reordering valid CSV rows or columns therefore
produces the same world and native hash when the parsed values and their native
integer/float representations match. For example, `1` and `1.0` remain distinct
representations in the native serialized hash even though they compare equal.

Admission does not assert separation or a permissible maneuver. The unchanged
planner applies its own policy after conversion, and its output remains only a
set of individually screened proposals. See [PLAN_WORLD.md](PLAN_WORLD.md).

## Check locally

```sh
python3 -m unittest discover -s tests -p test_world_from_csv.py -v
```

The focused suite uses actual converter/planner child processes and synthetic
CSV. It needs only Python's standard library. The normal repository pytest suite
also discovers these checks.
