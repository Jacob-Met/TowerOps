# Reset controls on current TowerOps main

Reset must restore the live playback rate and displayed policy values together with the world. On the pinned current main, tuning the speed or policy ranges and pressing Reset restores the sliders but leaves stale policy labels; actual traffic also retains the previous speed.

This candidate composes the previously reviewed Reset function onto main `a704b2c9f957a5f65169fa7eeb5e98f34c5a9d2c`, tree `5451d7fe56438137d3e162ccfcaabc5e064ab236`. The newer encounter and decision-trail integration is retained.

## Source change

The production change is limited to `web/airspace/src/main.ts::resetWorld`. It assigns the default live rate, derives reset range values from the restored policy/rate, and updates the three policy readouts using the existing formatting.

Current main's original Reset function is byte-identical to the earlier accepted baseline. The exact reviewed function transfers without adaptation. Every byte outside the function and all 16 inherited statements left intact remain identical and ordered. All 164 current-main file contents/modes are verified during each receiving phase; only the declared production source changes. The unchanged optional browser receiver is added at `tools/verify_airspace_reset.cjs`.

| Source pin | SHA-256 |
| --- | --- |
| Current baseline main.ts | `347cca82b84ea49c55efd468db995820d55d32249543aa69cc744797c4f3fc80` |
| Composed main.ts | `2ece5b27987b2fc4868dcf27c068ba8aabc53e77dbbae97226cc1c0751f3e9f1` |
| Frozen browser receiver | `30d8abef87cc09615277b839dc4d6edcc7ae90d6443abdbe18a90f86294aa6d7` |

The accepted original author commit is `0f6e453cee36bbfcece6c0c80e90a38bc39cd0bd`.

## Actual current-source receiving

Both production builds pass TypeScript and Vite. The candidate passes **120 native Vitest tests across nine files**, including current encounter, decision-trail, track-editing, numeric-admission, audit, and Python interoperability tests.

The same frozen receiver runs both actual builds in Chromium **153.0.8010.47**, using ordinary range-key input, Run, Reset, and Export controls. It steps the application's actual animation callbacks at 1000 and 1050 ms. State, projection code, and rendering are not replaced. Exported WorldState timestamps provide the elapsed-time observations.

The baseline passes the untouched-page group and fails both tuned-state Reset groups, with exactly six expected failing assertions. The candidate passes **all three groups and all 19 assertions**, with no page or HTTP errors. Both source and build pins remain unchanged.

| Scenario | Before Reset: simulated seconds in a 50 ms step | Baseline after Reset | Candidate after Reset |
| --- | ---: | ---: | ---: |
| Fresh default | 3 | — | — |
| Speed 3x, wide policy | 9 | 9 | 3 |
| Speed 0.5x, narrow policy | 1.5 | 1.5 | 3 |

The receiver also checks reset sliders, formatted labels, policy statistics, paused state, exact initial WorldState, and the projected world after resuming. Captured current-source policy screenshots were visually checked: the baseline displays 10.0 NM / 2,500 FT / 10.0 MIN beside reset range positions; the candidate displays 5.0 NM / 1,000 FT / 5.0 MIN.

This browser workflow covers Reset and ordinary traffic controls. Planner and approval/readback workflows are outside these browser cases. Commands, environment paths, source checks, raw results, and captures are preserved in the archive.

## Existing owners

[HAMON #140 comment 6058825120](https://github.com/Jacob-Met/hamon/issues/140#issuecomment-6058825120) and [TowerOps PR #44](https://github.com/Jacob-Met/TowerOps/pull/44) assign broader automatic-pause synchronization to `estate-55e3e26c5905`. The inspected head is `92700c313125d2c1fd32f7d016febe7090e6adc6`, source SHA-256 `c5867cb7c293eb3f5f104b5f3a0e5d2c94a5b8bb42be833bd2f7df42085ac312`. That source and the coordination text are retained.

The shared `rate=1` behavior overlaps that draft. Its `pauseTraffic` helper and eight existing pause boundaries remain with that owner. This composition does not adopt or revise the broader pause handling. If PR #44 lands first, integration must retain its helper/call-site behavior, with one rate reset and this policy/readout correction.

[Issue #37 comment 6059713022](https://github.com/Jacob-Met/TowerOps/issues/37#issuecomment-6059713022) retains e3's Reset ownership and links an independent four-group receiving of the original function. Root's independent receiver also passed 17 checks on the original candidate. Those earlier receipts remain pinned to their original source; the 120-test and 19-assertion results above are current-main receiving.

## Evidence packet

`manifest.json` indexes every member of `receiving-evidence.tar.gz` by SHA-256 and size. The archive contains source/ownership pins, exact baseline/candidate main files, composition/build/test drivers, raw runs, screenshots, and transformed HTML/JavaScript/CSS assets. Each browser receipt retains the complete served-file hashes. Copied runtime assets remain reproducible from the pinned source/dependency versions.

Existing dependencies were reused with generated output and caches confined to this receiver. After all tests passed, ENOSPC interrupted two packet-only writes, leaving both files empty. The guarded cleanup removed only verified untracked duplicate runtime copies; served builds, source, and actual test receipts stayed intact. That environment event is preserved separately and is not a product test failure.

This checkpoint includes no GitHub write, merge, or deployment. Recheck the actual source base and PR #44 coordination before publication.
