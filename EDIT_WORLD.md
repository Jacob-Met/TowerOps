# Edit one aircraft in a saved synthetic world

`edit_world.py` changes explicitly selected fields of one existing aircraft and
writes a new raw WorldState file. Use it when you want to author an alternative
coordinate, altitude or velocity without retyping the rest of a scenario.

```bash
python -B edit_world.py before.json --aircraft ALPHA --x-nm 4.5 --altitude-ft 12000 --out after.json
```

Keep `edit_world.py`, `plan_world.py`, `towerops.py` and `advisory_options.py`
together. Their selected path uses Python 3.10+ and the standard library. It does
not need the optional model adapter, browser, server or an installation step.

## Explicit edits and preserved data

The callsign is an exact, case-sensitive ID already present in the input. `A`
and `a` are different aircraft. It is never trimmed, renamed or guessed.
Choose one or more of these flags, each at most once:

| Flag | Native field and units |
| --- | --- |
| `--x-nm` | x position, nautical miles |
| `--y-nm` | y position, nautical miles |
| `--altitude-ft` | altitude, feet |
| `--vx-nm-min` | x velocity, nautical miles per minute |
| `--vy-nm-min` | y velocity, nautical miles per minute |
| `--climb-ft-min` | vertical rate, feet per minute |

Values use JSON number syntax. For a negative rate you can write
`--vx-nm-min=-2.5`. There is no bearing/speed conversion or motion projection.
The complete original file is admitted by the unchanged native `parse_world`
before editing. The same parser admits the complete result before a file is
created; its existing byte, ID, version and finite-number limits remain in force.

Unselected fields, other aircraft, and aircraft array order are preserved as
admitted values. Integers stay integers, floats stay floats and floating signed
zero is retained unless explicitly changed. Source formatting is not preserved:
the output is indented UTF-8 JSON followed by one LF.

The original native `WorldState.replace_aircraft` makes **one version increment**.
The editor passes the **original `observed_at` unchanged**. It never consults a
clock or declares the source newly observed. A source version that cannot be
incremented within the original admission limit refuses.

An unchanged edit refuses. Equality here is the native canonical JSON
representation, which also underlies world identity: `1` and `1.0`, or `-0.0`
and `0.0`, are distinct representations. Different input spellings that parse to
the same representation are equivalent. These distinctions do not establish a
physical difference or an improvement.

## New-file output

`--out` is required and its parent directory must already exist. The command
refuses an existing entry, including a previously saved result. It does not
overwrite the source, create parent directories, select defaults, scan folders
or read stdin. A literal filename `-` is just a filename.

The complete result is prepared before exclusive creation. Successful creation
prints one JSON receipt with format `towerops.world-edit-created.v1`:

- `source` and `output` contain the literal supplied path, byte length and SHA256
  for the original and new file respectively.
- `aircraft_id` is the selected ID; `changed_fields` lists actual representation
  changes in native order: x, y, altitude, x velocity, y velocity, climb.
- `source_version`, `version`, and `observed_at` identify the authored revision
  and the retained observation time.

Exit **0** means the new world and receipt were delivered. Exit **2** means an
argument, input, edit, file or console-delivery refusal/failure. If receipt
delivery fails after publication, the saved world remains, and a usable stderr
identifies that stage. A write failure can leave a partial new file: inspect it
before choosing another output path. No retry or automatic deletion occurs.
This is not a multi-file transaction or a concurrency protocol.

## Python API

```python
from edit_world import edit_world

with open("before.json", "rb") as stream:
    before = stream.read()
after = edit_world(before, "ALPHA", {"x_nm": 4.5, "altitude_ft": 12000})
# after is fully admitted raw WorldState UTF-8 bytes; this call writes no file.
```

The input must be bytes and the edit mapping a nonempty ordinary dictionary of
the six numeric fields. Expected refusals raise `ValueError` or `TypeError`.
Neither the input nor the supplied mapping is mutated. The CLI supplies the
existing bounded regular-file reader; API callers choose how to acquire bytes.

