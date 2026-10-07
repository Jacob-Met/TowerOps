# TowerOps / Airspace Lab

An interactive 2D traffic-management workbench, not a recorded animation. Add flights from your own callsign, position, flight level, bearing, speed and climb; or edit/import a `WorldState` JSON. Traffic advances from those velocity vectors. You can add/perturb/remove tracks, tune the horizontal/vertical separation envelope and look-ahead, run repeated planner passes, then approve and read back a world-bound setpoint before simulated actuation. A hash-chained audit trace can be verified in the page.

## Real TowerOps logic

The browser hosts a faithful TypeScript port of the Python `SafetyPolicy`, `AdvisoryPlanner`, `ControlRoom` safety gates, canonical world/advisory hashes and SHA-256 audit log. `tools/generate_airspace_reference.py` executes the original Python classes to maintain four reference scenarios; Vitest checks the browser port against those outputs. Additional tests construct visitor-authored worlds and run them through conflict timing, advisory search, approval, readback, actuation and audit verification. No prerecorded output drives the UI, and there is no model, network, live aircraft or external data call.

## Verify

From the repository root:

```bash
python3 tools/generate_airspace_reference.py --check
cd web/airspace
npm ci
npm test
npm run build
```

Optional Raider browser acceptance and desktop/phone captures:

```bash
python3 tools/capture_airspace.py
```

The app uses synthetic or visitor-provided state only. It is a research simulation, not operational air-traffic-control software or aviation assurance. Approval/readback controls are fixtures, not real authority.
