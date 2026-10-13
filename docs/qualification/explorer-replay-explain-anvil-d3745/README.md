# Explorer replay explanations — author qualification

This change adds `python3 explorer.py replay FILE --explain` so a caller can see the literal fields that differ from the local deterministic reproduction. The existing replay command and browser endpoint retain their response shape and behavior.

## Use the maintained command

Run these commands from the repository root at the published source revision:

```sh
python3 explorer.py run approved > approved.json
python3 explorer.py replay approved.json --explain
```

A matching export exits 0 and includes an empty `differences` array. A differing, admitted export exits 1 and includes up to 32 ordered rows. Each row identifies an RFC 6901 JSON pointer, a `missing`, `unexpected`, `type`, or `value` difference, and explicit expected/actual presence, JSON type, and literal value. The expected value is the local reproduction; the actual value is the supplied export. The report is a deterministic data comparison, without inferred cause, signature, provenance, or real-world authority.

The original command remains available:

```sh
python3 explorer.py replay approved.json
```

It has no new report fields. `EXPLORER.md` documents the public format and limits.

## Admission and output behavior

The explanation path reads at most 262,145 bytes from an admitted regular-file descriptor and refuses input larger than 262,144 bytes. It requires UTF-8 and finite JSON numbers, including refusal of overflowing floating-point literals. Malformed, excessively deep, invalid-request, or unavailable inputs exit 2 before a success JSON report. The default replay decoding and read path are unchanged.

Object keys are visited in sorted order and array indices in ascending order. A type change emits one row for that subtree. Missing values and present null values remain distinct. Finite numerically equal integers and floats retain the existing equivalence rule; booleans remain a separate JSON type. The 33rd difference sets `differences_truncated` while retaining the first 32 rows; the report does not claim a total difference count. Unicode strings and complete literal values are retained.

The complete response is serialized before output. A detected stdout write or flush failure exits 2. A partial write cannot be rolled back. The command does not write the input or create an output file, and makes no concurrent-writer or adversarial-directory guarantee.

## Exact author execution

The author source base is `8a87ad1331d7e7100367dde583d59560836f9eb8`, whose tree is `ffacbb9ace1a360d0aeca2bdb33b70e0c0422418`. The four changed/new source leaves are explicitly listed in the source authority; `scenarios.py` and `towerops.py` are unchanged runtime dependencies. The candidate was unpublished when executed.

On the verified `hamon-thinkpad` account, Python 3.14.4 ran an original-first course before the new helper existed. Four actual CLI commands demonstrated an approved export, a matching replay, a changed `after.version` with the original generic mismatch reply, and refusal of the then-unsupported `--explain` flag. All original source and donor bytes/modes remained unchanged. The exact original receipt and eight streams are retained under `original/`.

The frozen candidate then passed these focused maintained commands:

```sh
python3 -B -m unittest discover -s tests -p test_replay_explain.py -v
python3 -O -B -m unittest discover -s tests -p test_replay_explain.py -v
```

Both runs passed all 10 methods, with no skips, warnings, or errors. The optimized run propagates `-O` into its actual CLI children. These methods cover typed literal differences, presence and pointer escaping, deterministic order and truncation, detached reports, unchanged default reply bytes, regular-file and actual byte-bound admission, malformed/deep/nonfinite/UTF-8 refusals, and controlled stdout failure. The `/dev/full` case ran on Linux; it is explicitly skipped on systems without that device. The complete normal and optimized stdout/stderr files and receipt are retained under `author/candidate-v1/`.

The author supervisor PID was 3958669 and completed with exit 0. All ten candidate source inputs and eight baseline source inputs were unchanged. `source-spec-complete-six.json` binds the six source bodies supplied to the separate independent CLI receiver; it also retains the original ten-input native author inventory. The smaller first source spec is preserved as history.

The executed staging scripts contain the exact native paths used for these courses. They are evidence of those executions, not portable installation commands. Use the maintained test commands above from a source checkout for a new qualification run. No browser, service, model, provider, or live aviation workflow was invoked by the explanation author course.

## Independent receiving and publication

Independent CLI receiving is a separate root-owned course whose criteria and executable receiver were frozen before candidate exposure. Its original control and eventual candidate result must remain separately attributed from the author 10 + 10 maintained methods. Publication will retain that original descriptor and its raw streams alongside this author evidence. The earlier replay-selection browser result is a different feature and is published separately.

The source selection is exactly four leaves: `replay_explain.py`, `explorer.py`, `tests/test_replay_explain.py`, and `EXPLORER.md`. The default Explorer source span is mechanically unchanged after removing only the optional flag and its lazy dispatch. No browser asset, engine, scenario, workflow, or external owner file is included in this source change. The maintained estate publication-layout validator admits explicit source/support/evidence records before Git tree, commit, or ref creation. GitHub Actions are not part of this qualification.
