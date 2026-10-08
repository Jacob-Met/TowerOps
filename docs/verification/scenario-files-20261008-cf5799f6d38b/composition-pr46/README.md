# Saved scenarios with PR46 raw-draft ownership

This companion qualifies the scenario feature over the exact PR46 main, 8d4933f33a0f5e0673fa9d00002e8b29302a1c53. The only product changes from the previously published scenario feature are its main.ts and README composition seams. All five PR46 edits remain verbatim. An authored raw WorldState JSON draft remains separate while a scenario is saved, reviewed, cancelled or applied. Successful scenario loading says that it loaded the scenario and retained the draft, and points to Export live world. A pristine editor retains the original feedback.

The browser checks inspect the real traffic register and fresh scenario downloads. They establish that Apply restores the selected scenario's world, complete policy, clock and selected aircraft while keeping unrelated editor text; they do not infer the live world from a retained textarea. Successful raw Load invalidates a pending scenario review even when the new world's values are identical. A rejected raw Load preserves the review and draft. Explicit Export replaces the draft and resumes live editor synchronization.

## Exact source boundary

| Boundary | Identity |
| --- | --- |
| Previously published PR47 head | 9c6bef26bfef04f1eca264dec533e47e0f270aa8 |
| Previously published PR47 tree | d5d9827824e0d6f79fc54e5565698dc5d5a783ce |
| Qualified current base | 8d4933f33a0f5e0673fa9d00002e8b29302a1c53 |
| Base tree | 918931cb2034049be9e7717012b3b3309a63b4c3 |
| Product source tree, 188 leaves | 77fee12e647a82dea99506ccef13e967c28aad92 |
| Candidate with preserved historical evidence, 404 leaves | efd5d1d99edc0595111e15836c18a9b178abb4c3 |
| Candidate plus the two publication-lint files, 406 leaves | 93171c5bbcff4ac43b3701ff87a3906d3343f29a |

The exact source manifest records all 404 candidate leaves. The original 223-file scenario contribution remains a historical input: 221 files are identical, including all 216 evidence files, and only the two product seams change. All 181 unrelated leaves from the qualified base remain exact. The five other scenario product files are identical to the original published contribution. The final overlay manifest and preservation receipt record the additive companion and complete resulting publication tree without changing the historical packet.

A later read observed merged PR48 at 093f88b29d6e1ede778f967528c7e010b7689ab1. Its advisory alternatives overlap four scenario product files and change the Python worker and deployment gate. That advance was reported to the integration owner; it is not rebased into this frozen PR46 companion. See observed-later-main.json. This is a qualified merge checkpoint, not a claim that later main has already received the feature.

## Results

| Qualification | Result |
| --- | --- |
| Frontend tests | 188 passed |
| Native Python tests | 108 passed |
| Production build and generated reference check | Passed |
| Existing author scenario browser groups | 7 passed |
| Existing independent scenario groups | 6 passed |
| Pending real WebCrypto completion control | 1 passed |
| Scenario and encounter interactions | 3 passed |
| Encounter owner's browser controls | 10 passed |
| Decision-trace owner's browser controls | 11 passed |
| Scenario and decision-trace interactions | 2 passed |
| PR46's nine unchanged predicate bodies through native CDP transport | 9 passed |
| New scenario/raw-draft interactions | 4 passed |
| New independent draft/review completion controls | 2 passed |

The first browser rows total the 40 pre-existing controls. The nine upstream draft checks, four authored interaction groups and two new independent controls are separate. No source byte changed during receiving. The independent review additionally authors a valid third-world draft after file review, verifies real Save downloads A→B→A, and checks that Export keeps another pending review. A separately held genuine File.text completion cannot reopen review after a successful same-value raw Load. The new draft screenshot shows the phone layout with the explicitly retained text.

Native receiving used Node 26.3.0, Chrome 154.0.8037.98 and Puppeteer 25.12.0. Native Python was 3.12.8 with pytest 8.4.2. Hosted CI pins pytest 8.3.5; runtime parity is not claimed. The actual commands, dependency identities, original mixed gate result and later corrected receiver outputs are retained. The original qualification driver correctly exited nonzero for historical Ruff findings and upstream CDP navigation failures, despite the application gates and 40 controls passing.

