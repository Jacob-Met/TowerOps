# Independent receiving: scenario Load retires an earlier alternatives review

## Disposition

**The reviewed successor is qualified for both focused browser controls.** The initial composition reproduced a visible lifecycle defect: explicitly loading an identical saved scenario cleared the selected proposal and approval but left the earlier native alternatives selectable. The unchanged receiver passes on the successor, which clears that review at the scenario-load boundary.

| Exact source | Same-value explicit Load | Changed-version Load | Process |
| --- | --- | --- | --- |
| Initial tree `f4bc1ce05953dde6a33cea8588033fea9e18c5c4` | Fails: an old visible action recreates a pending proposal | Passes | 1/2; exit 1; 6.20 s; 2026-10-08 14:01 UTC |
| Successor tree `74ca2a2c29e09eb3c9d0c8b896eb81afcc418993` | Passes; a fresh native review restores usable proposals requiring new approval | Passes | 2/2; exit 0; 4.53 s; 2026-10-08 14:15 UTC |

There were no application page errors, external application requests, source/build integrity failures, receiving storage failures, or predicate changes in either run. The initial assertion failure is retained as negative product evidence. Each phase was executed once.

## What the counterexample establishes

The first group uses the actual **Review alternatives** button and native Python options route. It obtains 68 admitted alternatives from 74 checked candidates, chooses one and approves it through the existing UI, then chooses and explicitly loads the original real browser Save download. Review alone preserves the existing approval, as intended.

The before/after Save files have the identical SHA256 `0aa77d010974111d58fdc4812650e4f5c7f9c5efd86af88ae87ef8479f6984ec` in both phases. The receiver also compares the full decoded scenario: world, policy, clock, time scale, and selected flight. This avoids confusing a changed clock or selection with the intended same-value load.

On the initial source, Load clears the existing proposal and approval, but the panel retains its 68 alternatives and its earlier selected-proposal status. The previously selected button becomes enabled again. The receiver clicks that visible old action and records the resulting **PROPOSAL READY** state and enabled Approve button without another Review alternatives request. The old approval was **not** retained: Readback remains disabled. No unsafe separation result, approval bypass, or simulated actuation is claimed.

The scenario feature's fresh-decision contract is the relevant lifecycle expectation. The low-level alternatives binding intentionally accepts a cloned object with identical world, policy, and clock values; the corresponding native result can remain mathematically valid. The narrow repair retires an earlier UI review when the user explicitly loads a saved scenario. It does not change that value-based snapshot algorithm.

On the successor, the old actions are absent and the panel says **NO CURRENT REVIEW** after Load. A newly requested native review returns usable alternatives again. Choosing one enables Approve while keeping Readback disabled, so the new selection requires a new approval.

The second group changes only the saved world's version and verifies actual loaded-world fidelity plus alternatives invalidation. Its frozen test name mentions the existing snapshot guard because that explains the initial source's passing comparator. The successor clears the review explicitly before that guard would be needed. The final claim is preserved changed-version behavior, not proof that a particular internal branch executed.

## Source and runtime boundary

Both phases are over the same PR48 merge base, `093f88b29d6e1ede778f967528c7e010b7689ab1`. Each root-supplied input manifest pins **251 source files and 16 finalized production-build files**. Every nominated source/build file was verified before Chrome launch and after Chrome closed.

| Input | SHA256 |
| --- | --- |
| Initial source/build pin | `022805ce6de15626e92fdfa6daac13349191085d7655e7cd6b35c63dc168e0e6` |
| Successor source/build pin | `90b7ad5fd94cdcf7c465f51fd92b4fd0639ec1da8b738aa901d9f8fd829712ba` |
| Initial main.ts | `4b95aa8d24b98dedd26d55356556196f1e2f5236095d19ee2e901ad0733afdab` |
| Successor main.ts | `b235ec353d2556f45ede80b6ee6bb958a48efac993e6900834d668e5e460460f` |
| Unchanged independent receiver | `f1ff675481cb14a30868f6c106bde719aefdb26144688cce3828a299cebbcf0c` |

Independent source comparison found exactly two changed paths: web/airspace/src/main.ts and web/airspace/README.md. The other 249 files are byte-identical. The scenario loader now clears optionsReview/optionsStatus and updates its workflow messages. The snapshot comparison, alternatives panel implementation, Python worker, and native advisory_options.py are unchanged. successor-source-review.json retains the exact narrow diff and source identities.

Execution used Node v26.3.0, Chrome 154.0.8037.98 and Puppeteer 25.12.0 on the authorized Mac. The browser used private profiles and real file chooser/download events. The existing production builds and dependencies were read-only; no product or dependency tree was copied or changed. Passive request observation and a denying proxy kept application requests on the loopback origin; Chrome's blocked background attempts are separately recorded.

Both phases served the pinned Pyodide wasm, towerops.py, and advisory_options.py and exercised the product's native options request. No product function, worker result, or native solver response was replaced. This is isolated receiving of the exact compositions, not installation or current-serving evidence.

## Replay

The receiver takes an input pin JSON and a new, nonexistent output directory:

```sh
NODE_PATH=/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules \
  node independent_alternative_reset.mjs \
  reset-source-build-pin.json \
  /tmp/towerops-alternatives-independent-new-output
```

Use initial-source-build-pin.json for the retained counterexample. The input names the exact native source and build paths; all listed byte/SHA pins, and source Git blob pins when present, are checked. A relocated invocation should use a new copy of the metadata with only its source_root and build_root paths adjusted to verified relocated bytes. Preserve the original input and receipt. Rebuilt assets require a separately named receiving layer, since these receipts identify the exact existing builds.

The original execution wrappers are archived unchanged as run_initial.py.txt and run_reset.py.txt. Their native filenames are recorded in the publication manifest and process receipts; they are historical execution artifacts, not replacement tests. The replay command uses the unchanged .mjs receiver directly.

## Retained evidence

The packet retains the pre-execution source observations and receiver syntax receipt, both exact input manifests, raw stdout/stderr, both browser receipts and process receipts, every real downloaded scenario, the changed-version fixtures, and both screenshots. The initial 16-file negative-evidence manifest was verified again before and after the successor run.

The initial screenshot is after clicking the old action and shows the revived current proposal in the retained alternatives panel. The successor screenshot is after Load and before the fresh review; it shows no current review and the new guidance. Both were visually inspected.

This review does not repeat the author's broader browser matrix, the earlier raw-draft receiver, or unrelated native tests. A separate replay of inherited raw-draft controls, if performed, is a distinct receiving layer with its own authorship and source pins.
