# TowerOps presentation pack

Additive, docs-and-assets only. Built from `togishi/synthetic-explorer` @ `da998e4`. **Not recorded, posted or submitted anywhere.** Research simulation only.

| File | What |
|---|---|
| `demo-script.md` | 3-minute script: timed on-screen actions + narration, do/don't-say list |
| `shot-list.md` | 12 shots with source, must-be-visible text, and the check that backs each |
| `captions.srt` | Captions (generated, same timings as the script) |
| `devpost-description.md` | Devpost-style write-up with limits |
| `architecture.svg`, `assets/architecture.png` | Architecture diagram (1600x940) |
| `assets/ui-*.png` | Reference frames from the real explorer (desktop 1280 and mobile 390; approved, missing_ack, late_ack) |
| `claims-map.md` | Every claim → file / test; untested items marked "code only" |
| `build_pack.py`, `build_assets.py`, `check_claims.py` | Regenerate captions+timing, PNGs/screenshots; verify the claims map |

Regenerate: `python presentation/build_pack.py` (stdlib) · `python presentation/build_assets.py` (needs playwright+chromium) · `python presentation/check_claims.py`.
