# Reuse a saved Explorer request without retyping its controls

Owner: continuing HAMON team d3745ea0f44f / Loom. Anvil owns independently frozen original-first browser/HTTP receiving; root owns independent source/integration review and a separately coordinated later adoption path.

## Useful outcome and original source

The Synthetic Explorer can replay a saved export and explain a mismatch, but its scenario and two simulated-fixture switches must be re-entered manually before exploring a variation. Add one explicit **Use request settings** action for the currently completed replay. This fills the form only; the person still chooses **Run synthetic case**.

Baseline main `202782f29f3a0ed1411e67a7744f9e63f26926f1`, complete tree `90c81370fb3215943a8b64a4264f8e362a05d479`. Original app blob `ca183c7bff0bc42a3b9a8f7494fd2cca1816bec0`, index `3ed669246d6af590acd69bbea09ac5207b0c1471`, backend `875707f6480a54c2e450a4344c35090e7518b284`, scenarios `33b5703d2ce0d4177c50f05536e3f2715c8bea3b`. The complete current tree has no AGENTS/CONTRIBUTING/HALT/WORKSTREAM instruction file. All sixteen current open PR changed-path lists have no overlap with the five paths below; a fresh request-settings issue search found no existing claim. Existing Airspace/native-world, saved-file producer, replay, explanation and installer owners retain their scopes.

## Public behavior frozen before implementation

1. Add button `#replay-use-settings`, text **Use request settings**, initially hidden and disabled. Add local status `#replay-settings-status` with `role="status"`, initially empty.
2. Both a current MATCH and a current MISMATCH can make the action available after an ordinary successful `/api/replay` response with boolean `matches`. Native replay already validates the request independently of whole-result equivalence. A mismatch does not grant authenticity, authority or acceptance of the saved output.
3. Require the captured request to have exactly `scenario`, `include_approval` and `include_ack`: a string scenario present in the successfully loaded scenario catalog, plus two actual booleans. Use the exact request switches, not effective fixture presence: a missing-fixture scenario may still record a true switch while its effective fixture is null.
4. Until the scenario catalog is ready, keep the action hidden/disabled. If the current replay has already completed, successful catalog arrival may enable that still-current selection. Catalog failure or an unavailable scenario never enables it.
5. One explicit click copies the scenario into the existing selector and both booleans into the existing checkboxes, and updates the selected scenario description. It does not reread the file, fetch any endpoint, send `/api/run`, render a new result, reset projected time, change the displayed plots/audit/export, alter the main run status, alter the replay verdict, or clear/change the explanation.
6. The local applied status is exactly: **Request settings copied. Run synthetic case to produce a new result; displayed result is unchanged.** Values are local form inputs for synthetic research fixtures, not actual human approval, acknowledgement or operational authority.
7. The existing Run button remains the only way this action's settings produce a new run. Run captures the current controls through its unchanged request/render path. Pressing Run does not retire the settings action; it remains available for the current accepted replay, including an explicit repeat copy after manual form edits.
8. A new file selection immediately hides/disables the action and clears its local status before asynchronous reading or replay. Pending, rejected, malformed, oversized, cleared or superseded selections have no usable old settings action. Old file-read, HTTP/body success or error completions cannot restore it. Existing selection identity rules remain in force; outstanding requests are not promised cancellation.
9. Changing or clearing the replay file does not undo values already copied into the ordinary controls. It retires the ability to copy from the old selection only. Existing manual selection, checkbox, run, export, replay and explanation semantics otherwise remain unchanged.

## Narrow source fence

- `web/app.js`: new local settings-control state/action and its existing replay/catalog lifecycle seams.
- `web/index.html`: the button and local status only.
- `EXPLORER.md`: practical explicit-copy/then-Run guidance and limits.
- New `tests/test_explorer_request_settings.cjs`: focused controlled lifecycle/form/request preservation tests.
- `tests/test_explorer_replay_selection.cjs`: only add the two new replay-widget IDs to its unrelated-display snapshot exclusion. Preserve every existing assertion and case.

No backend, scenario, engine, replay helper, CSS, Airspace, dependency, workflow, installed selector/runtime or existing evidence path is edited. A later installed-use path is separately owned by root; this feature does not overwrite the currently working installation.

## Receiving and publication boundaries

An original-only observation will preserve the missing action with exact source identities before candidate implementation. Author controls use the original production browser script in a controlled DOM/fetch environment, keeping that scope distinct from Anvil's one bounded real browser/production-HTTP course. Independent expectations and executable controls stay separate from the candidate until their freeze. Current input copies, displayed result/export, captured requests and process closure will be retained without replaying the earlier broad browser or installer courses.

Both inherited workflow bodies were read. They subscribe to push/PR (and a separate manual demo dispatch), not issue/comment events. No Actions are dispatched, added or changed; source publication follows reviewed exact selection and ordinary skip-marked gates. No source publication or actual browser acceptance is claimed by this reservation.

[skip ci] [skip actions]

skip-checks: true
