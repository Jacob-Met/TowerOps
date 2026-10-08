# Review, save and reopen the native decision trail

Airspace Lab can review its recorded decision sequence, download the original
native JSON, and reopen a saved trace. The view distinguishes a broken hash
chain from a hash-valid history with decision-sequence issues. It displays each
advisory's screening, approval, readback, actuations and world links, followed by
recorded rejections. Opening a trace does not install its aircraft or history
into the live simulation.

## Current receiving composition

This contribution is based on main
`5ae808749c8624d9e267d23997beaa3ae5220dbc`, tree
`356e66716c8953a3c2aac8a23790ce6eeaba20d0`. Its 12 source/integration paths
produce tree `e5e2537982b09aee9a5ab4ffa23d7b913ef1b9c4` before qualification
documents: 130 unchanged parent leaves, six replacements, six additions and no
deletions. All 142 source leaves were verified before and after the current
frontend/build/browser gates. No applicable `AGENTS.md` or `CONTINUE.md` occurs
in this pinned repository tree.

PR #38 merged during receiving and changed the audit transport. The current
Worker emits Python's canonical event bodies in `audit_canonical`; the current
client registers them, and the current `AuditLog` uses them to verify the
displayed events. Reusing the earlier Worker overlay would remove this metadata
and break the current browser's Verify chain operation.

The final Worker starts from PR #38's exact blob
`688f4b0ba15fb86f89de07b39640603e4c860760`. It preserves the `canonical_bytes`
import, `browser_audit` helper, and success and rejection return paths. Only the
existing early `review_trace` branch, optional replay loader and request hook
are added. Removing those additions reproduces the current Worker byte-for-byte.
The current `python.ts` and `audit.ts` are unchanged parent inputs. PR #36's
numeric admission checks, native producer, replay algorithm, canonical
serializer, dependency manifests and lockfiles are also preserved.

The original source on `728387a51fba7be34cf8344fe4f5cd9c7b12b6ad` and the
subsequent receiving packet on `09b96e31d2867af5b7a9738406d0431cf1010090` remain
frozen. Their complete evidence and earlier publication metadata are retained
inside this packet. Their results are identified by their actual source pins.

## Native integration and review boundaries

`decision_trace.review_trace(raw)` parses the original text in Python and calls
the existing `audit_replay.replay_audit` unchanged. The Worker returns this
read-only projection before reading plan/apply inputs. Keeping the raw text
avoids JavaScript's conversion of native integral floats to integer JSON before
Python verifies their canonical hashes.

The UI and styles live in `decision-trace.ts` and `decision-trace.css`, with
small hooks in the existing panel and `main.ts`. Review uses the existing client
and busy guard and requires paused traffic. It retains the world, clock, policy,
proposal, pending approval and live audit. File tickets prevent an older read
from replacing a newer selection. Labels are rendered as literal text.

The optional replay modules load only when requested. An unavailable replay
source does not disable native planning, and a later explicit review can retry.
Both modules are included in existing Python packaging and Airspace workflow
path arrays. The maintained browser acceptance helper runs after the existing
capture and is included in those path arrays. Existing jobs, permissions and
commands are retained; no new product dependency or test framework is added.

## Completed qualification

The current receiving gates used native macOS, Python 3.13.7, Node 26.3.0,
Python Playwright 1.63.0, Chrome 154.0.8037.98, the unchanged npm lock, and the
actual built Worker with locally packaged Pyodide 0.27.7.

| Qualification stage | Observed result |
| --- | --- |
| Current full frontend suite, including PR #38's 21 audit-wire cases | 97 passed in eight files |
| Current Python packaging, TypeScript check and Vite build | Passed |
| Current maintained Chrome/Pyodide decision-trail controls | 11 passed |
| Native producer/replay/adapter qualification carried from identical inputs on `09b96e31` | 108 native cases, Ruff and four reference scenarios passed; no redundant native rerun |
| Original author source | 78 native, 51 frontend and 11 browser controls passed |
| Independent native receiving on original and `09b96e31` producer pins | Same six cases passed normally and under `-O` on each pin |
| Independent browser receiving on the frozen original build | Two saved-file controls passed |

The current browser run covers real planning, approval and readback, native
review, an exact download checked with the existing CLI, and reopening while a
different approval is pending. It checks the visible Verify chain action on the
native application flow, retains the live audit through imported history, and
checks later live application. Other controls exercise rehashed missing
approval, world and ordering issues; tampered hashes; malformed files; both
input bounds; literal hostile labels; a 390-pixel layout; native demo documents;
and an actual optional-module fetch failure followed by planning and retry.
The helper now records the current audit consumer and canonical serializer
alongside its Worker/client inputs. No fake Python browser runtime is used.

The maintained command locates the JavaScript driver inside the already existing
Python Playwright CI dependency. That package exports `chromium` and declares
Node 20 or later, matching the existing CI Node 20 setup:

```sh
TOWEROPS_PLAYWRIGHT_JS="$(python -c 'from pathlib import Path; import playwright; print(Path(playwright.__file__).parent / "driver" / "package" / "index.mjs")')"
node tools/verify_decision_trace.mjs --playwright "$TOWEROPS_PLAYWRIGHT_JS" --output "$RUNNER_TEMP/towerops-decision-trace-browser"
```

Native qualification appended the installed Chrome executable with `--chrome`
because the default Playwright Chromium revision was absent from that native
cache. The maintained CI command omits this override after its existing Chromium
installation. These are native receiving results; hosted CI, merging and
deployment are separate observations.

## Evidence and interpretation

`receipt.json` binds the final source, preserved parent inputs, current gates
and historical results. `evidence.tar.gz` contains the previous evidence archive
unchanged, its original publication metadata, and the current receiving logs,
source maps, exact Worker diff, commands, fixtures and screenshots. Each archive
stage supplies a member manifest. Initial author assertion/lint failures,
corrections and earlier UI captures remain preserved in their original stage.

Browser review accepts an event list or a native demo object with `audit_events`,
up to 2 MiB of UTF-8 JSON and 5,000 events. Downloads retain the full native text;
larger files can use `python audit_replay.py file.json`. The independent receiver
is a standalone command requiring an explicit source root and remains inside
the evidence packet, outside automatic pytest discovery.

Review retains the existing replay's meaning: first screening, approval and
readback associations, recorded actuations and available world links. Unknown
kinds and omitted optional world hashes keep their native behavior. Replay does
not rerun separation policy, reconstruct motion or authenticate approval.
