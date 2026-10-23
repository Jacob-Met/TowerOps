# Reproducible synthetic WorldState generation

Generate scenario-authoring and regression inputs without network data, a model, real aircraft, or safety authority. This helper creates complete, strictly native-admitted `WorldState` JSON containing 2–60 fictional tracks. It reuses **unchanged** `plan_world.parse_world` and `SafetyPolicy.state_has_conflict` as the only native input and conflict authorities. It never plans, approves, acts on, or updates a saved world.

From the TowerOps root:

```sh
python3 synthesize_world.py --seed 42 --mode encounter --aircraft-count 8 > new-world.json
python3 plan_world.py new-world.json
python3 synthesize_world.py --seed 42 --mode clear --aircraft-count 8 | python3 plan_world.py -
```

Each command emits a single raw `WorldState` object to stdout (compact UTF-8 JSON plus newline). On error, stdout stays empty *if no stdout write has begun*; status `2` and an explanation go to stderr. Saving via ordinary shell `>` **can truncate an existing file before the command starts**; only use a fresh destination. No files are opened, created, or replaced by the generator itself. `--help` is non-destructive.

Arguments: required 64-bit unsigned integer `--seed`; optional `--aircraft-count` (2–60, default 2), `--mode encounter|clear` (default `encounter`), `--observed-at` (finite bounded JSON number, default `1000.0` seconds), and `--version` (0–9007199254740991, default 1). The seed is not stored in the strict native schema; preserve the command arguments next to any saved result. Repeating them yields byte-for-byte identical output under the same native source.

For `encounter`, the primary pair approaches from 20 nautical miles apart at 4 NM/min relative speed and intersects at 5 minutes, yielding a native default-policy conflict. For `clear`, it diverges. The seed varies the axis, position, altitude, and separated background tracks. Background tracks remain more than the default policy's horizontal limit apart across the five-minute horizon; the native policy's verdict on the entire world is verified before emission. These claims are **only for the current default synthetic policy** (5 NM horizontal, 1000 ft vertical, five-minute horizon), not arbitrary policies or live air traffic.

Generated callsigns `SYN00`–`SYN59` are fictional. Aircraft order and numeric types follow the native `to_dict` representation. There is no external ingestion, traffic prediction, operational aviation safety assurance, flight instruction, agent approval, or simulated actuation in this command.

## Direct checks

```sh
python3 -m pytest -q tests/test_synthesize_world.py
python3 -m pytest -q
python3 demo.py
```

The focused suite exercises deterministic bytes, changed seeds, both conflict modes, native parser and policy verdicts, bounded 60-aircraft populations, invalid inputs, distinct callsigns, CLI behavior, and a native `plan_world.py` consuming subprocess. The actual repository must be available to run those integration tests. The generator's deterministic source behavior does not by itself qualify any browser, Strands, or real aircraft integration.
