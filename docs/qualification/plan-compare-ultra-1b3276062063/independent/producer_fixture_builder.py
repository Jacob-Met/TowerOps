"""Frozen producer-grounded comparison fixtures; no candidate import."""
import copy
import hashlib
import json
import zlib

def dump(value, *, compact=False):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False,
                       sort_keys=compact, separators=(",", ":") if compact else None,
                       indent=None if compact else 2) + "\n").encode("utf-8")

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def make_fixture_packet(review_world, SafetyPolicy, replace, canonical_bytes, sha256_obj):
    numbers = ("x_nm", "y_nm", "altitude_ft", "vx_nm_min", "vy_nm_min", "climb_ft_min")
    aircraft = [
        ("EAST", (-8.0, 1.0, 12000.0, 2.0, 0.0, 0.0)),
        ("WEST", (8.0, 1.0, 12000.0, -2.0, 0.0, 0.0)),
        ("FAR", (40.0, 40.0, 25000.0, 0.0, 0.0, 0.0)),
    ]
    world = {"version": 7, "observed_at": 120.0,
             "aircraft": [{"aircraft_id": name, **dict(zip(numbers, values))}
                          for name, values in aircraft]}
    raw_world = dump(world)
    policy = SafetyPolicy()
    five = review_world(raw_world)
    six = review_world(raw_world, policy=replace(policy, min_horizontal_nm=6.0))
    three = review_world(raw_world, policy=replace(policy, min_horizontal_nm=3.0))
    short = review_world(raw_world, policy=replace(policy, horizon_min=0.1))
    assert five["world_hash"] == "ae8ce380ecdddcef10cedfcdd46fcd601d9b6bdef5d33f90c4f531c2a5ed7150"
    assert (len(five["advisories"]), five["candidate_count"]) == (66, 74)
    assert (len(six["advisories"]), six["candidate_count"]) == (62, 74)
    assert (len(three["advisories"]), three["candidate_count"]) == (66, 74)
    assert (len(short["advisories"]), short["candidate_count"], short["status"]) == (0, 0, "no_conflict")
    five_ids = [row["advisory_hash"] for row in five["advisories"]]
    six_ids = [row["advisory_hash"] for row in six["advisories"]]
    assert set(six_ids) < set(five_ids) and len(set(five_ids) - set(six_ids)) == 4
    assert [row["advisory_hash"] for row in three["advisories"]] == five_ids
    files = {"world.json": raw_world}
    cases = []
    def put(name, value):
        files[name + ".json"] = value if isinstance(value, bytes) else dump(value)
        return name + ".json"
    def expected(left_raw, right_raw):
        left, right = json.loads(left_raw), json.loads(right_raw)
        lrows, rrows = left["advisories"], right["advisories"]
        lh = [row["advisory_hash"] for row in lrows]
        rh = [row["advisory_hash"] for row in rrows]
        entries = []
        for rank, row in enumerate(lrows, 1):
            other = rh.index(row["advisory_hash"]) + 1 if row["advisory_hash"] in rh else None
            entries.append({"membership": "retained" if other is not None else "left_only",
                            "left_rank": rank, "right_rank": other, "advisory": row})
        for rank, row in enumerate(rrows, 1):
            if row["advisory_hash"] not in lh:
                entries.append({"membership": "right_only", "left_rank": None,
                                "right_rank": rank, "advisory": row})
        changes = [{"field": field, "left": left["policy"][field], "right": right["policy"][field]}
                   for field in left["policy"]
                   if canonical_bytes(left["policy"][field]) != canonical_bytes(right["policy"][field])]
        def summary(doc, raw):
            return {"report_sha256": digest(raw), "reported_input_sha256": doc["input_sha256"],
                    "policy": doc["policy"], "status": doc["status"],
                    "conflicting_aircraft": doc["conflicting_aircraft"],
                    "candidate_count": doc["candidate_count"], "advisory_count": len(doc["advisories"]),
                    "first_advisory_hash": doc["advisories"][0]["advisory_hash"] if doc["advisories"] else None}
        return {"world": five["world"] if left["world_hash"] == five["world_hash"] else left["world"],
                "world_hash": left["world_hash"], "reviewed_at": left["reviewed_at"],
                "left": summary(left, left_raw), "right": summary(right, right_raw),
                "policy_changes": changes, "entries": entries,
                "counts": {"retained": len(set(lh) & set(rh)),
                           "left_only": len(set(lh) - set(rh)),
                           "right_only": len(set(rh) - set(lh)),
                           "rank_changed": sum(x["membership"] == "retained" and x["left_rank"] != x["right_rank"] for x in entries)}}
    for name, value in (("five", five), ("six", six), ("three", three), ("short", short)):
        put(name, value)
    def positive(name, left, right, cli=False):
        cases.append({"name": name, "kind": "accept", "left": left, "right": right,
                      "cli": cli, "expected": expected(files[left], files[right])})
    def negative(name, right, left="five.json", cli=False):
        path = right if isinstance(right, str) else put("bad_" + name, right)
        cases.append({"name": name, "kind": "refuse", "left": left, "right": path, "cli": cli})
    positive("tighten_policy_loses_four", "five.json", "six.json", True)
    positive("loosen_policy_gains_four", "six.json", "five.json", True)
    positive("identical_report", "five.json", "five.json", True)
    positive("policy_change_same_full_menu", "five.json", "three.json", True)
    positive("short_horizon_empty_menu", "five.json", "short.json", True)
    formatted = copy.deepcopy(five)
    formatted["world"]["aircraft"].reverse()
    put("formatted", dump(formatted, compact=True))
    positive("format_and_aircraft_order", "five.json", "formatted.json", True)
    reordered = copy.deepcopy(five)
    reordered["advisories"] = reordered["advisories"][1:] + reordered["advisories"][:1]
    put("reordered", reordered)
    positive("saved_rank_rotation", "five.json", "reordered.json", True)
    changed_body = copy.deepcopy(five)
    changed_body["advisories"][0]["rationale"] += " / recorded rationale variation"
    body = {key: value for key, value in changed_body["advisories"][0].items() if key != "advisory_hash"}
    changed_body["advisories"][0]["advisory_hash"] = sha256_obj(body)
    put("body_identity", changed_body)
    positive("full_body_identity", "five.json", "body_identity.json", True)
    int_policy = review_world(raw_world, policy=replace(policy, min_horizontal_nm=5))
    put("integer_policy", int_policy)
    positive("policy_numeric_token", "five.json", "integer_policy.json")
    empty_world = {"version": 0, "observed_at": 0.0, "aircraft": []}
    zero = review_world(dump(empty_world), now=0.0)
    minus_zero = review_world(dump(empty_world), now=-0.0)
    put("zero", zero)
    put("minus_zero", minus_zero)
    positive("empty_world_same_clock", "zero.json", "zero.json", True)
    negative("clock_signed_zero", "minus_zero.json", "zero.json", True)
    put("integer_clock", review_world(raw_world, now=120))
    negative("clock_integer_float", "integer_clock.json", cli=True)
    put("later_clock", review_world(raw_world, now=125.0))
    negative("clock_change", "later_clock.json")
    new_world = copy.deepcopy(world)
    new_world["version"] = 8
    put("new_world", review_world(dump(new_world)))
    negative("world_version_change", "new_world.json", cli=True)
    new_world = copy.deepcopy(world)
    new_world["aircraft"][0]["x_nm"] = -8
    put("world_number_type", review_world(dump(new_world)))
    negative("world_number_type", "world_number_type.json")
    corrupt = copy.deepcopy(five)
    corrupt["advisories"][0]["set_vx_nm_min"] = 0.125
    negative("body_hash_mismatch", corrupt, cli=True)
    corrupt = copy.deepcopy(five)
    corrupt["world_hash"] = "0" * 64
    negative("world_hash_mismatch", corrupt)
    corrupt = copy.deepcopy(five)
    corrupt["advisories"].append(copy.deepcopy(corrupt["advisories"][0]))
    negative("duplicate_advisory_identity", corrupt)
    corrupt = copy.deepcopy(five)
    del corrupt["advisories"][0]["rationale"]
    negative("incomplete_advisory_body", corrupt)
    corrupt = copy.deepcopy(five)
    corrupt["simulation_only"] = False
    negative("simulation_flag", corrupt)
    corrupt = copy.deepcopy(five)
    corrupt["status"] = "no_conflict"
    negative("status_menu_inconsistency", corrupt)
    corrupt = copy.deepcopy(five)
    corrupt["candidate_count"] = True
    negative("boolean_candidate_count", corrupt)
    corrupt = copy.deepcopy(five)
    corrupt["candidate_count"] = 1
    negative("candidate_count_below_admitted", corrupt)
    raw = files["five.json"]
    duplicate = raw.replace(b'"reviewed_at": 120.0,', b'"reviewed_at": 120.0, "reviewed_at": 120.0,', 1)
    assert duplicate != raw
    negative("duplicate_json_key", duplicate, cli=True)
    negative("infinite_json_number", raw.replace(b'"reviewed_at": 120.0,', b'"reviewed_at": 1e999,', 1))
    negative("over_four_mib", b" " * (4 * 1024 * 1024 + 1), cli=True)
    negative("invalid_utf8", b"\xff{}")
    encoded = {name: {"bytes": len(raw), "sha256": digest(raw), "hex": raw.hex()}
               for name, raw in files.items()}
    result = {"format": "towerops.independent-comparison-fixtures.v1",
              "evidence_kind": "authored synthetic saved reports from exact existing native planner",
              "candidate_exposure": "none",
              "case_count": len(cases), "cli_case_count": sum(x["cli"] for x in cases),
              "files": encoded, "cases": cases}
    packed = dump(result, compact=True)
    return result, packed, zlib.compress(packed, 9)