## Meaning of the result

This creates a **synthetic authored counterfactual**. Native admission only
establishes the supported data envelope; it does not run separation geometry,
check policy speed/climb limits, plan a maneuver, approve an advisory or actuate
anything. There is no contact with live aircraft or an external service.

Old world-bound plans, approvals, acknowledgements and traces do not describe
the new world. The retained observation time is not a freshness renewal. Any
later consumer performs its own explicit review. Existing composition, rotation,
selection, CSV and browser-edit tools remain separate and unchanged.

## Review the authored alternative with the original planner

The saved edit is a raw WorldState, which the existing offline `plan_world.py`
command accepts. It is not a Synthetic Explorer replay export or a complete
Airspace scenario. Keep the original and edited files separate, and review each
explicitly with Python 3.12+:

```bash
python -B plan_world.py before.json --now 1234.5
python -B plan_world.py after.json --now 1234.5
```

Both commands read one selected file and print a `towerops.world-plan.v1` report.
They do not edit either world or apply an advisory. Choose the synthetic review
clock deliberately: this example uses the saved observation time. The report's
`reviewed_at` and `observed_at` are seconds; the policy's projection horizon and
aircraft velocity calculations use minutes. Neither command reads a wall clock.
See [PLAN_WORLD.md](PLAN_WORLD.md) for policy, freshness and proposal semantics.
If redirecting stdout, choose a distinct new report filename; the shell controls
redirection and may overwrite its destination before Python starts.

### Worked three-aircraft example

The [received source/example kit and handoff](https://github.com/Jacob-Met/TowerOps/issues/136#issuecomment-6158356595)
contains the exact original and edited files used here. The original has ordered
aircraft ZULU7, ALPHA2 and MID9, version 17 and `observed_at=1234.5`. The edit of
MID9 changes x from -5.5 to -2.25 nautical miles, x velocity from -1 to 3.0 nautical
miles/minute and climb from 50.0 to -125 feet/minute. It preserves the other values,
increments the version to 18 and retains the observation time.

Two actual calls of the unchanged planner, each with `--now 1234.5` and the
original default policy, produced:

| Recorded field | Before | After |
| --- | --- | --- |
| CLI exit | 0 | 0 |
| `status` | `no_conflict` | `options_available` |
| `conflicting_aircraft` | empty | MID9, ZULU7 |
| `candidate_count` | 0 | 77 |
| admitted alternatives in `advisories` | 0 | 50 |
| world version | 17 | 18 |
| `reviewed_at` / `observed_at` | 1234.5 / 1234.5 | 1234.5 / 1234.5 |

At 3.75 projected minutes in the edited world, MID9 and ZULU7 have the same
horizontal position (9,4) and a 531.25-foot vertical gap. Under the recorded
five-nautical-mile/1000-foot/five-minute policy this is a predicted conflict in
this fictional model. ALPHA2 is not in the reported conflict set. The edit is
therefore not described as an improvement merely because its data is valid.

The 77 count is the enumerated candidate menu, not 77 admitted alternatives.
The 50 returned proposals are individually screened alternatives, not a batch.
The first is for ZULU7, even though MID9 was edited: the original planner visits
conflicting aircraft in descending identifier order. Its unchanged priority is
not an instruction to select that proposal. No approval, acknowledgement,
actuation or resolution of the world occurred.

The complete reports retain exact input hashes, native world hashes, policy,
review time and proposal bodies. The planner's embedded `world` uses native
identifier sorting, whereas the edited raw file retains source-array order.
Use `input_sha256` to identify the exact file bytes; the two worlds and their
world-bound reports are distinct. The original receiving reused the already
saved 392-byte source and 608-byte editor result, preserved their bytes, and ran
only those two ordinary planner calls. It is a worked synthetic workflow, not
a new planner validation campaign or an operational aviation recommendation.
