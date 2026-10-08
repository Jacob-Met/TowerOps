"""Review the native planner's alternatives without changing a live control room.

These are mutually exclusive proposals, not an executable batch. Selection does
not grant approval: the original ControlRoom.apply must still admit the selected
advisory, its world, its approval and its readback at application time.
"""
from __future__ import annotations

from dataclasses import dataclass

from towerops import (
    Advisory,
    AdvisoryPlanner,
    ControlRoom,
    GateRejected,
    SafetyPolicy,
    WorldState,
)


@dataclass(frozen=True)
class AdvisoryOptions:
    world_hash: str
    reviewed_at: float
    candidate_count: int
    advisories: tuple[Advisory, ...]


def review_advisory_options(
    state: WorldState, now: float, policy: SafetyPolicy | None = None,
) -> AdvisoryOptions:
    """Return every individually admitted native candidate in planner order.

    The existing maneuver generator owns the bounded menu and priority. A
    private control room checks freshness even when there are no conflicts,
    then screens each alternative separately so mutually exclusive options are
    never submitted as a batch. Its screening trace is intentionally local;
    reviewing options does not append events to a caller's decision trace.
    """
    policy = policy or SafetyPolicy()
    room = ControlRoom(policy)
    room.screen_batch(state, [], now)
    world_hash = state.world_hash
    planner = AdvisoryPlanner(policy)
    admitted: list[Advisory] = []
    candidate_count = 0
    for target in reversed(policy.conflicting_aircraft(state)):
        for vx, vy, climb in planner._maneuver_candidates(target):
            candidate_count += 1
            advisory = Advisory(
                aircraft_id=target.aircraft_id,
                world_hash=world_hash,
                set_vx_nm_min=vx,
                set_vy_nm_min=vy,
                set_climb_ft_min=climb,
                issued_at=now,
                expires_at=now + 8.0,
                rationale="synthetic projected-separation recovery",
            )
            try:
                room.screen_batch(state, [advisory], now)
            except GateRejected as error:
                if error.reason != "unsafe_advisory":
                    raise
            else:
                admitted.append(advisory)
    return AdvisoryOptions(world_hash, now, candidate_count, tuple(admitted))
