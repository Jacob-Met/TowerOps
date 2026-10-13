# Independent receiving: optional replay explanations

The replay --explain command reports the exact saved JSON fields that differ
from the deterministically reconstructed TowerOps synthetic scenario. Root
accepted the reviewed candidate after an original-first CLI course and source
review.

## Try the retained example

From the TowerOps repository root:

~~~sh
python3 explorer.py replay docs/qualification/explorer-replay-explain-anvil-d3745/independent/worked/saved-approved.json --explain
python3 explorer.py replay docs/qualification/explorer-replay-explain-anvil-d3745/independent/worked/changed-version.json --explain
~~~

The first command exits 0 and reports no differences. The second deliberately
exits 1 and reports one value difference at /after/version: the reconstructed
number is 2, and the saved number is 3. Exit 1 is the expected result for this
changed fixture, so a shell configured to stop on any nonzero status needs to
handle it. The exact received second result is
[worked/explanation.json](worked/explanation.json).

These are retained bytes from receiving, selected under explicit portable
destination names. The approved input originally had a filename containing a
space and Japanese characters. Its recorded original name remains unchanged in
the raw receipt. The changed input alters only after.version from the
approved fixture; nothing in the scenario engine or inputs is modified by
running the command.

Expected means the reconstructed scenario value; actual means the value in
the saved file. The record reports missing, unexpected, type and value
differences with JSON Pointer paths. Output is limited to 32 differences and
explicitly says when more were observed. A difference explains which field
does not match; it does not establish how the file came to differ. See the
project [EXPLORER.md](../../../../EXPLORER.md) for complete CLI and input limits.
TowerOps is a synthetic research simulation.

## What was actually received

| Course | Actual CLI commands | Recorded checks | Result |
| --- | ---: | ---: | --- |
| Original source | 5 | 19 | Accepted original behavior, including unsupported flag exit 2 |
| Reviewed candidate | 19 | 101 | All passed |

[freeze.json](freeze.json) was written before the candidate body was read or
executed. [receive.py](receive.py) is the exact frozen receiving driver.
[original-spec.json](original-spec.json) and [candidate-spec.json](candidate-spec.json)
bind source bytes and file modes. The complete
[original receipt](original-receipt.json) and
[candidate receipt](candidate-receipt.json) preserve command arguments, return
codes, stdout, stderr, literal actual/expected comparisons and source/control
identities. Their recorded absolute paths describe the receiving machines;
they are historical locations, not installation requirements.

The four shared ordinary export/replay commands have byte-identical stdout,
stderr and exit status across original and candidate. The candidate course
also exercised explicit correction after invalid input and real /dev/full
output failure. It preserved all source names, bytes and modes, and every
command preserved its inputs. The harness itself intentionally rewrote one
owned invalid fixture between commands to exercise recovery.

[stream-custody.json](stream-custody.json) identifies all 48 retained raw stream
files and confirms that each is exactly recoverable from the unchanged
receipt's inline text through strict UTF-8. Separate raw stream copies are not
included here. The /dev/full operation did not capture stdout; its empty
placeholder is explicitly labelled. Complete generated input sets can be
recreated by the exact driver, but only the practical worked pair is selected
as separate files in this publication.

[review.json](review.json) records source findings and evidence limits. This
root receiving course ran in the cloud Python environment. Anvil separately
qualified the same source on the estate ThinkPad. This record does not claim
a browser replay, live-service installation, model execution or validation of
real aircraft operations. No product run was repeated merely to assemble this
publication.
