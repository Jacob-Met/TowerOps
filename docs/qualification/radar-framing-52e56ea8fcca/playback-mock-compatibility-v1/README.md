# Playback and radar test compatibility

The actual PR53 merge, `687a1f9492eb3c9d7dfaed2ae745c7a1bb3313d8`, includes the concurrent PR44 playback controls. Its new page-level test fully mocked the drawing module and omitted the radar label export now called by the page. The main-push Airspace build failed before deployment.

This repair changes only that drawing mock to a typed partial mock. It retains the real pure drawing exports and replaces only Canvas rendering. All playback assertions and all production files remain unchanged.

The exact actual merge reproduced the failure in native Vitest: 11 of 14 playback cases passed; both reset-rate cases and the planner-call case failed. With the single mock replacement, TypeScript passed, all 158 current tests passed, and the actual playback-plus-radar production bundle built. The 49-file qualification mirror remained unchanged during each run. The one changed test has Git blob `878ca0a8824c64b88c305899c4caa8d2eea5ceb0`.

The attached receipt binds the actual source, exact test replacement, full negative and positive native logs, and production output bytes. The gzip packet is JSON with base64 member data and per-member byte counts, SHA256 and Git blob digests; every member was decoded and verified after packing. The existing radar packet restore script supports the same member fields.

Public deployment and actual-public interaction acceptance are pending a successful corrected main-push build and deploy. No additional browser claim is made for this test-only correction.
