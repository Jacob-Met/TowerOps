# Install another Explorer release without replacing a working command

Use `tools/stage_explorer.py` to give an explicitly reviewed Explorer composition
its own foreground command. The existing `towerops-explorer` launcher and older
versions remain available. This is useful when receiving a new browser feature
alongside a known working installation.

Keep `tools/stage_explorer.py` and the maintained sibling
`tools/install_explorer.py` together. The latter supplies shared filesystem
routines; its original create-only installer is not run. Linux, Python 3.12+
and `/usr/bin/python3` are required. No packages are downloaded.

## Inspect the exact composition

From the maintained repository, with a trusted source checkout or reviewed
eight-file projection:

```sh
python3 -B tools/stage_explorer.py inspect --source-dir /absolute/path/to/source
```

This reads only `EXPLORER.md`, `explorer.py`, `replay_explain.py`, `scenarios.py`,
`towerops.py`, `web/app.js`, `web/index.html` and `web/style.css`. It prints their
complete content manifest and its SHA256 digest. Other source files are ignored.
Nothing is copied or executed by inspection.

The digest identifies these eight contents and installed modes. It does not
establish trust, qualify their behavior or identify a complete Git checkout.
Use the exact digest recorded by the source review and receiving for the release
you intend to install. If it differs from this inspection, resolve that mismatch
before installation.

## Create a separate command

Use an absolute owned prefix whose `bin` and `share` directories already exist,
and a new receipt outside both that prefix and the source directory:

```sh
python3 -B tools/stage_explorer.py install \
  --source-dir /absolute/path/to/source \
  --prefix /home/jacob/.local \
  --expect-digest FULL_REVIEWED_64_CHARACTER_DIGEST \
  --receipt-new /home/jacob/hamon/receiving/new-release-install.json
```

Replace the digest and receipt name with the reviewed release's values. The tool
requires the fresh source digest to match before writing the receipt or an
installation entry. A new release lives under
`PREFIX/share/towerops/explorer/releases/FULL_DIGEST/`. Its separate command is
`PREFIX/bin/towerops-explorer-FIRST_12_DIGEST_CHARACTERS`.

On success, the printed JSON gives the exact command, release and receipt paths.
Run that command with `--port 0`, then open its printed loopback address. The
existing `serve` arguments are forwarded literally. Ctrl+C closes the foreground
server. Installation itself does not start a server or browser, modify PATH,
replace a command, add a service or arrange startup. You can continue using the
old command at any time; running servers are not redirected to another version.

The new release contains the eight captured source files, a shell launcher and
`installation.json`. `explorer.py` and the launcher are executable; the remaining
files are mode0644. The receipt is mode0600. Every installed byte and mode is
read back, and the source identities are checked again before and after the
absolute command symlink is created last. The release manifest retains the full
digest, original content manifest and actual wrapper identity.

## Refusals and retained state

A wrong digest, selected symlink, nonregular or multiply linked input, unexpected
owner, overlapping source/prefix, existing receipt, existing version or occupied
command refuses. A dangling command link also counts as occupied. Selected files
are bounded to 1MiB each and 2MiB in total. All selected source ancestors must be
real directories; the prefix, source root and selected files must belong to the
current user. Root-owned ancestors are allowed.

Repeated installation does not repair, replace or reuse an existing release.
Inspect its receipt and files instead. The full digest separates content, while
the short command name is only a convenience; a short-name collision refuses.

An error after creation begins may leave a partial release. A late failure can
leave a complete command even though the installer exits2. The new receipt and
JSON error retain the phase and created paths when the filesystem permits it.
A successful receipt can also remain after a console-output failure; the error
then explicitly says the selector may exist. Preserve and inspect that state.
The tool performs no cleanup, deletion, rollback or automatic retry.

Exclusive creation prevents this utility from silently replacing another
release or command. Stable reads detect source changes during staging. This is
a user-owned local workflow, not protection against another same-account process
concurrently replacing ancestor directories. Do not modify selected sources or
installation paths during the operation.

## Content identity and verification

The content manifest is `{"schema":"towerops.explorer-content.v1","files":[...]}`.
Rows are sorted by path and contain `path`, `bytes`, `sha256` and integer `mode`.
Its exact canonical bytes use Python `json.dumps` with `ensure_ascii=True`,
`sort_keys=True`, `indent=2`, followed by one LF and ASCII encoding. SHA256 of
those bytes is the full content digest. Modes are0755 for `explorer.py` and0644
for the other seven source files, independent of their original source modes.

Run focused development tests with:

```sh
python3 -B tests/test_stage_explorer.py
```

These tests include an explicitly tiny launcher fixture, coexistence, collisions,
source changes and retained partial/late failures. They are separate from actual
Explorer browser receiving and actual installed-command receiving. Installation
does not make any new simulation, operational or aviation safety claim.
