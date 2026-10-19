# View a saved synthetic world as a standalone SVG

`world_svg.py` produces a complete, offline SVG drawing from one **native raw**
TowerOps `WorldState` JSON file. It uses the same `parse_world` admission and
bounded file reader as `plan_world.py`. No network, model, browser service,
advisory, approval, acknowledgement, or actuation is involved.

```bash
python3 world_svg.py example.world.json > example.world.svg
python3 world_svg.py example.world.json --horizon-min 12 > example.12min.svg
cat example.world.json | python3 world_svg.py - > example.stdin.svg
```

Open the SVG in an image viewer or browser. Filled circles are the starting XY
positions; outlined squares are constant-velocity projected positions.
The plot uses *synthetic Cartesian nautical-mile offsets*, **not geographic
coordinates or a real airspace map**. X increases right; Y increases up.
The two-column legend shows each flight's initial and projected altitude in
feet; visual 2D intersections alone do **not** establish a separation conflict.
This visualization cannot certify the output of the planner or actual aircraft.

`--horizon-min` accepts a finite positive number up to 120 minutes (default 5).
The output is deterministic for equivalent native worlds regardless of input
aircraft order. The native parser refuses duplicate JSON keys, malformed types,
invalid callsigns, duplicate aircraft identities and non-finite inputs. The
renderer refuses non-finite projected results. Input bytes are left unchanged.
The command completes rendering before writing stdout. Invalid inputs exit 2,
print a diagnostic to stderr, and write no SVG. A downstream redirection target
is controlled by the shell, not by TowerOps: don't redirect over valuable files.
Broken stdout pipes can contain partial bytes; no file-integrity guarantee is
made for a failed downstream writer.

Offline verification from the repository root:

```bash
python3 -m unittest tests.test_world_svg -v
python3 -m compileall -q world_svg.py tests/test_world_svg.py
```

Research simulation only; not operational aviation software or safety assurance.
