"""Minimal Strands boundary for TowerOps.

The model/tool layer proposes structured synthetic advisories. The deterministic
TowerOps gate in towerops.py remains authoritative for admission and simulated
application.
"""

from strands import Agent, tool


@tool
def submit_synthetic_advisory(
    aircraft_id: str,
    set_vx_nm_min: float,
    set_vy_nm_min: float,
    set_climb_ft_min: float,
    rationale: str,
) -> dict:
    """Return one structured proposal; this does not apply or authorize it."""
    return {
        "aircraft_id": aircraft_id,
        "set_vx_nm_min": set_vx_nm_min,
        "set_vy_nm_min": set_vy_nm_min,
        "set_climb_ft_min": set_climb_ft_min,
        "rationale": rationale,
        "effect": "proposal_only",
    }


def build_agent() -> Agent:
    return Agent(
        system_prompt=(
            "You are a synthetic ATC research assistant. Propose only structured "
            "advisories for simulated aircraft. Never claim operational authority."
        ),
        tools=[submit_synthetic_advisory],
    )
