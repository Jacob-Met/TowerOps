# Scenario composition with playback and radar: independent native receiving

The frozen **8cd8023a2f676b2faa17d5d5120e3ae3e4fd54f4** composition passes the existing owners' actual-browser controls on its unchanged normal build. No product or test source was changed by this receiver.

| Receiving scope | Actual result |
| --- | --- |
| Exact playback owner driver, desktop 1280 px | 4/4 cases, exit 0 |
| Same unchanged playback driver, 390 px emulation | 4/4 cases, exit 0 |
| Radar owner predicates on production dist | 19/19 checks, exit 0 |
| All source and build bytes before/after every run | 1,017 source files and 16 build assets exact |
| Independent Git entry preservation | 560 historical scenario entries and 450 unrelated main entries exact |

## Source boundary

The current main base is [687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8](https://github.com/Jacob-Met/TowerOps/commit/687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8), tree aa483f5d708f4f6f6ab510168884eaf4d25cf9e1. It contains playback PR44 and radar PR53. Root composed the frozen scenario contribution over that base. This independent review received the resulting 1,017-leaf tree through its original source/build manifest, SHA256 c7a2fd2cee35e79b69fb74a520b15de0b2d697756ea60ac9b2ad68cbd86a2301.

The seven scenario product paths are the existing main/index/style/README plus scenario-file.ts, scenario-ui.ts and scenario-file.test.ts. Five retain their prior 3c5ec99 entries exactly; only main.ts and README have the current composition. The independent tree comparison checks mode, type and Git blob, as well as every actual source byte and executable mode.

The owner pauseTraffic helper, automatic-pause functions, planner, Reset and frame integrator remain byte-exact lines from current main. Both radar import/readout literals remain exact. The complete current README remains the unchanged prefix, with the original scenario section appended. Explicit scenario Load restores world/policy/clock/rate/selection, pauses traffic, resets frame timing and renders; that current render refits radar and updates the encounter explorer from the restored world. See source-seam-review.json and source-seams.patch.

## Maintained playback receiver

The accepted owner driver is restored byte-exact from [the published current093 archive](https://github.com/Jacob-Met/TowerOps/tree/687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8/docs/qualification/playback-55e3-20261008/native-093-0893): SHA256 **f1162d6d417327de3a8959e394541c27ab6f9f04aa3ee773c4958e286c4de941**.

Its four cases cover Reset after 3x and 0.5x, automatic pause after a policy edit at 2x, and automatic pause after a refused custom flight at 2x. It uses real Chrome input events and the explicit Export live world action. Only animation-frame scheduling is controlled; app handlers, state calculations, drawing and DOM remain native.

Both widths restore the actual default 1x engine rate, its 1.0x label, all policy sliders/readouts/statistics and the original paused world. Resumed clock, aircraft positions, altitude, identity and velocities pass the owner's existing predicates. Automatic pauses preserve the chosen 2x rate and refresh the paused encounter view. There are no page exceptions or horizontal overflow. The planner runtime is deliberately uninvoked in this receiver.

## Radar receiver adaptation

The owner full-app driver is preserved at SHA256 **7dc85c569334dad1d8c50a5023390e77795587a962d49cf1e9be53de39e0982e**, from [the published radar archive](https://github.com/Jacob-Met/TowerOps/tree/687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8/docs/qualification/radar-framing-52e56ea8fcca).

Its historical Vite import, source paths and 093 metadata required a receiving-environment adaptation. The successor accepts explicit current source/build paths and identities, serves the exact normal production dist from loopback and pins that dist before/after. It neither builds nor rewrites the product, and it installs no dependencies. The exact 8,767-byte region containing all 19 browser predicates is unchanged, SHA256 **b0b59f24cdd51da85aeeca9326fc8cf3b201d604d9e7c5b39e8f2df38d453e38**. The adapter is SHA256 **0a5008339e17ab794c84716de7996dd4c25b3986c2192abb3f8d575f14d70309**; the narrow patch and proof are included.

The native renderer keeps translated traffic separated at the same scale, shows absolute north coordinates, retains the real origin guides and displays an explicit unavailable view for finite projection overflow. Import admission, selected aircraft, raw draft preservation, Export and Reset remain intact. The real self-hosted CPython planner proposes without changing world coordinates; normal approval/readback applies one world revision and yields a valid four-event audit. All 19 checks pass with no page exceptions or failed requests.

The owner Canvas observer forwards every original drawing call. These are real Chrome rendering and application actions, with explicit recording instrumentation. They are distinct from the separate public Pages receiver, which uses no such instrumentation.

## Evidence and replay

The first executions all succeeded. Raw stdout/stderr, every owner report, all command/process receipts, original source/build bindings, exact executed setup drivers and receiver sources are preserved as exact base64 bytes in receiving-archive.json.gz. archive-manifest.json pins every member. restore-receiving.cjs verifies the archive and every member before restoring into a new empty directory. Historical executed Python drivers retain .py.txt transport names; they are transcripts of the exact executed bytes, not newly qualified Python modules. No lint exception is added.

Node 26.3.0, Chrome 154.0.8037.98 and the already installed Puppeteer 25.12.0 were used on the authorized Mac. No dependency trees, browser profiles or generated runtime bundles are included. The seven original PNGs are unedited. Desktop, narrow Reset, narrow translated traffic and unavailable captures were visually inspected; the existing close-label crowding remains visible and is outside this composition's source changes.

Reproduction after restoring the archive uses the exact commands in qualification-summary.json with current absolute paths for an independently reconstructed 8cd source tree and its normal build. The unchanged playback driver accepts --repo, --manifest and --dist. The radar adapter additionally requires the actual base commit, source tree and build manifest. Source/build manifests must describe the reconstructed bytes; they are validated before actions.

The root frontend run at this source identity separately had 223 passes and 3 playback-fixture failures. These actual-browser results do not relabel that run as a pass; root and the independent fixture reviewer own that diagnosis and any successor. Public deployment, normal main-push Pages artifact identity and actual canonical-route actions remain a separate receiving boundary.
