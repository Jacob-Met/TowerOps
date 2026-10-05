"""Fixed research fixtures: no live inputs, authority, or model calls."""
from dataclasses import asdict, replace
from typing import Any

from towerops import (
    Ack,
    AdvisoryPlanner,
    Aircraft,
    Approval,
    ControlRoom,
    GateRejected,
    SafetyPolicy,
    WorldState,
)

DISCLAIMER = "Synthetic research simulation only. Fixture identities, not real approval or authority. Not operational ATC, aviation assurance, or live aircraft control."
SCENARIOS = {
    "approved": ("Approval + acknowledgement", "Both exact-hash fixtures arrive before simulated dispatch."),
    "missing_approval": ("Missing approval", "The engine must refuse simulated actuation without its approval fixture."),
    "missing_ack": ("Missing acknowledgement", "Approval alone does not authorize the simulated transition."),
    "late_ack": ("Late acknowledgement", "Receipt is dated after the simulated dispatch cutoff; the engine rejects ack_late."),
    "stale_state": ("Stale observation", "The observation is older than the engine's ten-second freshness limit."),
    "stale_binding": ("Changed world binding", "World version changes after proposal; its hash no longer matches."),
    "wrong_ack": ("Wrong advisory acknowledgement", "Receipt binds a different advisory hash."),
    "expired": ("Expired proposal", "Dispatch occurs after the proposal's eight-second validity window."),
}


def run_scenario(scenario: str, include_approval: bool = True, include_ack: bool = True) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError("Unknown synthetic scenario")
    if type(include_approval) is not bool or type(include_ack) is not bool:
        raise ValueError("Fixture switches must be booleans")
    policy = SafetyPolicy()
    source = WorldState(1, 1001.0, (
        Aircraft("FIXTURE-A", -5.0, 0.0, 10000.0, 1.0, 0.0),
        Aircraft("FIXTURE-B", 5.0, 0.0, 10000.0, -1.0, 0.0),
    ))
    advisory = AdvisoryPlanner(policy).plan(source, now=1002.0)[0]
    state = replace(source, version=2) if scenario == "stale_binding" else source
    now = {"stale_state": 1012.0, "expired": 1010.5}.get(scenario, 1002.5)
    approval = Approval(advisory.advisory_hash, "approve", 1002.2, "FIXTURE-CONTROLLER-NOT-AUTHORITY")
    ack = Ack("f" * 64 if scenario == "wrong_ack" else advisory.advisory_hash,
              "accepted", 1002.8 if scenario == "late_ack" else 1002.4)
    if not include_approval or scenario == "missing_approval":
        approval = None
    if not include_ack or scenario == "missing_ack":
        ack = None
    room = ControlRoom(policy)
    room.audit.append("fixture_proposal", {"scenario": scenario, "source_world_hash": source.world_hash,
                                         "advisory": asdict(advisory), "simulation_only": True})
    after, reason = state, None
    try:
        after = room.apply(state, advisory, approval, ack, now)
    except GateRejected as exc:
        reason = exc.reason
    return {
        "format": "towerops.synthetic-explorer.v1", "disclaimer": DISCLAIMER,
        "request": {"scenario": scenario, "include_approval": include_approval, "include_ack": include_ack},
        "label": SCENARIOS[scenario][0], "description": SCENARIOS[scenario][1],
        "simulation_clock": {"dispatch_sec": now, "observed_sec": state.observed_at,
                             "projection_horizon_min": policy.horizon_min},
        "policy": asdict(policy), "before": state.to_dict(), "after": after.to_dict(),
        "before_world_hash": state.world_hash, "after_world_hash": after.world_hash,
        "advisory": asdict(advisory), "advisory_hash": advisory.advisory_hash,
        "fixtures": {"approval": asdict(approval) if approval else None, "ack": asdict(ack) if ack else None},
        "outcome": "simulated_actuation" if reason is None else "rejected",
        "rejection_reason": reason, "before_conflict": policy.state_has_conflict(state),
        "after_conflict": policy.state_has_conflict(after),
        "audit_events": room.audit.events, "audit_head": room.audit.head,
        "audit_valid": room.audit.verify(room.audit.events),
    }


def json_equivalent(expected: Any, actual: Any) -> bool:
    import math
    if type(expected) in (int, float) and type(actual) in (int, float):
        return (type(actual) is int or math.isfinite(actual)) and expected == actual
    if type(expected) is not type(actual):
        return False
    if isinstance(expected, dict):
        return expected.keys() == actual.keys() and all(json_equivalent(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return len(expected) == len(actual) and all(json_equivalent(a, b) for a, b in zip(expected, actual))
    return expected == actual


def replay_result(value: Any) -> dict[str, Any]:
    """Rerun fixed inputs and compare *all* output, not merely a self-consistent chain.

    This proves reproducibility under this local code, NOT provenance/authority.
    """
    if not isinstance(value, dict) or value.get("format") != "towerops.synthetic-explorer.v1":
        raise ValueError("Unsupported export format")
    request = value.get("request")
    if not isinstance(request, dict) or set(request) != {"scenario", "include_approval", "include_ack"}:
        raise ValueError("Malformed fixture request")
    if not isinstance(request["scenario"], str):
        raise TypeError("Scenario must be a string")
    expected = run_scenario(**request)
    # JSON clients serialize 1001.0 as 1001. Accept equivalent finite numbers,
    # but never coerce booleans, strings, containers, or field presence.
    matches = json_equivalent(expected, value)
    return {"matches": matches, "audit_valid": expected["audit_valid"],
            "outcome": expected["outcome"], "rejection_reason": expected["rejection_reason"],
            "expected_audit_head": expected["audit_head"],
            "note": "Local deterministic reproduction only; not a signature, provenance proof, or authority."}
