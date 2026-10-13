# Reuse a saved Explorer world

`explorer_world.py` connects the complete saved synthetic Explorer result to the existing raw-world consumers. Choose either its **before** or **after** world explicitly; the command emits only the native `version`, `observed_at` and `aircraft` object.

From the TowerOps source directory:

```bash
python3 explorer.py run approved > approved-explorer.json
python3 explorer_world.py approved-explorer.json --phase before
python3 explorer_world.py approved-explorer.json --phase after
```

The input file stays unchanged. To review the selected world through the existing planner, use a shell that reports upstream pipeline errors:

```bash
set -o pipefail
python3 explorer_world.py approved-explorer.json --phase before | python3 plan_world.py -
python3 explorer_world.py approved-explorer.json --phase after | python3 plan_world.py -
```

At the qualified source, the approved fixture's before world produces `options_available`; its after world produces `no_conflict`. Those are synthetic planner results. The planner continues to emit `proposal_only: true`.

For an entirely streamed fixture:

```bash
set -o pipefail
python3 explorer.py run approved | python3 explorer_world.py - --phase before | python3 plan_world.py -
```

The emitted raw JSON can also be pasted into the existing Airspace Lab raw-world draft. That browser path is an existing compatible format; this change's retained receiving evidence exercises the native planner path.

## Admission and refusal

Both file and standard-input reads are bounded to 262,144 bytes. Paths must resolve to regular files; ordinary file symlinks are supported. UTF-8 JSON is required. Duplicate fields and non-finite constants are rejected.

Before returning either world, the command calls the unchanged `scenarios.replay_result` and requires the **complete** export to match its deterministic fixture replay. Changes to the other world, audit events, labels or extra fields also refuse extraction. The native comparison accepts equivalent finite integer/float JSON representations, while retaining its existing type and field-presence checks. The selected world then passes through the unchanged `plan_world.parse_world` admission boundary.

The output preserves the selected decoded numeric forms and aircraft order. JSON whitespace is reformatted. It contains no additional provenance fields, so it remains directly acceptable to native raw-world consumers. Keep the complete export alongside an extracted world if its scenario and audit context matter.

| Exit | Meaning |
| --- | --- |
| 0 | The selected raw world was written and standard output flushed. |
| 1 | A supported saved fixture result differed from complete native replay. |
| 2 | Arguments, input, admission or output failed. |

A refusal during arguments, reading, replay or admission emits no raw world. An output failure can occur after some bytes were accepted by the destination; consumers should check the pipeline's exit status. Output errors are reported before normal interpreter shutdown.

## Python use

```python
from pathlib import Path
from explorer_world import extract_world

saved = Path("approved-explorer.json").read_bytes()
before = extract_world(saved, "before")
after = extract_world(saved, "after")
```

The API accepts bytes and an explicit phase. Each call decodes a new object graph; changing one returned world does not change the saved bytes or another call's result. CLI file and stream reads are bounded before decoding; callers using the API are responsible for how they obtain their input bytes.

## Scope

This is a connector for saved fixed-fixture Explorer results. Native replay recomputes the local fixture, including its modeled transition for approved scenarios. It establishes local reproducibility, not authenticity, a signature or approval authority. It does not operate a live service or receive live traffic.

The connector introduces no policy, geometry, state transition, browser or existing-consumer changes. Raw-world inputs that did not come from an Explorer result continue to use the existing raw-world commands directly.

## Qualification

Run the focused consumer tests from the source directory:

```bash
python3 -B tests/test_explorer_world.py
python3 -B -O tests/test_explorer_world.py
```

The retained ThinkPad receiving uses Python 3.14.4 and base TowerOps commit `1ce5a91431dce0ca43813ba3198e602f4ae218f5`. Seven test methods pass in each mode, including 64 scenario/approval/acknowledgement/phase combinations, both file and standard-input handoffs, unselected-world and audit tampering, integer/float equivalence, the exact byte limit, detached results and an actual `/dev/full` output failure. The last control is skipped on hosts without that POSIX device. All five required existing source modules were hashed before and after receiving and remained unchanged.

The baseline receipt first records the original complete-export format refusal and the successful manually selected raw-world control. The candidate receipt and saved consumer outputs record the new command's consequence. These are deterministic local fixture checks, not external or operational adoption.
