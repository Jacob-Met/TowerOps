# Install the reviewed Synthetic Explorer on the ThinkPad

This fixed adoption provides `towerops-explorer` in Jacob's existing ThinkPad PATH. It launches the reviewed foreground, loopback-only Synthetic Explorer. The saved-file replay and explicit **Explain this mismatch** controls use the already accepted runtime; this installer does not change their logic.

## Exact source and destination

The command is restricted to Linux host `hamon-thinkpad`, account `jacob`, uid `1000`, home `/home/jacob`, with Python 3.12 or newer. It requires the existing owned ordinary directories `/home/jacob/.local`, `.local/bin` and `.local/share`. No sudo, service manager, network download or dependency installation is involved.

The accepted source is the eight-file primary projection at [c77e98e68d627c3ad75edc2d775ee8da018dbdcf](https://github.com/Jacob-Met/TowerOps/commit/c77e98e68d627c3ad75edc2d775ee8da018dbdcf), adopted through PR133. Exact copies are retained in [accepted-source](qualification/explorer-install-anvil-d3745/accepted-source/), so later changes to current source do not silently change this version.

| File | Bytes | SHA-256 | Installed mode |
| --- | ---: | --- | --- |
| `EXPLORER.md` | 9,288 | `135c46bab3ef61c90d88cf6599f129c36f446a164214a37099b0dba71ad399e3` | `0644` |
| `explorer.py` | 7,604 | `0d2d9ce308bb5a1648ae03fb3230d5f6beed629314c2a7a76b0bab187392c843` | `0755` |
| `replay_explain.py` | 5,432 | `bd717d3bd86f238e3f44c2710b56f88d142046cf02ec9049fd337a9a7db9fc7b` | `0644` |
| `scenarios.py` | 5,989 | `bda24452b41a9ec8b6a7a0865b2fb95217a4a304ecf17b1c5d72b2dab65f6a52` | `0644` |
| `towerops.py` | 19,684 | `b8bb4a15c70b0137e1c47aa614e6ed1b6f3cae096af9fb0c8810f3d900a48f70` | `0644` |
| `web/app.js` | 9,430 | `9e3d38e3dec59d0b4725771770c05a89afa0190fec8438cd61921b6d3b846739` | `0644` |
| `web/index.html` | 3,934 | `d616416300f809bce0b843b792a65f15f560bb8c543f49936744dfd95b46a0b1` | `0644` |
| `web/style.css` | 2,566 | `b0ee12c04e0b0bb4b7bb1e9ce0dc7dbc9e874966d9e326784f3728e42dc023c9` | `0644` |

The version directory is:

```text
/home/jacob/.local/share/towerops/explorer/c77e98e68d627c3ad75edc2d775ee8da018dbdcf/
```

It contains those eight regular source/guide files, the `web/` directory, a `towerops-explorer` shell wrapper and `installation.json`: ten regular files total. The manifest records the accepted source, each source file's byte/hash/mode identity, the wrapper hash, interpreter and installation time. A new symlink `/home/jacob/.local/bin/towerops-explorer` selects the versioned wrapper.

## One explicit installation

From a checkout containing the installer and accepted-source support, on the designated host:

```sh
python3 -B tools/install_explorer.py \
  --source-dir "$PWD/docs/qualification/explorer-install-anvil-d3745/accepted-source" \
  --receipt-new "$PWD/explorer-install-receipt.json"
```

Use an absolute, new receipt path in an existing owned directory outside `/home/jacob/.local`. Source files must be owned, singly linked regular files with the exact fixed bytes. Symlink ancestors and linked/nonregular source entries are refused. The installer captures the admitted bytes before creating installation paths and checks their identities again before and after publishing the selector.

Both the selector and the **complete `share/towerops` namespace must be absent**, including dangling symlinks. An occupied namespace is preserved even if it contains an earlier working version or appears empty. A repeat returns status 2; this command does not upgrade, repair, automatically reuse or remove an installation.

The installer reserves the receipt first, exclusively creates the new namespace/version, writes and verifies the files, then publishes the selector last. Every new directory entry, file and selector is synchronized through the relevant file or directory descriptor. This ordering improves durability; it is not a tested power-loss transaction and assumes stable owned local directories. There is no shared Tsuka lock, command replacement or PATH configuration edit.

## Launch and stop explicitly

After successful adoption:

```sh
towerops-explorer --help
towerops-explorer --port 8765
```

Open the printed loopback address. Choose another unused port if necessary. `--port 0` asks the existing server for an available ephemeral port and prints the actual address. **Ctrl+C** stops the foreground server. Nothing starts during installation, at login or in the background. The launcher does not open a browser.

The wrapper executes `/usr/bin/python3 -B <absolute versioned explorer.py> serve "$@"`. It forwards arguments to the existing **serve** subcommand and keeps imports and static assets relative to the same versioned source. It is not a replacement for the separate run/replay terminal commands. Python `-B` avoids writing bytecode into the installed version.

Try the exact saved C fixture and usage instructions in the [published browser receiving guide](https://github.com/Jacob-Met/TowerOps/blob/c77e98e68d627c3ad75edc2d775ee8da018dbdcf/docs/qualification/explorer-browser-explain-root-d3745/independent/README.md), or use an existing synthetic Explorer export. Select it under Replay exported JSON; on MISMATCH, choose **Explain this mismatch**. Expected values describe the local synthetic reproduction and Actual values describe the saved file. The typed literal differences, absence markers and 32-row limit do not infer a cause, authenticate a file or establish operational authority.

## Read the receipt before deciding what happened

Status **0** means the installation, final on-disk receipt and stdout report were delivered. The stdout JSON names the accepted source, release, selector and receipt. The receipt records source and installed identities, created paths, the selected wrapper and the last phase.

Status **2** may be an argument/admission refusal or a later file, synchronization, receipt or stdout failure. Inspect the explicit receipt path, namespace and selector:

- An admission refusal creates no installation namespace. A missing or altered offered source can be explicitly corrected and retried while the receipt, namespace and selector are still absent.
- A later failure can leave a partial receipt or version. Created paths are retained for inspection; changing only the receipt name does not make an occupied namespace replaceable.
- A failure after selector publication can leave a usable command. In particular, stdout write/flush failure returns 2 while the final on-disk receipt can still say `ok: true`. The error report identifies this console phase. A failed final receipt can instead leave a selector with an incomplete or false receipt. The exit status alone does not establish rollback.
- A competing selector is never replaced. Its presence causes refusal and leaves the completed private version for inspection.

No automatic rollback, cleanup or retry occurs. An error-phase label is diagnostic; use the receipt's `ok` field and actual retained paths together. This guide does not authorize deleting an occupied command, namespace or receipt. Any later repair or version change needs an explicit adoption decision.

## Focused verification

```sh
python3 -B -m unittest discover -s tests -p 'test_explorer_install.py' -v
python3 -B -O -m unittest discover -s tests -p 'test_explorer_install.py' -v
```

The maintained methods use temporary owned prefixes and copies of the exact source. They cover source admission/correction, missing/linked/hardlinked/FIFO inputs, occupied command and namespace variants, receipt placement, ancestry, source changes after capture, namespace synchronization failure, a real bounded-file-size partial write, competing selector creation, a late receipt failure, real `/dev/full` stdout failure, host/argument refusals, repeat preservation and an actual installed-style wrapper `--help` invocation from an unrelated directory with spaces.

Normal and optimized test processes propagate their optimization setting into explicit temporary-layout main subprocesses. The installed-style wrapper itself deliberately uses Python `-B` only. Author tests do not install into the real PATH or replay the earlier browser qualification. The separate [installed-use receiving record](qualification/explorer-install-anvil-d3745/) records actual PATH launch, exact relocated assets, accepted HTTP responses and explicit owned-server shutdown when those results are available.
