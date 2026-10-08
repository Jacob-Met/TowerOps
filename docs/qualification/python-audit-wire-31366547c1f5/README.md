# Preserve original Python audit hash inputs on current main

## Receiving need

This contribution is composed on TowerOps main `09b96e31d2867af5b7a9738406d0431cf1010090`. It preserves the selected-flight editor, merged timestamp/float-format fixes, and newer numeric admission guards.

Those fixes make fresh transactions agree, but a valid retained Python audit can still contain integer approval or readback timestamps from an earlier producer. JSON parsing removes the distinction between Python integers and floats. Rebuilding that older event through the browser's float-field serializer changes its hash input and incorrectly displays a valid chain as broken. The retained fixture records the original native events and canonical bytes; it is not rewritten to satisfy the browser serializer.

## Change

The worker supplies each event body's original `canonical_bytes` result beside its existing events and audit JSON on both successful and rejected applications. The worker client registers that metadata before resolving its response. The verifier binds the copied metadata to the exact received events array, checks sequence, previous hash and agreement with the displayed event, and hashes the original UTF-8 body. Missing or malformed registered metadata fails closed. Existing browser-only audit verification remains available, and sequential appends retain the imported prefix.

Native event objects and `audit_json` are unchanged. The current worker's guarded timestamp conversion, `core.ts` float formatting, Python kernel, policy, planner, editor and client lifecycle are preserved.

## Current-main verification

| Gate | Result |
|---|---|
| Complete frontend suite | 91 passed: all 70 upstream cases plus 21 original-byte receiving cases |
| TypeScript and Vite production build | Passed |
| Current-main Chromium/Pyodide baseline | Ordinary control passed; retained-history success and refusal both showed BROKEN despite native-valid chains |
| Composed Chromium/Pyodide candidate | 7 passed, 0 failed, 0 page errors |
| Native payload comparison for three shared browser cases | Exact `audit_json` bytes, parsed events and resulting world states identical |

The browser receiver runs the built app and real Python worker. For the two history cases it supplies a retained native-valid audit as the existing `audit_json` request input; it does not replace the worker response. The native Python verifier checks every resulting chain. Coverage includes fresh ordinary, integral, exponent and large clocks, a denied acknowledgment, and both successful and denied applications extending the retained integer-timestamp prefix. The prefix remains unchanged.

The receiving tests also reject changed payloads, timestamps, claimed hashes, previous hashes, sequence, ordering, removed events, malformed metadata and altered canonical bytes. They check append continuity and array-specific metadata binding.

Independent source review on base `728387a51fba7be34cf8344fe4f5cd9c7b12b6ad` by `chatgpt-31366547c1f5/device_state` found no blocker. It independently checked the primary upstream worker and `core.ts`, reconstructed the composed worker without changing timestamp normalization, and reviewed metadata binding and fail-closed verification. The three reviewed production files remain byte-identical in this current-main composition. The reviewer did not rerun tests; preservation of the newer, unrelated admission changes is covered by the complete source-tree comparison. Review SHA-256: `d1b04121bd660a299e45afa4310090d79ae6e854464f36b3ed625ff701b9cb9c`.

## Source and evidence

Receiving base: `09b96e31d2867af5b7a9738406d0431cf1010090`.

| Production file | SHA-256 |
|---|---|
| `web/airspace/src/audit.ts` | `80ba5c956cffa3ede818fc0eb3ed8e694962b9b2493f14062e09ac1c1e58e075` |
| `web/airspace/src/python.ts` | `8d7ee802aa3775867f4ffeb0195251f87e7d68203a5654c4a7b157807f6b7d0c` |
| `web/airspace/src/python-worker.ts` | `9980f9f7d39a139ce59901c593c5f40926efb0ad1615e4d2667db31ffd111536` |

Current baseline browser receipt SHA-256: `8e35b276430462e4c170b929f02c7956f316b91776f57d893e4681d5ac3e5839`.
Current candidate browser receipt SHA-256: `7f8e16c863774ce5e8d29c5cfc99017bd00df9ced173ed6417c21cc1eabea64c`.

The complete current receiving evidence, production distribution, and publication manifest are held under the existing estate custody convention at `/srv/hamon-estate/custody/chatgpt-31366547c1f5/towerops-audit-wire-current-09b96e31`. Earlier qualification at `b2b2fd19d7461ff5e99df4de81db78004fcffeed` remains separately preserved. This short summary accompanies the five source/test files; archived evidence is not duplicated in this change.

Run the standard source gates from `web/airspace`: `npm ci`, `npm test`, and `npm run build`. The existing interoperability cases require Python 3 on PATH. Displayed JavaScript numbers retain their existing precision; this change preserves verification of the original native hash inputs. This receiving record does not claim a hosted deployment.
