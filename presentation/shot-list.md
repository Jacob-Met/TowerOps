# TowerOps — shot list (3:00)

Screen capture at 1280x900 unless noted. Times match `demo-script.md` and `captions.srt`. Assets: `assets/` (regenerate with `python presentation/build_assets.py`). **Nothing here has been recorded or posted.**

| # | Time | Shot | Source / how to get it | Must be visible | Checked by |
|---|---|---|---|---|---|
| 1 | 0:00-0:14 | Title card: "TowerOps", subtitle "The model proposes. Deterministic code decides." over a dimmed `assets/architecture.png`; bottom strip: "Synthetic research simulation only" | `assets/architecture.png` | Disclaimer strip for the whole shot | claims-map #18, README banner |
| 2 | 0:14-0:34 | Full architecture diagram; slow push-in on the dashed proposal lane, then the teal trust-boundary lane | `assets/architecture.png` / `architecture.svg` | Labels "PROPOSAL SIDE" and "DETERMINISTIC TRUST BOUNDARY" | claims-map #2-#10 |
| 3 | 0:34-0:48 | Explorer, Run on "Approval + acknowledgement" | live `python explorer.py serve --port 8765`; reference frame `assets/ui-desktop-approved.png` | Green "Fixture accepted · simulated actuation only"; "Projected conflict: before true → after false" | `browser_acceptance.py` (approved) |
| 4 | 0:48-1:04 | Drag the projected-time slider 0 → 5 min, before/after SVG plots side by side | same | Two aircraft circles move; dashed projected paths differ only in the After panel | `browser_acceptance.py` (slider, SVG geometry) |
| 5 | 1:04-1:28 | Scroll to Advisory + Audit timeline; hover/zoom the chain-head line | same | Events: fixture_proposal, screen_pass, approval, ack, simulated_actuation; "Local chain valid: True" | `test_all_cases_and_fixture_switches` |
| 6 | 1:28-1:50 | Select "Missing acknowledgement", Run, no reload | reference `assets/ui-desktop-missing_ack.png` | Red "Rejected · no simulated actuation"; "Engine reason: ack_missing"; After title "After rejection · unchanged world"; timeline ends in `reject` | `browser_acceptance.py` (success→missing-ack regression) |
| 7 | 1:50-2:02 | Quick cut through "Late acknowledgement" (reference `assets/ui-desktop-late_ack.png`), then the dropdown open showing all 8 cases | same | `ack_late`; 8 options | `SCENARIOS` |
| 8 | 2:02-2:30 | Export JSON; choose the file under Replay → "Replay MATCH". Open a copy, change `after.version`, replay → "Replay MISMATCH" | real download from UI | The two status lines verbatim; add on-screen note "Reproducibility, not authenticity" | `test_replay_checks_whole_export`; `browser_acceptance.py` |
| 9 | 2:30-2:42 | Terminal: `python -m unittest -q test_explorer` | real run | "Ran 8 tests" and "OK" | the suite itself |
| 10 | 2:42-2:50 | Terminal: JSON summary from `python browser_acceptance.py` (optional; needs playwright) | real run | `"fixture_controls": "passed on both viewports"`, `"page_errors": []` | `browser_acceptance.py` |
| 11 | 2:50-2:56 | Phone-width view (390x844) of the same result | reference `assets/ui-mobile-missing_ack.png` or devtools at 390x844 | No horizontal scroll | `browser_acceptance.py` (`scrollWidth <= innerWidth`) |
| 12 | 2:56-3:00 | Closing card: "TowerOps · synthetic research simulation · fixture identities, no real authority"; repo path | text card | Disclaimer | claims-map #18 |

## Capture notes
- Use the live app for shots 3-9; the PNGs in `assets/` are reference frames and fallbacks, not substitutes for the recording.
- Record the terminal at 120 columns; cut the `Ran 8 tests` line in tight.
- Keep the Strands adapter off screen (claims-map #12).
- Do not show the `evidence/` folder or local paths.
