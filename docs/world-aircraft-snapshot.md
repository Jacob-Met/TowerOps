# Aircraft membership in a native world

`WorldState` retains the supplied aircraft membership as a tuple when it is
constructed. Later edits to the caller's list do not change that world's
aircraft, order, serialized state, world hash or native planner inputs.

```python
from towerops import Aircraft, WorldState

traffic = [
    Aircraft("A", -5.0, 0.0, 10000.0, 1.0, 0.0),
    Aircraft("B", 5.0, 0.0, 10000.0, -1.0, 0.0),
]
world = WorldState(1, 1000.0, traffic)
traffic.clear()
assert len(world.aircraft) == 2
```

Previously, the frozen dataclass prevented field assignment but retained a
supplied list. Clearing that list also emptied the existing world and changed
its hash. In the synthetic example above, the native options review then
changed from 74 candidates and 68 admitted alternatives to zero of each.
A one-shot iterator was exhausted by duplicate-ID validation and left no
aircraft available to subsequent readers.

Construction now materializes the supplied iterable once, then applies the
existing duplicate-ID check to that retained membership. A duplicate still
raises `ValueError`. Native tuple input keeps its order, aircraft objects,
integer and float values, and signed zero; no aircraft fields are normalized.
The existing JSON parser already supplies a tuple and retains its behavior.

To represent changed traffic, explicitly construct another world or use
`replace_aircraft` for its existing versioned replacement operation. Editing
the original input container does not update an already constructed world.
An advisory remains subject to the existing world hash, policy, time,
approval and acknowledgement checks when it is applied.

This is a Python container snapshot. It does not copy arbitrary nested field
objects, synchronize a concurrently changing iterable during construction,
change the browser world model, or extend the synthetic geometry's claims.

## Verification

```sh
python -m pytest -q tests/test_world_aircraft_snapshot.py
```

The focused course checks caller clear/reorder/replacement/duplicate edits,
one-shot input, duplicate refusal, retained numeric representation, native
options review and a complete synthetic approval/readback/application path.
