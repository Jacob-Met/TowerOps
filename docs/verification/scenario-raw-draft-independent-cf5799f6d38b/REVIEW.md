# Independent receiving: saved scenarios with retained raw drafts

## Result and boundary

**Qualified for the two reviewed browser interactions.** Both independently authored groups passed on their first execution on 2026-10-08 at 13:24:40–13:24:45 UTC. The process exited 0 after 4.61 seconds. There were no application page errors, external application requests, source-integrity failures, or receiving corrections.

The exact nominated composition is tree `efd5d1d99edc0595111e15836c18a9b178abb4c3`, product-source tree `77fee12e647a82dea99506ccef13e967c28aad92`, over the PR46 merge `8d4933f33a0f5e0673fa9d00002e8b29302a1c53`. The author composed PR47's saved-scenario feature with PR46's raw-draft ownership changes. This receipt does not cover the later PR48 advisory-alternatives composition.

The independent input check verified all **404 nominated source leaves**, including the author's existing evidence, against source-manifest SHA256 `238311ba022629ad4cef386c0fd6afee0ee7f94126ccdcaaae7077fef606c50a`. The receiver verified the same 404 leaves before and after the browser run. All 15 files of the finalized production build were independently pinned before use and rechecked after use. Source and build were served read-only; no source tree, dependency tree, or build was copied or changed. The receiver never invoked Git or accessed the author's mutable Git index.

The five existing PR46 edits were also checked verbatim against an immutable read of `web/airspace/src/main.ts` at the PR46 merge, Git blob `d975ab8c55c01b0f6177ad736ed0c6b1fa821599`. These are the ownership flag, renderer guard, explicit raw Export, successful raw Load, and textarea input listener. The received main.ts SHA256 is `f4976fa8729cd3e5507ec1f721931706c91ecdec773443687aa3e3b451f9f7e4`. Exact primary bytes and fragment comparisons accompany this receipt.

## Two independent controls

| Control | Consequential observation |
| --- | --- |
| Valid third-world draft authored **after** scenario review | The user reviews saved scenario B, then types a valid different world C into the raw editor. Review remains usable, and a real Save still downloads live A. Applying B restores its full world, policy, clock, scale, and selection while preserving C literally, including surrounding newlines. The feedback explicitly explains that the raw draft remains. |
| Explicit Export during another pending review | Continuing the same group, the user reviews A while B is live. Export replaces the raw draft with B without invalidating A's pending review. Applying A restores A, the editor resumes synchronization, and the feedback is the pristine scenario message. |
| Genuine file-read completion overtaken by same-value raw Load | The second group begins a real file chooser read of B. The native File.text method runs and returns the uploaded bytes; only delivery of that successful result is held. Typing equivalent A does not cancel the read. A successful raw Load then replaces the live state object without changing its value, invalidates the pending read, and refuses the old completion when released. |

The first two rows belong to **one** sequential group; there are exactly two new browser groups.

Live state is established by the rendered flight register and **seven actual browser Save downloads**, not by assuming the raw textarea is live state. The first group's A downloads all have SHA256 `0aa77d010974111d58fdc4812650e4f5c7f9c5efd86af88ae87ef8479f6984ec`; the B download has `f41d502a4767229c1db873501acf64824f55cac44da8edab72607e9d56e91de7`. In the second group, canonical A before and after the stale completion has the identical download digest `b5ff1edbe50d016452d7a197cc57bc8e32167dfa194d9a08f051208c63e68917`.

The raw draft is a fully formed WorldState fixture with two stationary aircraft, finite bounded fields, and a separate version and timestamp. It is deliberately never submitted through raw Load in the first group. The second group's gate checks that the genuine read text and byte count match the uploaded fixture, then restores File.prototype.text after releasing the result. It changes completion order only; parsing, UI state, successful raw Load, and scenario invalidation all execute the product's code.

## Actual runtime and isolation

- Mac receiver root: `/tmp/towerops-raw-draft-review-cf5799f6d38b-zsv38ev0`.
- Read-only author source: `/tmp/towerops-scenario-draft-cf5799f6d38b-hzrph_6k/candidate`.
- Node v26.3.0, Chrome 154.0.8037.98, Puppeteer 25.12.0.
- Chrome executable: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- Existing Puppeteer module root: `/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules`.
- A private browser profile and download directory were used. The finalized Vite production output was served from a loopback HTTP server at its existing base path.
- Request observation was passive. A denying proxy blocked Chrome's background connection attempts; the receipt records those attempts separately from the empty external-application-request list.
- No live account, provider, installed service, or production state was used or altered. These two groups did not invoke the Python planner or audit solver.

The 15-file dist pin establishes the exact executed build; this review reused the author's finalized build rather than rebuilding dependencies. Build provenance is named in input-receipt.json. The result is an isolated native-browser receiving observation for the nominated composition, not a deployment or current-serving claim.

## Replaying the exact receiving script

The original execution command and timestamps are preserved in process-receipt.json. With the nominated native source still present, run the unchanged receiver from this packet's directory, using a **new, nonexistent** output directory:

```sh
NODE_PATH=/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules \
  node independent_raw_draft.mjs \
  /tmp/towerops-scenario-draft-cf5799f6d38b-hzrph_6k/candidate \
  /tmp/towerops-raw-draft-independent-new-output
```

Keep input-receipt.json, source-manifest.json, and dist-manifest.json adjacent to the receiver. It verifies every pinned input before opening Chrome and again after Chrome closes. prepare.py and run.py are retained as exact original native setup/execution artifacts, including their original paths.

For an independently relocated source checkout, first materialize the nominated source bytes and exact build (or record a separately rebuilt build as a new receiving layer). Copy this packet into a new work directory; change only that copy's input-receipt source path to the relocated absolute source root. Do not edit the preserved original receipt or change expected source/build hashes. The receiver will reject any changed nominated source or build file. Such a relocated invocation is a new run, not the recorded run here.

## Evidence notes

browser-r1/receipt.json contains both predicates, actual download digests, UI states at each relevant transition, served asset digests, network observations, and before/after pin checks. stdout, empty stderr, process metadata, fixtures, all seven downloaded files, and the unchanged receiver are retained. No failed independent attempt was omitted: this two-group receiver had no earlier execution.

Both screenshots were visually inspected. valid-draft-after-apply.png shows the separate draft and honest retained-draft feedback. stale-native-read-refused.png is captured after the final Save and shows the hidden review; the intermediate refusal wording is preserved in the structured receipt because the successful Save subsequently changes the status message.

There is no blocker within these two reviewed interactions. This packet adds receiving evidence only and does not replace the author's broader suites, their retained infrastructure failures, or prior scenario-feature reviews.
