# Hosted receiving and integration checkpoint

The [root hosted review](HOSTED_PR_REVIEW.md) accepts the exact comparison
module `2042f344a71cdbcebbe97ad7e31fdcdb359be3282a8e4427b728cc1afe6d76c0`
after 27 frozen API cases and 22 actual CLI processes. Ordinary pytest ran
171 tests successfully; lint and adapter jobs also passed.

The accepted source head is `a75888c42338ae0ffe165aa522a01c3e27e3d1d2`.
[PR run 37820535313](https://github.com/Jacob-Met/TowerOps/actions/runs/37820535313)
tested synthetic checkout `5d93029ebfed871b6b0b56fbe9a19086fd83896c`.
[Push run 37820254304](https://github.com/Jacob-Met/TowerOps/actions/runs/37820254304)
also passed. A synthetic PR checkout is not an actual integration commit.

The three original root acceptance leaves are preserved byte-for-byte.
[HOSTED_PR_RAW_ARCHIVE.json](HOSTED_PR_RAW_ARCHIVE.json) retains the exact
base64(zlib(JSON UTF-8)) envelope from the actual test log. Its inner archive
contains 47 regular-file outputs, including the same RECEIVING.json as
[HOSTED_PR_RECEIVING.json](HOSTED_PR_RECEIVING.json). No link or FIFO is included.
Both root and source owner independently verified the compressed/uncompressed
hashes and every retained file. [The custody record](HOSTED_PR_CUSTODY.json)
and [source-owner verification](HOSTED_PR_ARCHIVE_VERIFIED.json) retain details.

This additive evidence successor composes main
`a11c30497896455de3e74c21e530787dc7982bca`
(tree `b6435584e26bf52c281be4878d9dd1c875caabaa`), preserving its five new,
unrelated scenario verification files. All 35 previous contribution leaves
are retained exactly, including every product, test, frozen oracle and
historical failure record. Six new evidence leaves are added; no runtime,
workflow, dependency or product behavior changes.

Ordinary successor CI and actual merged-source receiving remain separately
observable gates. This checkpoint does not claim that a future merge has
already happened. The final PR closure records the actual integration pin
and merged-source workflow, keeping it distinct from this accepted synthetic
checkout. No Mac/Windows/LA7 installation or live planning effect is implied.
