# Read a recorded plan summary

Use this command when you already have the JSON output of `plan_world.py` and
want its recorded status, clock, counts and policy in a compact sheet:

```sh
python -B review_saved_plan.py after.plan.json
python -B review_saved_plan.py after.plan.json --json
```

Python 3.10 or later and the complete repository source are sufficient for this
standard-library command. It does not need the optional agent/provider packages.
It reads the selected saved file and writes stdout; it never invokes the planner
or changes a world. A raw WorldState, browser scenario or decision trace is a
different input format. See [PLAN_WORLD.md](PLAN_WORLD.md) for the producer and
[EDIT_WORLD.md](EDIT_WORLD.md) for the existing synthetic save -> edit -> plan
example.

## What the sheet tells you

The first lines say **Recorded status** and **Recorded review time**. They refer
to the saved report, not to present traffic or the current time. The observation
and review clocks are synthetic seconds; the policy's horizon/sample values use
minutes. The script does not read the wall clock or renew a proposal's validity.

The sheet includes:

- The exact selected report byte length and SHA-256, plus the original-input
  SHA-256 reported inside it. These are different identities.
- Recorded world hash, version, observation time and review time.
- Saved aircraft count and every recorded conflicting aircraft in original
  list order.
- The **recorded candidate count**, separately from the count of saved
  alternative rows. For the retained fictional edit/plan example, those are
  77 and 50 respectively; 77 does not mean 77 alternatives passed screening.
- A count of saved alternative rows for each explicitly named conflicting
  aircraft, including zero, in that same conflict order.
- Every one of the seven recorded policy fields, with explicit units.

Grouping counts only the saved advisory target IDs. It does not assess geometry,
reorder or recommend alternatives, inspect a first choice, project trajectories,
compare separate worlds, or choose anything to apply. A no-conflict report has
an empty conflict/group list. A report with conflicts but no admitted option
still produces a complete sheet, with zero alternative counts.

The summary is intentionally compact: full aircraft kinematics, alternative
bodies, rationales and validity times remain in the original report. Its hash
lets you retain the exact source alongside the sheet. No field is silently
truncated, and the input is never rewritten into a supposedly corrected report.

## Admission and its limits

This reader delegates unchanged to the current `compare_plans._read_report`
and `compare_plans._parse_report` helpers. That selected runtime closure is
`review_saved_plan.py`, `compare_plans.py`, `plan_world.py`,
`advisory_options.py` and `towerops.py`; keep those files from one reviewed
checkout together. The underscore-prefixed helpers are an explicit dependency
of this tool. No new public comparator API or stronger admission guarantee is
introduced.

The existing helper accepts a direct regular UTF-8 JSON file up to 4 MiB and
checks its exact native report fields, bounded numbers, world/advisory body
hashes, explicit synthetic/proposal flags, and status/count consistency. Its
existing refusal of input symlinks and special files is retained. It reconstructs
the native world for internal identity checks but never calls the planner or
screens the saved alternatives again.

Internal consistency is not producer authentication, candidate-menu completeness,
freshness, policy correctness, proof that screening actually happened, or safety
approval. Derived counts count admitted saved rows. The reported candidate count
remains a recorded claim. The input's own original-world hash cannot prove that
an external raw-world file exists or matches without separately receiving it.

The saved alternatives were recorded individually, not as a simultaneous batch.
An individual option may leave other aircraft in conflict. This command selects
and applies nothing. TowerOps is a research simulation, not operational aviation
guidance or an aircraft-control system.

## Keep literal values and identities

Plain text JSON-escapes names and values; `--json` is ASCII-safe JSON whose decoded
values retain any admitted Unicode. Numeric types and signed zero are preserved
in the projected fields. Original JSON whitespace is reflected in the report's
byte identity; the summary is a new rendering, not an exact copy of that JSON.

The JSON result uses `format: towerops.saved-plan-summary.v1`. `recorded` holds
status/world identity/time/candidate/conflict values, `counts` contains the three
derived row counts, `policy` holds all seven values, and
`saved_alternative_counts` holds ordered `{aircraft_id, count}` records. The CLI
adds `source_path` using ordinary `str(Path(argument))`; relative spellings stay
relative and it is not reduced to a basename. The pure API
`summarize_report(raw: bytes)` returns the same projection without that path.

The existing proposed single-plan HTML format in #65/PR71 is separate: it renders
a fresh producer result, not an admitted saved report. This reader neither
depends on nor adopts that detached source or any browser/selector integration.

## Saving a sheet and checking completion

Choose a new output path distinct from the input before using shell redirection:

```sh
python -B review_saved_plan.py after.plan.json > after-summary.txt
python -B review_saved_plan.py after.plan.json --json > after-summary.json
```

Exit **0** means a complete summary was written for an admitted report, including
`no_conflict` and `no_admitted_option`. Exit **2** means a usage, read, admission,
serialization or output refusal. Diagnostics go to stderr. Output failure can
leave partial bytes, and shell redirection can truncate a selected file before
Python runs; inspect completion before accepting a saved sheet. The reader does
not implement a file-output writer or overwrite protection for the shell.

Focused maintained checks:

```sh
python -B -m unittest discover -s tests -p test_review_saved_plan.py -v
```

These exercise literal saved-row grouping/order/zero counts, both empty outcomes,
numeric representation, raw byte identity, no planner/screening calls, plain
limits/policy and CLI file custody. The independent consumer uses the retained
original before/after JSON from the earlier edit/plan workflow; it does not
replay that planner, a browser, a live service or a scientific campaign.
