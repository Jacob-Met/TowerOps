"""Independent geometric and scale checks for the proximity CLI."""

from proximity_report import MAX_PAIRS, report_proximity
from tests.test_proximity_report import flight, world


def test_held_out_randomized_proximity_against_dense_independent_grid():
    # Deterministic geometry oracle: no reuse of _proximity's optimization.
    # Every grid point is an actual reachable point, so a correct continuous
    # minimum must be <= the smallest sampled score (within FP error).
    import math
    import random

    rng = random.Random(20261019)
    for case in range(160):
        a = flight("A", rng.uniform(-50, 50), rng.uniform(-50, 50),
                   rng.uniform(5000, 20000), rng.uniform(-5, 5),
                   rng.uniform(-5, 5), rng.uniform(-1500, 1500))
        b = flight("B", rng.uniform(-50, 50), rng.uniform(-50, 50),
                   rng.uniform(5000, 20000), rng.uniform(-5, 5),
                   rng.uniform(-5, 5), rng.uniform(-1500, 1500))
        horizon = rng.uniform(0.1, 30)
        horizontal = rng.uniform(1, 10)
        vertical = rng.uniform(500, 2000)
        actual = report_proximity(
            world(a, b), horizon_min=horizon,
            horizontal_nm=horizontal, vertical_ft=vertical,
        )["pairs"][0]
        dx, dy, dz = a["x_nm"] - b["x_nm"], a["y_nm"] - b["y_nm"], a["altitude_ft"] - b["altitude_ft"]
        dvx = a["vx_nm_min"] - b["vx_nm_min"]
        dvy = a["vy_nm_min"] - b["vy_nm_min"]
        dvz = a["climb_ft_min"] - b["climb_ft_min"]
        reference = min(
            max(math.hypot(dx + dvx * (horizon * tick / 2048),
                           dy + dvy * (horizon * tick / 2048)) / horizontal,
                abs(dz + dvz * (horizon * tick / 2048)) / vertical)
            for tick in range(2049)
        )
        assert 0 <= actual["closest_time_min"] <= horizon, case
        assert actual["proximity_ratio"] <= reference + 1e-9, case
        assert actual["proximity_ratio"] >= 0, case


def test_aircraft_input_order_changes_raw_bytes_but_not_canonical_pair_ranking():
    entries = (
        flight("Z", -5, vx=1), flight("A", 5, vx=-1),
        flight("B", 5, y=5.5, altitude=12000),
    )
    forward, reverse = report_proximity(world(*entries)), report_proximity(world(*reversed(entries)))
    assert forward["input_sha256"] != reverse["input_sha256"]
    assert forward["world_hash"] == reverse["world_hash"]
    assert forward["pairs"] == reverse["pairs"]
    assert forward["native_conflict_pair_count"] == reverse["native_conflict_pair_count"]


def test_sixty_aircraft_report_is_bounded_but_counts_every_pair():
    raw = world(*(flight(f"F{i:02d}", i * 50, altitude=10000) for i in range(60)))
    result = report_proximity(raw, limit=1)
    assert result["total_pair_count"] == MAX_PAIRS == 1770
    assert result["native_conflict_pair_count"] == 0
    assert result["returned_pair_count"] == 1
    assert result["truncated"] is True
