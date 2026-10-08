# Python-compatible aircraft identifier ordering

[Source claim #67](https://github.com/Jacob-Met/TowerOps/issues/67) was opened before implementation. This packet records the original failures, the one-file production correction and native verification. Independent receiving and normal hosted gates remain prerequisites to integration.

## Observable defect and correction

The TypeScript `worldHash` and `conflictingAircraft` functions sorted IDs with `localeCompare`. Python orders strings by Unicode code point. With the maintained two-aircraft fixture and only callsigns changed, the admitted pairs `A-1 / A_1`, `-A / _A` and `B / _A` produced different world hashes and planner targets. Each implementation refused the other's advisory, and actual native `ControlRoom.apply` rejected the TypeScript proposal with `world_hash_mismatch`. Ordinary `A / B` and `A1 / A2` controls succeeded.

One private comparator in `web/airspace/src/core.ts` now walks Unicode code points and uses that same order at both sort sites. It preserves prefixes, distinct combining representations and astral/BMP order without consulting locale. No native Python, admission, policy, motion or UI call path changes.

**Scope:** the current production interface delegates planning and application directly to Python. These results qualify the maintained TypeScript API and its cross-language contract; no failure of the current direct-Python interface is claimed. The pinned Pyodide checks execute that real runtime in Node, not a browser interface.

## Source identities

- Original source: `89529c5459b1c3d52448e197de2b2f7fe8b6d128`, tree `03fec48eb2a60ff34084051d55ce4c5b446c7bb1`.
- Incoming main: `a11c30497896455de3e74c21e530787dc7982bca`, tree `b6435584e26bf52c281be4878d9dd1c875caabaa`.
- Incoming work adds five verification documents. All production, test and build inputs are unchanged; the native branch fast-forwarded while preserving the candidate.
- Canonical candidate core blob: `acab00c3e8cb6498e3b5352333f2dfe767edb907`, SHA-256 `01c351be73c9f404aeb6a30d80ab6796ec72a0b24fade725ac853104c89f940f`.
- The native Windows core has CRLF line endings and SHA-256 `c240b53b69075daab91f53889e6ceec0d3de2feb4583eaf9cbfd897ba4b7d243`. The Git clean conversion to canonical LF was checked byte-for-byte; all other bytes agree. `qualification.json` binds both identities for every changed source/test file.
- Unchanged native oracle: `towerops.py` Git blob `3f541e5f0f3a05dac9d12c96e75d3d69ef3377d1`. The checked-in fixture records its producer and exact source commit.

## Verification

| Check | Original source | Candidate |
| --- | --- | --- |
| Full Vitest suite, exact configured native Python | 229 pass, 9 new regressions fail; 238 total | 238 pass, 0 fail, 0 pending |
| Five native CPython cross-language transactions | 2 ordinary controls succeed, 3 punctuation cases fail | 5/5 equal hashes/targets, both-way admission and successful application |
| Same five transactions in pinned Pyodide | Same original failures | 5/5 successful |
| TypeScript and Vite production build | Not claimed for the original source in this packet | Exit 0; 16 output files hashed |

The native suite and build each pin all 1,092 source/test files before and after execution and show no source mutation. Toolchain: Node 24.21.0, locked TypeScript 5.7.3, native CPython 3.13.15, pinned Pyodide 0.27.7 / CPython 3.12.7.

The 12 new tests use 11 native-produced vectors plus a control that makes `localeCompare` throw. They cover ordinary IDs, admitted punctuation, prefixes, all 38 admitted single characters, case-sensitive API inputs, accented and combining strings, and astral/BMP code points. They compare hashes, conflict order and complete two-aircraft proposals; check native proposal admission; preserve inputs; and repeat identity/order checks with reversed input.

Two receiver problems remain in the evidence separately from the product defect. Initial Windows text-stdin decoding produced a UnicodeEncodeError; the receiver was corrected to read JSON from binary stdin. The initial full suite also could not launch the default `python3` for 13 existing tests. Using the project's supported `TOWEROPS_PYTHON` override and explicit UTF-8 stdio resolved those launch failures without changing tests or machine-wide settings. Original scripts, logs and results are retained.

## Evidence and replay

- `qualification.json`: source bindings, native baseline/candidate transactions, gate summaries, incoming composition and scope limits.
- `native-receiving.zip`: 47 individually hashed members, 284,849 bytes, SHA-256 `906793451f534f3925aaede87bca4fac992069ff20bda610c25fc1855d084d24`.
- `archive-manifest.json`: every archive member's exact path, length and SHA-256. The archive was reopened, CRC-tested, and every member read and compared.

The archive includes full Vitest JSON/logs, all source pins, build output hashes, original and candidate compiled modules, native receiver programs, the original source claim and retained failures. It contains only this contribution's explicitly selected private receiver files; no general Git metadata.

For the maintained regression suite in a fresh source checkout:

```sh
cd web/airspace
npm ci
npm test
npm run build
```

On Windows without `python3` on PATH, set the existing `TOWEROPS_PYTHON` override to the installed Python executable and `PYTHONIOENCODING=utf-8` for that process. The archived native scripts record the exact Windows tool paths used. Their paths are relative to a checkout's private `.git` directory; replay into an isolated checkout. Original baseline programs must run on the pinned original source, and candidate programs on the proposed source. Keep the archived receipt files immutable when replaying.
