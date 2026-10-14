# Create an additional, identified Synthetic Explorer release

Owner: HAMON continuing team d3745ea0f44f / root. Forge independently receives the public CLI behavior before candidate exposure. Loom owns issue138's browser feature; Anvil owns its real-browser receiving. No descendants or scheduled continuation.

## Outcome
Install an explicitly identified eight-file Explorer composition as an additional foreground command. The existing towerops-explorer command and its c77e98e68d627c3ad75edc2d775ee8da018dbdcf release remain untouched. The first intended consumer is issue138 after its independent receiving and source publication.

Baseline repository Jacob-Met/TowerOps main 202782f29f3a0ed1411e67a7744f9e63f26926f1, tree90c81370fb3215943a8b64a4264f8e362a05d479. Existing install_explorer.py blob a732823616549e398dbd2ff5ad75d17b08442091 supplies unchanged filesystem helpers. Its complete body was read. The complete tree and sixteen open PR path lists were checked by Loom; root checked its three new paths against that retained ownership record. Fresh open upgrade issues0; launcher matches61/94/75 are unrelated native-world scopes. Old installer issue134 is closed. Fresh d55 identity confirmed hamon-thinkpad, jacob uid1000, passwdhome/home/jacob, clientd2b7a455; default selector still targets original c77 release and that is the only current namespace child. Read-only native inspection506721 exited0.

## Exact new source fence
- tools/stage_explorer.py
- tests/test_stage_explorer.py
- docs/EXPLORER_RELEASES.md
- unique qualification evidence under docs/qualification/explorer-releases-root-d3745/

Existing install_explorer.py, all eight runtime/guide files, README, workflows, existing source/evidence and installed versions remain unchanged. This utility uses the maintained sibling install_explorer.py via an explicit file-location import; shipping both tools together is required.

## Frozen public CLI and behavior
Python3.12+ on POSIX/Linux. No network, source execution, server startup, browser opening, PATH edit, selector replacement, autostart or deletion.

1. `python3 -B tools/stage_explorer.py inspect --source-dir ABS` reads exactly EXPLORER.md, explorer.py, replay_explain.py, scenarios.py, towerops.py, web/app.js, web/index.html, web/style.css. Source directory and selected file ancestors must be real directories owned by current uid or root; source directory itself and selected singly-linked regular files belong to current uid. No selected symlinks. Each file <=1,048,576 bytes and aggregate <=2,097,152 bytes. Additional source files are ignored and never copied. Capture bounded bytes with stable pre/post identities; errors exit2, no source execution or writes.
2. Canonical installed modes are0755 for explorer.py and0644 for the other seven. Content manifest is exactly an object with schema `towerops.explorer-content.v1` and files array sorted by path; each item has path, bytes, sha256 and mode integer. Manifest serialization uses Python json.dumps(ensure_ascii=True, sort_keys=True, indent=2) plus LF, encodedASCII. Digest is SHA256 of those exact bytes. This identifies content, not trust, a full repository revision, semantic correctness or authority. Inspect prints one JSON object with ok:true, digest and manifest, ending LF, exits0.
3. `python3 -B tools/stage_explorer.py install --source-dir ABS --prefix ABS --expect-digest LOWERCASE64HEX --receipt-new ABS` requires exact freshly captured content digest before any installation or receipt write. Caller obtains the reviewed digest from the release's source/receiving record; computing it alone is not qualification.
4. Prefix, prefix/bin and prefix/share must already exist as real current-user-owned directories. Existing share/towerops and share/towerops/explorer may be real owned directories; missing ones are created exclusively. The added release collection is share/towerops/explorer/releases. Its preexisting contents remain untouched.
5. New version path is share/towerops/explorer/releases/FULLDIGEST; unique command is prefix/bin/towerops-explorer-FIRST12DIGEST. Both must be absent, including dangling symlinks. A collision or repeated install exits2 and preserves existing entries. No reuse, repair, cleanup or overwrite is attempted. Prefix and selected source directories must be disjoint (neither ancestor of the other); receipt is a new file outside both.
6. Capture all source bytes before mutation. Write only the eight captured files plus wrapper `towerops-explorer`0755 and `installation.json`0644 in the new release. Wrapper is exactly "#!/bin/sh\\nexec /usr/bin/python3 -B " + shlex.quote(absolute explorer.py path) + ' serve "$@"\\n'. No -I, preserving the existing sibling imports. Manifest records content digest/manifest and wrapper identity; no invented commit qualification.
7. Read back the complete new release, verify every byte and canonical mode, recheck source identities, then create an absolute symlink to its wrapper using exclusive creation, last. Fsync new files and affected directories. Read back selector and complete release, recheck input custody. Existing default selector and older release contents are neither opened for writing nor traversed for copying.
8. Receipt-new is created0600 only after all initial source/path/collision/digest checks. It records ok, phase, content digest, release, selector, created paths, input identities and successful installed identities; it is updated through the open descriptor. Success stdout includes ok:true, digest, release, selector, receipt; exit0.
9. Filesystem or controlled refusal exits2 with JSON error on stderr. Partial writes, a late fsync/readback/source-change or receipt/console failure may leave new partial or fully selected state. Preserve it; report created paths and actual phase where possible. An already successful receipt can coexist with console failure; the error says selector may exist. No automatic retry/rollback. After a collision or partial failure inspect the original receipt and state before choosing a different reviewed release.
10. Standard user-owned local filesystem, with exclusive new names and stable read checks. It does not promise protection against an uncooperative same-account actor concurrently replacing ancestor paths. Concurrent use of this utility reserves a release by exclusive mkdir; it cannot silently replace the same version or alias.

## Receiving and adoption
Focused author tests exercise deterministic inspect, changed bytes, bad digest/no writes, symlink/bounds, collisions, quote-safe launcher, partial and late failure state, and prior installation preservation. Forge freezes an independent bounded temporary-prefix CLI course before candidate exposure. Subsequent native installation uses the qualified issue138 composition and published tool with exact source identity, then a small real installed-command receiving scope; it does not rerun the prior119 or feature browser course. Publish reviewed source, retain original evidence and direct existing Drive/Notion consumers to the actually installed command.

[skip ci] [skip actions]

skip-checks: true

