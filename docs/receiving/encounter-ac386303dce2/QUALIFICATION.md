# Author receiving: native saved-pair encounter consumer

Claim: https://github.com/Jacob-Met/TowerOps/issues/77
Base: 2119eac83f97763cfb66f8c29bff506437ba4725; tree bb500f893ee7397b241e453cc51b1c97be071e6f.

The original native saved-world planner successfully reports the authored simultaneous and disjoint controls, but provides no selected-pair window/cursor report. This is a new offline consumer, not a claim that the existing planner is defective. Full original stdout, inputs and source pins are retained in original-planner-receipt.json.gz (decompressed SHA-256 96f696ab3b6fa7f350d23248903b7f78df9b5d4cf9aa6dc33d49e6b403386d0f).

Frozen inspect_encounter.py SHA-256 bb6e5586196f77f6ac7bd994d9d1f07c818ec79f5a6f01845568e6262a491715 (Git blob d8dfd27fbbaade51f5945b7d8aafd827412c0ca1). Frozen new test SHA-256 b61364fe2165ff419c4af615119b42370c85395fb6d34b0c04188a5f5acd4775 (blob 9bd42325539f204feb07244342cf970b0918f251). No source corrections were needed during these author runs.

Actual receiving:
- ThinkPad hamon-thinkpad, Python 3.14.4: new consumer 15/15 methods and existing saved-world planner 22/22 methods, each normal and -O; zero skips.
- Isolated local Linux Python 3.12.14: unchanged new consumer 15/15 methods; zero skips.
- Every source byte was rechecked after execution. Actual CLI file/stdin results match and authored input files are unchanged.
- The native candidate capsule is /home/jacob/towerops-encounter-ac386303dce2-xr9jqwkg; source and initial evidence total 173,415 bytes before this compact publication packet, within its 2 MiB bound. No browser, provider, installation, service or shared-source mutation occurred.

Tests include known analytical windows, disjoint and exactly touching intervals, strict threshold/tangency behavior, horizon clipping, stationary and diverging closest approach, caller order and exact identity, raw-byte/native-hash provenance, invalid cursor/policy/IDs, complete original admission, output failure, and refusal of every planner/menu/ControlRoom call during analysis.

The consumer imports existing raw-world admission and numerical checks from plan_world.py and native analytical functions from towerops.py. None of those dependencies changed. It does not run the planner or native admission/actuation gates. Cursor time is an offset from the saved observation; it is not a freshness check or world update. The closest point minimizes horizontal separation only. Native floating-point and strict-interval semantics are retained, including endpoint clipping disclosed in INSPECT_ENCOUNTER.md.

The archive contains exact source closure, new and retained tests, original native planner before-control, full author outputs, native source/ownership readback and the Python 3.12 receiving result. The full unrelated native coordination record stays in host custody; the scoped intake records its exact digest and this contribution only.

This author receipt is not independent review or hosted CI. Those results must be recorded separately on the actual published composition.
