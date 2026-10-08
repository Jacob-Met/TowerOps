# Live traffic register: source and native qualification

This packet accompanies TowerOps issue [#63](https://github.com/Jacob-Met/TowerOps/issues/63). It adds callsign search, scenario/callsign/altitude ordering, visible match counts, an explicit filtered-selection notice and native keyboard selection to the existing Traffic panel.

The actual authored parent is `89529c5459b1c3d52448e197de2b2f7fe8b6d128`, tree `03fec48eb2a60ff34084051d55ce4c5b446c7bb1`. The radar owner confirmed its #59 composition leaves `drawLists` unchanged. The source boundary is the new register model/view/scoped CSS, one main import/initialization, the former flight-row loop, register-only markup, focused tests and operator guidance. Existing conflict rendering, scenario controls, planner/worker, gate, clock, editor, track-edit and radar handlers are preserved.

## Accepted results

- Native Chromium 153.0.8010.47 / Node 22.22.1: **35/35** checks, no page errors or external requests. The normal JSON input loaded a nontrivial 60-aircraft world. Search, every order, hidden selection, explicit Tab/Enter selection, focus through redraw, live climbing rows, scenario replacement and 390-pixel layout were exercised.
- The same browser completed a real Python planner → approval → unfinished selected-flight edit/raw JSON draft → cancel → readback/apply journey. Register actions preserved the complete held state and then the nonempty four-event native audit. The Worker observer recorded and forwarded actual traffic; it did not substitute worker results or application state.
- All **1,094** frozen source hashes and **5** borrowed inputs matched before/after native receiving. The receipt SHA-256 is `3c63fb91915c0a71469d70b1c7cdf60d17313ce907085db9334225ab3c3f3887`.
- TypeScript and all **234/234** Vitest assertions passed, including **8/8** new projection tests and the retained **14/14** playback assertions. The playback fixture only gained a rendering adapter mock because it intentionally has no browser DOM; every assertion body remains byte-identical.
- Native Python asset preparation and Vite production build passed, with runtime and borrowed inputs unchanged. The native browser accepted the Vite-served source, not a separately claimed built-browser run.
- The exact desktop and 390-pixel frames were inspected: controls, counts, hidden-selection notice and flight rows remain readable and inside the viewport.

Runtime model SHA-256: `e1c24207d07ef4cd25f0fd8efaaadee9e38b0149d1e52fbdebfc7b9a935d2293`.
Runtime view SHA-256: `47aff47e99481815e3f953b7de677d08e9e3ba726626eb009edf20e707e57b85`.

## Preserved controls and nonaccepting attempts

The unchanged parent browser receipt proves the 60-flight input and incumbent explicit selection, and records the absent search/order capability. This is feature absence, not a reported parent defect.

The first candidate browser attempt completed 20 checks, then timed out waiting for metadata to change in the EST fixture group. Those aircraft have zero climb and constant velocity, so the displayed altitude/velocity correctly stayed fixed as traffic moved. The second method changes only that live-running fixture filter to the existing climbing STH group. Runtime was unchanged. The first receipt and exact method remain here as a nonaccepting receiver result.

The first unit run recorded 231/234, with three playback assertions interrupted by the new real DOM view inside the deliberately minimal playback fixture. The unchanged parent fixture separately passed 14/14. The added rendering mock follows that fixture's existing drawing/Python boundaries; no assertion was removed or weakened, and the real register DOM was received in Chromium.

## Reproduction and scope

Run the ordinary `web/airspace` TypeScript/Vitest/build commands with the repository's existing lock-matched dependencies. The eight maintained projection challenges are in `web/airspace/tests/flight-register.test.ts`.

The exact native receiving methods and input manifest are preserved under `methods/` and `inputs/`. They are historical executable methods for the recorded native source and runtime paths. Their config requires an owned, new output/profile directory, exact source hashes, installed Chromium, and the existing lock-matched Vite/Pyodide assets. For another checkout, create a new reviewed config and retain the new receipt separately; do not relabel these results as acceptance of changed source.

This packet records isolated source qualification. It does not claim a merged PR, installed deployment, real traffic service or aviation assurance.
