# Inspect a saved world with the native planner

`plan_world.py` reviews a raw synthetic `WorldState` JSON file through the existing
Python planner menu and deterministic screening gate. It returns every individually
admitted alternative in the original order, with the exact native proposal bodies
and hashes. It requires Python 3.12+ and no third-party package.

This is a proposal review for the research simulator. It does not apply a maneuver,
create approval/readback fixtures, or establish operational aviation safety.

## Review your own traffic

Save the raw JSON from Airspace Lab's **Inspect or load a WorldState** editor as
`world.json`, then run from the repository root:

```sh
python3 plan_world.py world.json
python3 plan_world.py world.json > review.json
```

The command reads the file without changing it. It does not start a browser or
server. The input is the raw world object, not a scenario file, fixed-explorer
export, decision trace, or previously generated planning report.

For a small custom example, save this as `world.json`:

```json
{
  "version": 7,
  "observed_at": 120.0,
  "aircraft": [
    {
      "aircraft_id": "EAST",
      "x_nm": -8.0,
      "y_nm": 1.0,
      "altitude_ft": 12000.0,
      "vx_nm_min": 2.0,
      "vy_nm_min": 0.0,
      "climb_ft_min": 0.0
    },
    {
      "aircraft_id": "WEST",
      "x_nm": 8.0,
      "y_nm": 1.0,
      "altitude_ft": 12000.0,
      "vx_nm_min": -2.0,
      "vy_nm_min": 0.0,
      "climb_ft_min": 0.0
    }
  ]
}
```

Standard input is also supported. A dash selects stdin; `./-` names a file whose
literal name is a dash. In a POSIX shell:

```sh
cat world.json | python3 plan_world.py -
```

## Choose the synthetic clock and policy

By default, review time equals the world's `observed_at`. This deliberately
reviews the saved snapshot at its own synthetic observation time; it does not
compare that historical number with the machine's wall clock or update it.

Use `--now` to exercise the unchanged native freshness gate at another synthetic
time. The default maximum state age remains ten seconds. A future observation or
a state more than ten seconds old is refused even when no conflict exists.

```sh
python3 plan_world.py world.json --now 125
python3 plan_world.py world.json --horizontal-nm 3 --vertical-ft 800 --horizon-min 4
```

Raw world JSON has no policy settings. The command uses native defaults unless
you supply these three flags; it does not recover settings from a browser session.
The report always records all seven actual policy fields:

| CLI setting | Native field | Default |
| --- | --- | ---: |
| `--horizontal-nm` | `min_horizontal_nm` | 5.0 nautical miles |
| `--vertical-ft` | `min_vertical_ft` | 1000.0 feet |
| `--horizon-min` | `horizon_min` | 5.0 minutes |
| Fixed native default | `sample_step_min` | 0.5 minutes |
| Fixed native default | `max_state_age_sec` | 10.0 seconds |
| Fixed native default | `max_speed_nm_min` | 6.0 nautical miles/minute |
| Fixed native default | `max_climb_ft_min` | 3000.0 feet/minute |

Clock and policy arguments use JSON numeric syntax. Booleans, null, strings and
non-finite values are refused. The Python API also exposes
`review_world(raw_bytes, now=None, policy=None)` for a caller-supplied native
`SafetyPolicy`; `None` selects the same default clock or policy.

## Read the result

A successful invocation writes one `towerops.world-plan.v1` JSON document to
stdout. It includes the input byte SHA-256, the decoded world and native world
hash, review time, complete policy, conflicting aircraft, number of candidates
examined, and the complete ordered `advisories` array.

| `status` | Meaning |
| --- | --- |
| `no_conflict` | The native policy finds no conflicting pair in this snapshot and horizon. No candidate is needed. |
| `options_available` | At least one candidate from the existing menu passed individual native screening. |
| `no_admitted_option` | The native policy finds a conflict, but its bounded menu has no individually admitted option. |

The first returned alternative retains the original planner's first-choice
priority. Later entries are alternatives to review, not a simultaneous execution
batch. Resolving a targeted flight's conflicts can leave an unrelated pair in
conflict. An available option therefore does not mean that every world conflict
has been resolved. An empty menu is not repaired by changing aircraft, relaxing
the requested policy, or inventing a maneuver.

Hashes use the original Python objects and serializer. Numeric JSON types,
floating signed zero, and exact identifier case are preserved; no caller should
normalize a returned body and assume that its original hash still applies. The
world in the report uses native identifier sorting. The separate `input_sha256`
identifies the exact bytes, including whitespace, that were read.

Reviewing creates only the existing helper's private screening state. It does
not emit a live decision trace or turn a proposal into approval or readback.
Any later simulated application still belongs to the original `ControlRoom`
screening, freshness, approval and acknowledgement sequence.

## Input envelope and refusal behavior

The CLI accepts at most 262,144 bytes of UTF-8 JSON. A bounded read enforces that
limit for files and stdin. Duplicate JSON fields, malformed text, unsupported
fields and incomplete objects are refused as a whole.

The world must contain exactly `version`, `observed_at` and `aircraft`. Version
must be an integer JSON token from 0 through 9,007,199,254,740,991; booleans and
floating tokens such as `7.0` are not integer tokens. There may be 0–60 aircraft;
an empty native world is a valid no-conflict review. The browser's own input UI
has its separate minimum of one aircraft.

Each aircraft needs exactly the seven fields shown in the example. Identifiers
contain 1–10 ASCII letters, digits, underscores or hyphens. Exact duplicates are
refused by the native `WorldState` constructor. Identifier case is retained, so
`A` and `a` are distinct native identifiers; the browser's input normalization is
not applied by this CLI.

All kinematic fields and clocks must be finite JSON numbers with absolute value
at most 1,000,000,000,000. Policy values must be between 0.000001 and that same
upper bound. This is a numerical input envelope for the new consumer, not a new
physical policy or a claim of exhaustive floating-point accuracy. Values outside
it are refused; they are not clamped, rounded into range or passed to the engine
as a successful review. Native model and library admission behavior are unchanged.

| Exit | Meaning |
| --- | --- |
| 0 | Completed review, including either empty-menu status; `--help` also exits 0. |
| 1 | The unchanged native gate refused the review, with its reason on stderr. |
| 2 | Invalid arguments/input, unsupported numerical domain, unreadable file, or report output failure. |

Read, validation and native-gate failures produce no stdout report. An output
device failure can leave partial bytes, so automation must check the exit code
before accepting output. The command does not write an input or a fallback
report file. Shell redirection is controlled by the caller: choose a different
output path from the input path.

## Receiving

The focused suite runs actual native imports and actual Python subprocesses:

```sh
python3 -m unittest discover -s tests -p test_plan_world.py -v
```

It checks complete native option/body/hash parity, meaningful empty outcomes,
clock/policy behavior, type and resource refusals, exact input retention, file and
stdin equivalence, and output failure. The existing repository Python, lint and
Airspace Lab gates remain the current-composition acceptance path.