The separate publication copy passes normal Ruff 0.16.10 check . with exact-path exceptions for the six immutable receiving scripts. Product settings are unchanged. The earlier source-only Ruff results, the original 18 full-tree findings, the hosted failing job and the later full-publication gate are separately identified. See ../PUBLICATION-LINT.md, lint/, and the final overlay receiving manifest.

## Receiver corrections and retained failures

The original PR46 script timed out in Page.navigate before eight functional check bodies could reach the page. Its remaining exception-only check passed without exercising those paths. The same Vite source and Chrome executable loaded through Puppeteer CDP sessions. Two preserved shortcut attempts then failed the editor's own actual-typing assertion because they inserted into unselected text. The final receiver sends the native CDP selectAll editing command with rawKeyDown/KeyA, then the original Input.insertText. It does not assign a DOM value.

All nine check bodies remain byte-identical to the PR46 source: 5,374 bytes, SHA256 6687500786795aeb2358dffa93edd2e4444e43316f0b860b3db55be79a04afca. The Vite serving block is also byte-identical. Receiver-pins contains the original/follow-up identities and a reconstructible transport patch. The final adapter is 0ef3b762c5fe83eda6b5d676da1d9a6927cb4f682b3053e71e5defe75016ac14.

The first two authored interaction runs reached the last group's traffic edit with the existing Shape the traffic panel collapsed. A third preserved receiver added pointer hit testing, which identified SUMMARY rather than the Inject crossing traffic button. The fourth receiver opens that existing panel before clicking. All four predicates pass; the one-line navigation patch and earlier raw failures remain. No application fix was made for these receiver defects.

The [new independent review](../../scenario-raw-draft-independent-cf5799f6d38b/REVIEW.md) retains its original 28-file manifest and all executed bytes. Two newly contributed setup drivers have explicit .py.txt transport names: prepare.py.txt and run.py.txt. They are historical driver transcripts, not requalified Python modules. The other 26 paths stay exact. independent-archive-path-map.json records original and published paths, byte counts, hashes and Git blobs; lint/independent-historical-drivers.json preserves the four packaging-time Ruff findings. The original six-path Ruff policy is unchanged. The independent .mjs receiver and its replay command are unchanged.

## Reproduction

Start from the exact current base and restore the original published evidence directory from PR47. Apply scenario-on-pr46.patch to obtain the seven product files, then stage the result. Before the additive lint policy and this companion, git write-tree must return efd5d1d99edc0595111e15836c18a9b178abb4c3. The smaller draft-on-scenario.patch records the two product seams against the original qualified scenario product source.

Use the exact project package lock and existing build/test commands:

~~~sh
npm --prefix web/airspace ci
npm --prefix web/airspace test
npm --prefix web/airspace run build
python -m pytest -q
python tools/generate_airspace_reference.py --check
python -m ruff check .
~~~

current/process-receipt.json records the native executable paths and commands used. The five unchanged JavaScript scenario receivers are already preserved in ../composition-pr39-pr42/receivers. The encounter owner uses tools/verify_encounter_browser.py, and the decision-trace owner uses tools/verify_decision_trace.mjs. The native runtime paths in the receipts are receiving locations, not required installation paths.

With a separate output directory and profile, run the final upstream adapter and new interactions:

~~~sh
node receivers/pr46-puppeteer-receiver-v3.mjs \
  --root /absolute/checkout \
  --browser /absolute/chrome \
  --toolchain /absolute/checkout/web/airspace/node_modules \
  --qa /absolute/isolated-qa \
  --output /absolute/isolated-qa/pr46
node receivers/scenario-raw-draft-v4.mjs \
  /absolute/checkout /absolute/isolated-qa/scenario-draft
~~~

Provide Puppeteer through the receiving environment's NODE_PATH, and use REVIEW_SOURCE_TREE for the existing independent receiver's stated source identity. Each receiver creates its own synthetic fixtures and local browser outputs. This companion intentionally omits browser profiles, dependency trees, Vite caches and generated fixture/download directories. It retains the actual scripts, source/build hashes, raw results, relevant screenshot and exact failure history. The separately nominated independent-review prefix also retains its seven real downloads, three small fixtures and two screenshots. Empty stderr files are recorded by their zero-byte digest in receiving-inputs.json.

