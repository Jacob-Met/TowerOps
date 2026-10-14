# Copy a saved Explorer request into the next form

The Synthetic Explorer now provides **Use request settings** after a current
saved export finishes replaying. It copies the saved scenario and both request
booleans into the ordinary controls. It does not run the engine or replace the
displayed result. Choose **Run synthetic case** explicitly when ready to make a
new result.

## Use the feature

From the pinned checkout, with Python 3.12 or later:

```sh
python3 -B explorer.py serve --port 8765
```

Open the loopback URL printed by the foreground server. If that port is occupied,
choose another unused port. Stop this server with Ctrl+C in its own terminal.

1. Run any synthetic case and export its result as JSON, or use a supplied saved
   fixture from the worked handoff.
2. Select the saved JSON in **Replay exported JSON**. After MATCH or MISMATCH,
   choose **Use request settings**.
3. Inspect the copied case, checkboxes and case description. Change any input you
   want, then explicitly choose **Run synthetic case**.

Copying keeps the displayed run, projected time, export, replay verdict, main
status and any field explanation unchanged. In particular, **Missing
acknowledgement** can carry `include_ack: true` while its effective acknowledgement
fixture is null. The form copies the exact request switch, not the inferred
presence of that fixture. These are simulated research inputs, not real approval,
acknowledgement or operational authority. MISMATCH does not authenticate the saved
output.

The action waits for both a completed current replay and a successfully loaded
catalog containing the scenario. New, pending, rejected or cleared selections
retire it immediately; delayed old completions cannot bring it back. Form values
already copied are not undone. An explicit Run does not retire the accepted
saved request, so copying it again can restore settings after manual edits.

## Source and evidence boundaries

The original source is `202782f29f3a0ed1411e67a7744f9e63f26926f1`, tree
`90c81370fb3215943a8b64a4264f8e362a05d479`. The five-path change is confined to
the app, two HTML widgets, the EXPLORER guide, a new focused Node test,
and a two-ID snapshot exclusion in the existing selection test. Backend, engine,
scenario catalog, explanation helper, CSS, workflows and installed runtime are
unchanged. Side-by-side installed adoption is a separate receiving step; this
source publication does not claim to update the old default launcher.

The original public contract and author chronology are retained in
[author preparation](author/preparation/public-contract-v1.md). The original
controlled observer's failed GET-body diagnostic and the narrowly corrected
version remain separate. The actual original export/replay commands were not
repeated.

Author syntax admission and all twenty-five named Node methods passed: ten new
settings controls, ten retained selection controls and five retained explanation
controls. All fifteen offered source files remained unchanged. The raw outer
author receipt remains false because its collector expected TAP summary lines
and Node emitted the spec reporter. The [separate retained-output audit](author/author-v1/reporter-classification-audit-v1.json)
verifies complete raw summaries and method names without rewriting that receipt
or rerunning the product. Read [the author scope note](author/author-v1/README.md)
before interpreting those records.

The independently frozen actual browser and production-HTTP course is retained
under `independent-anvil/`. Its original descriptor is consumed byte-for-byte by
the maintained publication admission; received source-at-execution metadata is
not rewritten to pretend that the source was published earlier.

The original browser absence course passed all 24 observations. The single
candidate course passed all 78 comparisons through the actual Python Handler
and Firefox 157: sixteen HTTP requests including seven POSTs, three actual saved
downloads, and two retained candidate screenshots. The two A downloads before
and after copying B settings are byte-identical; after explicit Run B, copying
C settings still exports the unchanged B result. One delayed old replay body and
one delayed catalog response establish the stated current-selection boundaries.
All eight source files, frozen controls and original fixtures were preserved;
owned browser, backend and relay closed, with zero relay sockets and both
listeners closed. This is the declared local receiving sequence, not a claim
about every browser or scheduling combination. See the complete
[independent receiving guide](independent-anvil/README.md) and
[retained visual interpretation](received-display-review-v1.json).

## Reproduce the focused production-script controls

```sh
node --check web/app.js
node tests/test_explorer_request_settings.cjs
node tests/test_explorer_replay_selection.cjs
node tests/test_explorer_explanation.cjs
```

The controlled Node methods, independent actual browser course, passive artifact
custody and later installed use have distinct scopes. There is no full repository
suite, universal browser-scheduling, live aviation or user subjective acceptance
claim.
