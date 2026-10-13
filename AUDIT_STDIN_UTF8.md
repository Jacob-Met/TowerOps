# UTF-8 input for saved audit reviews

The audit CLI reads saved JSON as UTF-8 through either a named file or standard input. The same complete bytes produce the same chain and lifecycle review, including traces with non-ASCII names or recorded reasons.

```sh
python audit_replay.py trace.json
python audit_replay.py - < trace.json
```

The second example uses byte redirection in a POSIX shell or Windows `cmd.exe`. A caller can also pass the saved bytes directly through `subprocess.run(..., input=raw_bytes)`. Shells and upstream programs may transcode a text pipeline before the bytes reach Python; the CLI cannot restore bytes already changed upstream.

## Why the pipe encoding is explicit

Python's [standard-stream documentation](https://docs.python.org/3.14/library/sys.html#sys.stdin) distinguishes Windows console encoding from the locale encoding used for files and pipes. A process can also choose a standard-stream encoding through `PYTHONIOENCODING`. Those text settings must not reinterpret a saved UTF-8 audit document before its recorded hashes are checked.

For an ordinary binary-backed stdin stream, the command reads its binary buffer and decodes UTF-8 strictly, matching the existing file reader. Invalid UTF-8 returns the existing input error status 2 and no audit summary, even when the stream's text wrapper would replace or discard undecodable bytes.

Embedded callers that replace stdin with a text-only object such as `io.StringIO` may continue to supply already-decoded text. The caller remains responsible for that earlier decoding. The loader does not close or reconfigure either kind of supplied stream.

The audit hash and lifecycle checks are unchanged. A complete clean review still exits 0, recorded findings exit 1, and input/review/output errors exit 2. This change does not turn a changed digest into a clean record, normalize text, alter a saved file, or add an operational aviation guarantee.

## Focused verification

```sh
python -B -m unittest discover -s tests -p 'test_audit_replay_stdin_utf8.py' -v
```

The regressions compare actual named-file, default-stdin and explicit-stdin commands under UTF-8, cp1252 and ASCII stream settings. They retain clean Unicode histories, ASCII/empty/changed-digest controls, strict malformed-byte refusal and text-only embedded input. Native Windows receiving separately checks the ordinary inherited pipe settings with exact source and input bytes.
