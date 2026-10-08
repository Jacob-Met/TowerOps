# Inherited raw-draft receiving on the PR48 + scenario successor

## Result and authorship

**Both inherited browser controls pass on the exact successor composition** `74ca2a2c29e09eb3c9d0c8b896eb81afcc418993`. The single replay ran on 2026-10-08 at 14:26 UTC, exited 0, and took 3.22 seconds. It had no application page errors, external application requests, integrity failures, or receiving corrections.

This is a new source replay of two previously independently authored predicates. It is **not two newly authored tests**. The copied independent_raw_draft.mjs is byte-identical to the receiver that passed 2/2 on the earlier `efd5d1d99edc0595111e15836c18a9b178abb4c3` composition. Its SHA256 remains `8ab4f56d0f8e0a62f80b72f799268d9e1ee43012dd5e336f6bf5033930db1997`.

The earlier 28-file raw-draft packet and the separate 33-file alternatives comparison were already sealed. Their declared files were rechecked before preparation of this replay and again during final sealing, without changing them. The alternatives comparison retains its separate 1/2 initial counterexample and 2/2 repaired outcome.

## Preserved interactions

| Inherited group | Observed result on the successor |
| --- | --- |
| Valid third-world raw draft typed only after saved-scenario review | The pending review stays usable; Save still downloads live A. Apply loads B's complete world, policy, clock, time scale and selection while preserving draft C literally and explaining it. Reviewing A and explicitly exporting live B retains A's review; applying A restores synchronization and the pristine feedback. |
| Genuine File.text completion overtaken by same-value raw Load | The real file chooser reads B and the native File.text method resolves its actual bytes; the receiver holds only their delivery. Typing equivalent A keeps the read pending. Successful raw Load invalidates the pending read even though A's value is unchanged. Releasing the original native text does not reopen the stale review. |

The first group's real A downloads retain SHA256 `0aa77d010974111d58fdc4812650e4f5c7f9c5efd86af88ae87ef8479f6984ec`; B has `f41d502a4767229c1db873501acf64824f55cac44da8edab72607e9d56e91de7`. The second group's normalized A before and after the stale completion has `b5ff1edbe50d016452d7a197cc57bc8e32167dfa194d9a08f051208c63e68917`. These match the earlier receiver's positive controls. Full decoded scenario comparisons, the live flight register, seven real downloads, and intermediate UI states are retained.

No predicate, expectation, selector, fixture definition, or native timing gate was changed. The new setup metadata points the same receiver at the current nominated source/build. The product-source-tree field is explicitly null because root nominated one full source tree rather than a separate product-only tree.

## Exact receiving boundary

The root source/build pin has SHA256 `90b7ad5fd94cdcf7c465f51fd92b4fd0639ec1da8b738aa901d9f8fd829712ba`, copied unchanged as source-manifest.json. It nominates 251 source files and 16 finalized production-build files. The original receiver verified their bytes and SHA256 before Chrome launch and after Chrome closed; the final collector also checked the source Git blob identities supplied by the root pin.

The received main.ts SHA256 is `b235ec353d2556f45ede80b6ee6bb958a48efac993e6900834d668e5e460460f`. The source and existing dist were read-only. Only the inherited receiver and small receiving metadata were copied; product source and dependency trees were not copied or changed.

Runtime was Node v26.3.0, Chrome 154.0.8037.98 and Puppeteer 25.12.0 on the authorized Mac. The run used a private browser profile, loopback serving, real file chooser/download events, passive request observation and a denying proxy. Chrome background attempts are recorded separately from the empty external-application-request list.

These raw-draft groups do not request the Python planner or alternatives solver. The separate alternatives packet qualifies that native path. This replay is evidence for the exact isolated source/build composition, not installation or current-serving behavior.

## Replay and evidence

Keep independent_raw_draft.mjs, input-receipt.json, source-manifest.json and dist-manifest.json together. With the nominated native source still present, use a new output directory:

```sh
NODE_PATH=/Users/me/.npm/_npx/4b4c857f6efdfb61/node_modules \
  node independent_raw_draft.mjs \
  /tmp/towerops-root-advisory-cf5799f6d38b-8zg02jnj/candidate-reset \
  /tmp/towerops-raw-draft-pr48-new-output
```

For relocated exact bytes, make a new metadata copy and update its source path to the relocated absolute source root; keep expected file digests unchanged. Treat a rebuilt build or another source composition as a separately recorded receiving layer. Do not edit preserved receipts to imply they were run elsewhere.

The original stdin preparation script and execution wrapper are archived unchanged as prepare-replay.py.txt and run.py.txt, with their native-to-repository names declared in the publication manifest. The actual replay uses the unchanged .mjs driver directly.

The packet retains the exact receiver, input mapping, root source/build pins, original process command, raw stdout/empty stderr, complete browser receipt, all fixtures and seven downloaded files, and two inspected screenshots. The retained-draft screenshot shows the explanatory message. The hidden-review screenshot is after final Save; the intermediate stale-read refusal wording is in the structured receipt because Save changes the status message afterward.
