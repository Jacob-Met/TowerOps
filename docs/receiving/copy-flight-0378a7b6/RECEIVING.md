# Selected-flight copy receiving

The unchanged 2119eac8 browser can edit its selected trajectory under a fixed callsign; it has no independent copy action. Its actual CPython planner, approval, readback and audit passed in the original baseline.

The seven-path authored source is pinned in source-freeze.json. The candidate retains exact source velocity/climb, appends one translated flight, and binds review to current fields and simulation context. Production code is additive: new model/controller, a narrow main seam and copy panel. Existing selected-edit, radar, worker and planner functions are unchanged.

Native source gates: Node 24.19.0, existing CPython 3.12.14, all 254 original tests; candidate all 276 tests (22 new) and build pass. The first baseline invoked the Windows Store python3 alias (13 failures); a second used an existing Python 3.11 environment and default Windows text encoding (one Unicode failure). The declared Python 3.12 minimum and explicit UTF-8 pipes resolved the receiving environment, without modifying shared runtimes. Every original log is retained.

The original browser matcher accidentally matched the existing button “Edit COPYBASE”; the corrected baseline matcher is anchored to the action name. Its original failure is preserved. The first candidate browser found the copy panel remained visible until the next draw after starting playback. Commitment already rechecked context. Two event refresh hooks now retire playback/time-scale reviews immediately; original failure retained.

The corrected actual-browser receipt passes six groups: nonmutating preview/cancel with raw and builder drafts; exact-vector one-time copy and invalid/changed input refusal; world/policy/playback/reset retirement; existing selected-edit exclusivity; preservation of an actual pending CPython proposal and approval on cancellation; fresh actual CPython planner/approval/readback after a committed copy clears the prior proposal. Page errors and external requests are empty. Desktop and mobile screenshots show the reviewed copy panel. The runtime input hashes equal the later authored commit; docs were added afterward.

The standalone browser drivers use this contributor's existing Playwright installation and MSI Chrome, serve only the isolated checkout on loopback, and preserve receipts on failure. Machine paths are provenance, not installation requirements. No operational aviation assurance is claimed.

Independent source/receiving adoption and final hosted CI/integration will be recorded separately. MANIFEST.json verifies every copied evidence byte.
