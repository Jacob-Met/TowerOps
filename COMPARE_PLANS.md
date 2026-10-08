# Compare saved policy experiments

Use `compare_plans.py` to inspect two already saved
`towerops.world-plan.v1` reports from the native [world planner](PLAN_WORLD.md).
The command shows which complete advisory records are present in both menus,
which appear on one side only, and where each record appeared in the original
menu order. It also shows the exact saved policy values that differ.

Both reports must describe the **same exact native world and review clock**.
This makes the tool useful when reviewing policy settings against one frozen
synthetic traffic snapshot. It refuses a changed world or clock instead of
presenting those differences as a policy comparison.

The command reads saved results. It does not run the planner or separation
policy, select a preferred policy, approve a proposal, or apply an advisory.
TowerOps remains a synthetic research simulation, not operational aviation
assurance.

## Run a comparison

Python 3.12 or later and the existing repository modules are sufficient; no
additional package, browser, service or network connection is needed.

Create two reports using the same raw WorldState file. For example:

```sh
python3 plan_world.py world.json > baseline.plan.json
python3 plan_world.py world.json --horizontal-nm 6 > wider-envelope.plan.json
python3 compare_plans.py baseline.plan.json wider-envelope.plan.json
```

The original native planner owns those policy options and their meaning. Use
the same explicit `--now` for both producer calls if you override the saved
world's observation time. The comparison command takes no policy or clock
override.

For complete machine-readable comparison records:

```sh
python3 compare_plans.py baseline.plan.json wider-envelope.plan.json --json
```

All comparison output goes to stdout. The command never opens an output path.
When using shell redirection, choose a separate destination: the shell can
truncate an existing destination before Python runs, including an input file
if you mistakenly reuse its path.

Supply two direct regular files. Read-only files and the same file on both
sides are supported. Directories, symbolic links, FIFOs and other special
files are refused. Inputs are local paths; the command does not fetch URLs or
consume stdin.

## Read the terminal result

The heading identifies the full native world hash and exact saved review
clock. Each side includes its report-file SHA256, the original-input SHA256
reported by its producer, saved status, reported conflicting identities,
candidate count and number of saved alternatives. Changed policy fields and
the other identical policy fields are all shown, with their native units.

A changed policy can leave every advisory record unchanged. Conversely, the
saved `no_conflict` outcome is distinct from `no_admitted_option`:
the latter records a conflict with no admitted alternative in the producer's
bounded menu. The comparison preserves those recorded statuses; it does not
recompute them.

Menu rows use three membership labels:

| Label | Meaning |
|---|---|
| `retained` | The same complete native advisory body and hash occur in both reports. |
| `left_only` | That complete advisory identity occurs only in the left report. |
| `right_only` | That complete advisory identity occurs only in the right report. |

`L1/R4` means the record occupied position 1 on the left and position 4
on the right. Positions are 1-based. A dash means the record was absent on
that side. The left menu is listed in its original order, followed by
right-only records in their original right-side order.

The count of changed ranks describes absolute positions. Removing an earlier
alternative can shift later ranks without reversing their relative order.
The comparison never re-sorts a menu to recommend a maneuver.

Each row retains the exact aircraft identity, velocity and climb setpoints,
full advisory SHA256, issued/expiry times and literal rationale. Numeric
values are not rounded. Text uses JSON-style escapes so newlines, terminal
control characters and distinct Unicode sequences remain inspectable without
being interpreted by a terminal.

These are individually recorded alternatives, never a simultaneous batch.
An available alternative for one target does not establish that all other
flight pairs have been resolved.

## Exact identity and the limits of this inspection

World identity follows the unchanged native `WorldState.to_dict` and hash:
aircraft order is canonicalized by exact identity, while every saved field,
version, numeric type and signed zero is retained. Consequently:

- Reordering JSON object keys, changing whitespace, or reordering the world's
  aircraft array can retain the same native world identity.
- Integer `120` and floating `120.0` are different native clock values for
  this comparison, as are `0.0` and `-0.0`. Equal-looking integer/float or
  signed-zero world changes are also refused.
- Native JSON number spellings that decode to the same type and value may
  have the same native identity. The report-file hash still distinguishes
  their original bytes.
- Exact policy representation differences, such as integer `5` versus float
  `5.0`, remain visible even if their saved menus are identical.
- Advisory matching uses the full native body and hash, including its world,
  times and rationale. Matching only a flight, rounded setpoint or maneuver
  shape would lose information and is not used.

Each report's world hash and every advisory hash are recomputed from its
complete saved body with the existing native hash implementation. Duplicate
advisory identities and inconsistent bodies are rejected. This establishes
internal consistency only. A person who edits a body can also calculate a
new hash.

The consumer does **not** authenticate the producer, possess or rehash the
original WorldState input, prove that both producers used the same source
version, verify menu completeness, or replay the saved safety decision.
Candidate counts and statuses remain reported facts with structural checks,
not independently reproduced planning results. The reported original-input
SHA256 is labeled as such and is separate from the SHA256 calculated over
each actual report file.

The same world and clock are necessary for this comparison; they do not
establish that a policy change alone caused a difference between two
unauthenticated saved outputs. Keep the producer's own source/qualification
evidence when that distinction matters.

Each input is a bounded read of one opened regular file. The two reads are
not a filesystem transaction or a lock against another process modifying a
report. The displayed report hashes bind the bytes actually read.

## JSON output

Successful `--json` output has format `towerops.plan-comparison.v1`.
It includes the complete native world, exact review clock, both policy and
source summaries, policy changes, membership/rank counts and complete
advisory rows. The CLI also includes the two supplied source paths.

`entries` contains every left record in left order, with its optional
right rank, then every right-only record in right order. Each entry has
`membership`, nullable `left_rank` / `right_rank`, and the full original
`advisory` object including its native hash. It does not create a new
advisory or approval identity.

JSON output escapes non-ASCII text without normalizing it. Decoding the JSON
restores the original admitted Unicode and numeric values. Use
`compare_reports(left_bytes, right_bytes)` for the same comparison as a
native Python API; CLI path labels are added only by `main`.

## Refusals and exit status

Both reports are admitted completely before any comparison output is written.
The reader accepts UTF-8 JSON of at most 4 MiB per report. It refuses duplicate
object fields, non-finite/coerced numbers, unsupported or incomplete shapes,
unknown fields, invalid native world/policy domains, inconsistent flags,
statuses, identities or counts, duplicate advisory identities and mismatched
body hashes. The v1 positive policy and finite numeric bounds follow the
existing producer, including the valid expiry at the maximum review clock.

A valid comparison exits **0**, including equal menus, changed menus and
empty recorded outcomes. Read, admission, compatibility, argument or output
failure exits **2**, with a diagnostic on stderr. An input refusal has no
comparison on stdout. An output failure can occur after some bytes reached
the destination; it is reported as failure and is not a transactional output
guarantee.

To correct a world/clock mismatch, return to the original producer inputs and
produce reports for the same snapshot and time. Editing a hash or reported
clock does not turn a different experiment into the same one.

## Maintained receiving tests

From the repository root:

```sh
python3 -B -m unittest discover -s tests -p test_compare_plans.py -v
```

The tests use real native producer outputs and actual CLI processes for file
and output boundaries. They cover policy changes with and without menu
changes, preserved body identities and order, empty outcomes, exact
world/clock refusal, malformed complete inputs, literal text, regular-file
custody and a genuinely closed stdout reader. No live aircraft, model,
provider or existing user file is used.
