# Native receiving: current 093 with composed 0893

Qualified baseline: `093f88b29d6e1ede778f967528c7e010b7689ab1`, tree `4a87643d57cabf81e570b21c119f00b43f79448e`. Candidate main SHA-256: `0893cae0bedbe7e7516b92c0f55eb01a0d6c09289dac3ed14d6f4da153b3b0dd`. The unchanged playback test is `fbe02527200a428fae18c6d45b09ef942b9dcfd411d7e8a8bf11c30d5e74a845`; the unchanged accepted browser driver is `f1162d6d417327de3a8959e394541c27ab6f9f04aa3ee773c4958e286c4de941`.

The actual configured Vitest suite passed **147 tests across 11 files**, including 14 playback controls and 13 advisory-options cases. Both baseline and candidate completed the native prepare-python, TypeScript and Vite build. All 59 baseline and 60 candidate source files, both 16-file builds and the installed dependency lock retained their exact pins. No new dependency installation was needed.

Actual Chrome 154.0.8037.98 used fresh disposable profiles and the native built page, drawing, physics, controls and Export live world handler. Only animation-frame scheduling was controlled for deterministic elapsed time.

| Browser case | Exact current baseline | Candidate desktop, 1280px | Candidate mobile, 390px |
| --- | --- | --- | --- |
| Reset after 3x | Known retained-rate and stale readouts reproduced | Pass | Pass |
| Reset after 0.5x | Known retained-rate and stale readouts reproduced | Pass | Pass |
| Policy edit at 2x | Known stale pause label reproduced | Pass | Pass |
| Refused flight at 2x | Known stale pause label and encounter state reproduced | Pass | Pass |

Reset cases first set all three policy controls to 6 NM, 1,500 FT and 6 MIN. The candidate restored every slider, adjacent readout and active policy statistic to 5 NM, 1,000 FT and 5 MIN. It held the exact fixture paused, displayed Run traffic and 1.0x, and resumed exported aircraft at the actual default 1x rate. Clock, world version, aircraft identity, all motion axes and velocities were checked independently. Automatic pauses preserved 2x and refreshed the current paused encounter state.

Baseline admission required the exact known failure set plus positive retained-rate and stale-text observations; unrelated failures would reject it. Every run had trusted input events, zero page exceptions, no horizontal overflow and unchanged source/build bytes. Original full-page screenshots show the current Review alternatives control alongside the correct Reset and policy controls.

`receiving-text.json.gz` contains 18 exact raw files as gzip-compressed JSON with base64 contents, original paths, sizes, SHA-256 and Git blob hashes. `receiving-manifest.json` lists those entries without embedded contents. The packet includes native logs, all three browser reports and process receipts, source manifests, driver and launcher. `image-receiving-manifest.json` verifies the three separate original, unedited PNGs.

The browser gate covers playback, Reset, automatic pause, encounter state and explicit WorldState Export. It does not type a WorldState draft, choose an advisory alternative, invoke planner/Pyodide, or exercise approval/readback. Earlier C4 browser and 803 native-only cuts remain separate evidence. These results came from an isolated Mac qualification workspace; hosted Pages delivery, main-hub installation and production service state require their own receiving identity.
