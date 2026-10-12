# Complete requests before explorer execution

The loopback synthetic explorer now refuses incomplete or ambiguously framed
HTTP requests before entering the existing scenario or replay functions. An
idle request body receives a timeout response instead of retaining its handler
indefinitely.

## Run the explorer

The application still uses only the Python standard library:

```sh
python explorer.py serve --port 8765
```

Open `http://127.0.0.1:8765` and use the existing Run, Export and Replay controls.
The browser supplies the supported request framing automatically. No new
configuration or dependency is needed.

## Request behavior

Both `/api/run` and `/api/replay` require one `Content-Length` field containing
ASCII decimal digits, with ordinary surrounding spaces/tabs and leading zeros
permitted. The admitted size remains 1 through 262,144 bytes. The server
compares decimal text before conversion, so very long leading-zero spellings
retain their numeric meaning and oversized digit strings do not reach Python's
integer-string conversion limit.

| Request condition | Response |
| --- | --- |
| No `Content-Length` | 411 |
| Signed, underscored, fractional or otherwise malformed length | 400 |
| Repeated length fields, even when equal | 400 |
| Any `Transfer-Encoding`, including an empty field | 400 |
| Zero length or more than 262,144 bytes | 413 |
| End of input before the declared body is complete | 400 |
| Five seconds of idle waiting for body bytes | 408 |
| Complete admitted body | Existing JSON and scenario/replay validation |

Length and transfer-encoding refusal happen before reading the body. Short EOF
and idle refusal happen before parsing JSON or dispatching a consumer. The
socket's prior timeout is restored after the body read. This is an idle body
timeout, not a total request deadline or a timeout for request headers.

The existing Host/Origin checks, static assets, JSON validation and deterministic
simulation/replay implementation retain their original behavior. The explorer
remains a local synthetic research fixture.

## Reproduced original failure

The baseline is commit
`a86b661ee66c19c2617ed9ee75e193ed6d0f21a8`, tree
`e2fb7f4b0987ac23f3bbac46c271346b446564ee`. Its `explorer.py` blob is
`d19e5bf1bd2991b076d7166fc2280b7f1d312d9a`.

Real raw-socket requests containing complete JSON but fewer bytes than their
declared length returned HTTP 200 and entered the real scenario or replay
consumer. Duplicate lengths and unsupported transfer encoding also reached
those consumers. An idle incomplete body produced no response within the
independent receiver's 6.5-second observation window; after write-side EOF for
cleanup, it still executed the scenario and returned 200.

## Verification

The new maintained socket regressions and the existing explorer tests run with:

```sh
python -m unittest tests.test_explorer_requests test_explorer -v
```

All 19 test methods pass: 11 new request-boundary methods and eight unchanged
explorer methods. The tests use real loopback sockets and the original
simulation/replay functions. Refusal tests also observe that neither consumer
was called. The maintained idle tests shorten only the timeout constant to keep
the suite fast; independent receiving uses the ordinary five-second value.

A separate worker froze and executed 29 HTTP cases against the original before
viewing the implementation. The baseline passed 17 and failed 12. The identical
harness passes all 29 against the repaired implementation, with no server
exceptions. The ordinary idle refusal arrived after 5.0056 seconds. Exact-length
run/replay, fragmented body writes, leading-zero lengths and origin controls
remain compatible.

The same reviewed source and unmodified browser assets were copied to an
isolated Windows consumer. Python 3.14.3 and Chrome 154 passed all 14 receiving
checks. After malformed run/replay requests and the ordinary five-second idle
timeout, no extra consumer ran, the displayed five-event audit/result remained
unchanged, and a second actual export matched the first byte-for-byte. Ordinary
replay, a subsequent missing-acknowledgement run and replay of that rejected
export remained usable. No page or server error was observed.

The reviewed production file is 7,141 bytes, SHA-256
`da950f18a267a36e018649e2b29df19ae34f3679358227ea5afbc69bb7a42c75`, Git blob
`897ddf219cb5be863ff89318d1bf8b22a08e3e2f`. The independent HTTP harness SHA-256 is
`7ab8518104673410aab17389444c2e8b368ae03b6cadf8b5e8f7539afed51f84`.
The source worker authored the repair; the separate runtime worker performed
the frozen receiving, reviewed the implementation and exercised the Windows
consumer. Both original negative results and the completed receiving packet
are retained with their source hashes.

The final full-repository run on Python 3.12.14 passes **192 tests in 8.07 seconds**
with the repository's pinned pytest 8.3.5. Pinned Ruff 0.16.10 reports **All checks
passed** for `python -m ruff check .`. Their first run found two inherited formatting issues
in `tests/test_audit_world_linkage.py`, alongside one in the new regression.
The accompanying test-only cleanup wraps imports and combines equivalent
context managers in their original order. It changes no assertions, inputs or
audit implementation, and was separately reviewed.

## Publication

GitHub Actions is intentionally not used for this increment. Both current
workflow definitions were inspected; their automatic events are `push` and
`pull_request`. Publication commits retain GitHub's documented `[skip actions]`
instruction. Existing workflows and repository rules remain unchanged. Local
qualification is reported as local qualification, not a hosted CI result.
