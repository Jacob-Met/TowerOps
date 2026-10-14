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
