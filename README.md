# TowerOps

TowerOps is a **synthetic air-traffic-control decision-support research demo** built for the AWS **Agents for Humans** challenge. It combines a Strands agent proposal boundary with deterministic conflict prediction, freshness checks, approval/acknowledgement binding, simulated state transition, and hash-chained audit/replay.

> **Research simulation only.** TowerOps is not operational ATC software, aviation certification, a real clearance system, or connected to live aircraft/surveillance data.

## Inspiration

The initial idea came from seeing a social-media clip about two aircraft using the same callsign. That raised a broader question: what if an agent could help surface ambiguity, projected conflicts, stale state, or bad readbacks **without becoming the safety authority itself**?

## Core loop

```text
synthetic world state
→ conflict prediction
→ Strands agent proposal boundary
→ deterministic safety/freshness gate
→ approval binding
→ acknowledgement/readback binding
→ simulated state transition
→ audit/replay
```

The model proposes. Deterministic code decides whether the proposal is admissible.

## Run the deterministic demo

Requires Python 3.12+.

```bash
python demo.py
```

The demo creates two synthetic aircraft on a converging path, generates a bounded advisory, applies fixture approval + acknowledgement, performs the simulated transition, and prints the audit chain.

## Strands path

Install the SDK:

```bash
pip install -r requirements.txt
```

`strands_adapter.py` exposes a structured advisory tool. The Strands layer is proposal-only; it cannot bypass `towerops.py` safety, freshness, approval, acknowledgement, or audit logic.

## What is demonstrated

- continuous projected conflict/separation checks for the synthetic constant-velocity model
- exact world-state hash binding
- stale/future-state rejection
- contradictory recommendation rejection
- bounded advisory schema
- explicit approval requirement
- acknowledgement binding and late/missing acknowledgement rejection
- simulated state transition only after gates pass
- hash-chained audit log with replay verification

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Known limits

TowerOps is a hackathon research prototype. Its geometry and timing logic are evaluated on synthetic finite cases, but this repository does **not** claim operational aviation safety, exhaustive numeric coverage, live ATC integration, or production deployment. The demo uses fixture identities for approval/readback and no real-world authority.

## License

MIT — see [LICENSE](LICENSE).
