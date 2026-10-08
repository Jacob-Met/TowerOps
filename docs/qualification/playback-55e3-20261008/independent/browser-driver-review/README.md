# Independent browser-driver admission review

This receipt preserves a source-level finding and its repair **before native browser execution**. It adds no product test result. The earlier 39-file receiving packet and 14-file current-audit packet remain unchanged.

The original driver (`6d550471…`) allowed every failure whose name began with `reset default engine rate:` under `--expect-broken`. That included unrelated world-version, aircraft-identity and velocity failures. Its grouped `reset visible controls` check also allowed an unexpected label, slider or visible clock mismatch to be treated as the known stale-rate readout. The failure-name pair `reset visible controls` and `reset default engine rate: world version` satisfied those source predicates. This is a direct code-path counterexample; no fabricated browser failure is recorded.

The repaired driver (`32ceece0…`) separates Reset control checks, requires actual retained-rate baseline progression and the exact stale readout, and compares the complete observed failure-name list to the exact expected set. For automatic pauses it additionally requires the exact stale `Pause traffic` button and its one expected label failure. Unrelated failures now refuse expected-baseline admission. All other driver code was unchanged in the reviewed diff.

The reviewed driver uses trusted Chrome input events, the native Export live world action, native drawing and native controls. It controls animation-frame timestamps explicitly. Source and built-file hashes are recorded before and after. Build-to-source correspondence must also be established by the separate native build receipt. Desktop/mobile results concern the tested Chrome viewports and screenshots. Planner/Pyodide and physical-device behavior are outside this driver.

The original and repaired source bytes are preserved alongside [before-static-review.json](before-static-review.json) and [repaired-static-review.json](repaired-static-review.json). This review runs no new tests and edits no product source. Actual Mac build/Vitest/browser outputs are a subsequent receiving stage.

| Captured driver | SHA256 |
| --- | --- |
| `before-driver.mjs` | `6d55047158fbcfc6c19e7198422cc025e98f884fd78e151e8e9fa964bb0853a6` |
| `repaired-driver.mjs` | `32ceece05135ae23dbf6442b2c3755da0a1602e85d7408328b9118b23d43ce93` |
