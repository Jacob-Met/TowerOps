"""Cold custody and semantic check for the TowerOps optional HTML author packet.

Reads the archive without extracting or executing product, browser, or planner.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import tarfile


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def shown(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


class Document(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.feed(raw.decode())

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": "", "ancestors": self.stack[:]}
        self.nodes.append(node)
        if tag not in {"meta", "link", "br", "hr", "input", "img"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data

    def find(self, attr, value, parent=None):
        return [
            node for node in self.nodes
            if node["attrs"].get(attr) == value
            and (parent is None or any(ancestor is parent for ancestor in node["ancestors"]))
        ]

    def one(self, attr, value, parent=None):
        nodes = self.find(attr, value, parent)
        require(len(nodes) == 1, f"Expected one {attr}={value}; got {len(nodes)}")
        return nodes[0]


def verify(path):
    with tarfile.open(path, "r:xz") as archive:
        members = archive.getmembers()
        require(all(member.isfile() for member in members), "Only ordinary files allowed")
        require(len({member.name for member in members}) == len(members), "Duplicate member")
        require(all(not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
                    for member in members), "Unsafe member name")
        data = {member.name: archive.extractfile(member).read() for member in members}
    manifest = json.loads(data["native-manifest.json"])
    require(manifest["schema"] == "towerops.plan-html-author-native/1", "Manifest schema")
    require(set(data) == {row["path"] for row in manifest["files"]} | {"native-manifest.json"},
            "Complete member set")
    for row in manifest["files"]:
        require(len(data[row["path"]]) == row["bytes"], f"Length: {row['path']}")
        require(sha(data[row["path"]]) == row["sha256"], f"Hash: {row['path']}")
    def record(name):
        return json.loads(data[name])
    frozen_name = "evidence/candidate-frozen-manifest.json"
    require(sha(data[frozen_name]) ==
            "f9f0b0e2fc2a60e6d3bdfdfd0177cef7db035c9dd62f8aa51ecce0aa48467397",
            "Exact accepted candidate manifest")
    frozen = record(frozen_name)
    for row in frozen["files"]:
        raw = data["candidate/" + row["path"]]
        require(sha(raw) == row["sha256"] and len(raw) == row["bytes"],
                "Candidate bytes " + row["path"])
        require(git_blob(raw) == row["git_blob"], "Candidate Git blob")
    primary = record("evidence/primary-git-provenance.json")
    original = {row["path"]: row for row in primary["original_tree"]["tree"]
                if row["type"] == "blob"}
    baseline = record("evidence/baseline-complete-manifest.json")
    require(len(baseline["files"]) == 33, "Baseline closure")
    for row in baseline["files"]:
        raw = data["baseline/" + row["path"]]
        require(sha(raw) == row["sha256"], "Baseline hash " + row["path"])
        require(git_blob(raw) == original[row["path"]]["sha"], "Canonical Git source")
    modes = [row["path"] for row in baseline["files"]
             if row["mode"] != original[row["path"]]["mode"]]
    require(modes == ["explorer.py"], "Explicit one-file native projection mode distinction")
    mode_note = record("evidence/native-projection-mode-qualification.json")
    require(mode_note["difference"]["canonical_git_mode"] == "100755", "Canonical executable")
    require(mode_note["difference"]["native_copy_mode"] == "100644", "Native projection mode")
    source = data["candidate/plan_world.py"].decode()
    parser_addition = (
        '    parser.add_argument(\n        "--html", action="store_true",\n'
        '        help="Write a standalone offline alternative review instead of JSON",\n    )\n'
    )
    format_addition = (
        "        if args.html:\n            from world_plan_html import render_plan_html\n\n"
        "            output = render_plan_html(output)\n"
    )
    require(source.count(parser_addition) == 1 and source.count(format_addition) == 1,
            "Exact optional CLI additions")
    restored = source.replace(parser_addition, "", 1).replace(format_addition, "", 1)
    require(restored.encode() == data["baseline/plan_world.py"], "All original producer bytes")
    native = record("evidence/author-native-v1/receipt.json")
    require(native["full_suite_exit"] == 1, "Retain original incomplete-capsule suite failure")
    require(b"FileNotFoundError" in data["evidence/author-native-v1/pytest.stdout"],
            "Original missing static file error")
    corrected = record("evidence/author-native-v2/receipt.json")
    require(corrected["returncode"] == 0 and corrected["source_unchanged"], "Final native suite")
    require(b"155 passed, 89 subtests passed" in data["evidence/author-native-v2/stdout.txt"],
            "Actual native counts")
    require(corrected["source_before"] == corrected["source_after"], "Native source stable")
    require(native["source_unchanged"], "Original CLI source stability")
    case_rows = []
    total_advisories = 0
    for row in native["cases"]:
        label = row["case"]
        prefix = "evidence/author-native-v1/" + label
        original_json = data[prefix + "-baseline.stdout"]
        require(original_json == data[prefix + "-candidate.stdout"], "Default JSON unchanged")
        expected = json.loads(original_json)
        require(expected["input_sha256"] == sha(data[prefix + ".world.json"]), "Input identity")
        require(expected["world_hash"] == sha(canonical(expected["world"])), "World body hash")
        document = Document(data[prefix + "-html.stdout"])
        anchor = document.one("id", "download-json")
        url = anchor["attrs"]["href"]
        header = "data:application/json;charset=utf-8;base64,"
        require(url.startswith(header), "Native data download")
        require(base64.b64decode(url[len(header):], validate=True) == original_json,
                "Exact JSON download")
        require(not any(node["tag"] in {"script", "img", "link", "iframe", "form"}
                        for node in document.nodes), "No executable or external resources")
        summary = document.one("id", "summary")
        values = {key: expected[key] for key in
                  ["status", "candidate_count", "conflicting_aircraft", "reviewed_at",
                   "input_sha256", "world_hash"]}
        values.update(version=expected["world"]["version"],
                      observed_at=expected["world"]["observed_at"],
                      admitted_count=len(expected["advisories"]))
        for key, value in values.items():
            require(document.one("data-field", key, summary)["text"] == shown(value),
                    "Exact summary " + key)
        for key, value in expected["policy"].items():
            require(document.one("data-policy-field", key)["text"] == shown(value),
                    "Exact policy " + key)
        world_node = document.one("id", "world")
        world_rows = [node for node in document.nodes
                      if node["tag"] == "tr" and "data-aircraft-id" in node["attrs"]
                      and any(parent is world_node for parent in node["ancestors"])]
        require([node["attrs"]["data-aircraft-id"] for node in world_rows] ==
                [item["aircraft_id"] for item in expected["world"]["aircraft"]],
                "Complete ordered world table")
        for node, aircraft in zip(world_rows, expected["world"]["aircraft"]):
            for key, value in aircraft.items():
                require(document.one("data-field", key, node)["text"] == shown(value),
                        "World value " + key)
        options = document.find("class", "alternative")
        require(len(options) == len(expected["advisories"]), "Complete native option count")
        current = {item["aircraft_id"]: item for item in expected["world"]["aircraft"]}
        for rank, (node, option) in enumerate(zip(options, expected["advisories"]), 1):
            require(node["attrs"]["data-rank"] == str(rank), "Original menu rank")
            require(node["attrs"]["data-aircraft-id"] == option["aircraft_id"], "Target identity")
            body = {key: value for key, value in option.items() if key != "advisory_hash"}
            require(sha(canonical(body)) == option["advisory_hash"], "Advisory body hash")
            require(option["world_hash"] == expected["world_hash"], "Bound world")
            displayed = document.one("data-field", "advisory_json", node)["text"]
            require(displayed == json.dumps(option, ensure_ascii=False, allow_nan=False, indent=2),
                    "All nine exact native option fields")
            for field in ["vx_nm_min", "vy_nm_min", "climb_ft_min"]:
                table_row = document.one("data-component", field, node)
                require(document.one("data-value", "current", table_row)["text"] ==
                        shown(current[option["aircraft_id"]][field]), "Current component")
                require(document.one("data-value", "proposed", table_row)["text"] ==
                        shown(option["set_" + field]), "Proposed component")
        total_advisories += len(options)
        case_rows.append({"case": label, "status": expected["status"], "advisories": len(options),
                          "json_sha256": sha(original_json)})
    require(len(case_rows) == 6, "Six original/candidate CLI pairs")
    failed = record("evidence/author-browser-v3/failure.json")
    first = [row for row in failed["checks"] if row["name"].startswith("crossing ")]
    require(len(first) == 12 and all(row["passed"] for row in first), "First complete browser case")
    require("Timeout" in failed["error"], "Retain original later keyboard timeout")
    rest = record("evidence/author-browser-v4/report.json")
    require(rest["passed"] and len(rest["checks"]) == 60 and
            all(row["passed"] for row in rest["checks"]), "Five-case browser supplement")
    require(failed["errors"] == [] and rest["errors"] == [], "No document errors")
    require(all(url.startswith("file:") for url in failed["requests"] + rest["requests"]),
            "Observed direct-file requests")
    require(rest["metadata"]["javaScriptEnabled"] is False, "JavaScript disabled")
    accepted_downloads = [
        ("crossing", "evidence/author-browser-v3/downloads/crossing.json")
    ] + [(row["case"], "evidence/author-browser-v4/downloads/" + row["case"] + ".json")
         for row in rest["downloads"]]
    require(len(accepted_downloads) == 6, "Six accepted actual browser downloads")
    for label, filename in accepted_downloads:
        require(data[filename] == data["evidence/author-native-v1/" + label + "-baseline.stdout"],
                "Actual native download bytes")
    images = []
    for name, raw in data.items():
        if name.endswith(".png"):
            require(raw[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature")
            width, height = struct.unpack(">II", raw[16:24])
            require(width in (375, 1280) and height == 900, "Actual viewport PNG dimensions")
            images.append({"path": name, "width": width, "height": height, "sha256": sha(raw)})
    reconstruction = record("evidence/current-parent-reconstruction.json")
    current_readme = primary["current_readme"]["content"]
    composed = data["publication/README.md"].decode()
    require(composed.replace(reconstruction["readme_block"], "", 1) == current_readme,
            "Current README reconstruction")
    require(sum(row["unchanged"] for row in reconstruction["canonical_closure"]) == 32,
            "Later-parent exact byte closure")
    require(record("evidence/own-profile-cleanup.json")["all_retained_hashes_exact"],
            "Own disposable profile cleanup retained sources/results")
    return {
        "schema": "towerops.plan-html-author-verification/1",
        "archive_sha256": sha(Path(path).read_bytes()),
        "ordinary_members": len(members),
        "manifest_artifacts": len(manifest["files"]),
        "canonical_baseline_files": 33,
        "frozen_candidate_files": len(frozen["files"]),
        "scoped_paths": frozen["scope_paths"],
        "native_projection_mode_difference": mode_note["difference"],
        "actual_native_tests": {"passed": 155, "subtests_passed": 89},
        "cli_pairs": case_rows,
        "advisory_bindings_recomputed": total_advisories,
        "accepted_browser_checks": 72,
        "accepted_actual_browser_downloads": len(accepted_downloads),
        "original_incomplete_suite_and_browser_failures_retained": True,
        "images": images,
        "current_source_only_parent": reconstruction["parent"],
        "product_execution_during_verification": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive), ensure_ascii=False, indent=2) + "\n", end="")
