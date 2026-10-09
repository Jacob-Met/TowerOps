"""Recorded actuations need available world identities before linkage is clean."""
import contextlib
import copy
import io
import json
import sys
import unittest
from unittest.mock import patch

import audit_replay
from decision_trace import review_trace
from towerops import Ack, AdvisoryPlanner, Aircraft, Approval, AuditLog, ControlRoom, SafetyPolicy, WorldState


def produced_events():
    policy = SafetyPolicy()
    state = WorldState(
        1, 1000.0,
        (
            Aircraft("LEFT", -5.0, 0.0, 10000.0, 1.0, 0.0),
            Aircraft("RIGHT", 5.0, 0.0, 10000.0, -1.0, 0.0),
        ),
    )
    advisory = AdvisoryPlanner(policy).plan(state, 1002.0)[0]
    room = ControlRoom(policy)
    room.apply(
        state, advisory,
        Approval(advisory.advisory_hash, "approve", 1002.2, "Authored reviewer"),
        Ack(advisory.advisory_hash, "accepted", 1002.4), 1002.5,
    )
    return room.audit.events


def rebuild(events):
    log = AuditLog()
    for event in events:
        log.append(event["kind"], copy.deepcopy(event["payload"]))
    return log.events


class WorldLinkageTests(unittest.TestCase):
    def check_report(self, events, expected):
        before = copy.deepcopy(events)
        report = audit_replay.replay_audit(events)
        delivered = review_trace(json.dumps(events))
        self.assertTrue(report.chain_valid)
        self.assertEqual(report.ok, expected, report.issues)
        self.assertEqual(delivered["ok"], expected, delivered["issues"])
        self.assertEqual(delivered["issues"], report.issues)
        self.assertEqual(events, before)
        return report

    def test_actual_producer_keeps_complete_world_links(self):
        self.check_report(produced_events(), True)

    def test_each_absent_or_unusable_identity_is_a_finding(self):
        for index, field in ((0, "world_hash"), (3, "before_world_hash")):
            with self.subTest(field=field, value="absent"):
                events = produced_events()
                del events[index]["payload"][field]
                report = self.check_report(rebuild(events), False)
                self.assertTrue(any("usable" in issue for issue in report.issues))
            for value in (None, "", " \t\r\n", 0, False, [], {}):
                with self.subTest(field=field, value=value):
                    events = produced_events()
                    events[index]["payload"][field] = value
                    report = self.check_report(rebuild(events), False)
                    self.assertTrue(any("usable" in issue for issue in report.issues))

    def test_equal_unusable_values_do_not_establish_world_identity(self):
        for value in (None, "", " \t", 12, False, [], {}):
            with self.subTest(value=value):
                events = produced_events()
                events[0]["payload"]["world_hash"] = value
                events[3]["payload"]["before_world_hash"] = value
                self.check_report(rebuild(events), False)

    def test_opaque_nonblank_string_identity_remains_compatible(self):
        for value in ("legacy-world-label", " world label with surrounding spaces "):
            with self.subTest(value=value):
                events = produced_events()
                events[0]["payload"]["world_hash"] = value
                events[3]["payload"]["before_world_hash"] = value
                self.check_report(rebuild(events), True)

    def test_comparison_does_not_normalize_present_identity(self):
        events = produced_events()
        events[0]["payload"]["world_hash"] = "world"
        events[3]["payload"]["before_world_hash"] = " world "
        report = self.check_report(rebuild(events), False)
        self.assertTrue(any("does not match" in issue for issue in report.issues))

    def test_nonactuated_prefixes_do_not_gain_identity_requirements(self):
        events = produced_events()
        del events[0]["payload"]["world_hash"]
        for length in (0, 1, 2, 3):
            with self.subTest(length=length):
                self.check_report(rebuild(events[:length]), True)

    def test_rejection_only_and_unknown_kinds_keep_existing_meaning(self):
        for kind, payload in (
            ("reject", {"reason": "authored rejection"}),
            ("future_annotation", {"world_hash": None, "text": "unrecognized kind"}),
        ):
            with self.subTest(kind=kind):
                log = AuditLog()
                log.append(kind, payload)
                self.check_report(log.events, True)

    def test_a_later_incomplete_actuation_is_not_hidden_by_a_complete_one(self):
        events = produced_events()
        later = copy.deepcopy(events[-1])
        del later["payload"]["before_world_hash"]
        report = self.check_report(rebuild([*events, later]), False)
        advisory = next(iter(report.advisories.values()))
        self.assertEqual(len(advisory.actuations), 2)
        self.assertTrue(any("before_world_hash" in issue for issue in report.issues))

    def test_broken_chain_keeps_its_original_early_result(self):
        events = produced_events()
        del events[-1]["payload"]["before_world_hash"]
        report = audit_replay.replay_audit(events)
        self.assertFalse(report.chain_valid)
        self.assertFalse(report.ok)
        self.assertEqual(report.advisories, {})
        self.assertEqual(report.issues, ["audit chain integrity check failed"])

    def test_stdin_main_delivers_findings_without_changing_input(self):
        events = produced_events()
        del events[-1]["payload"]["before_world_hash"]
        events = rebuild(events)
        raw = json.dumps({"audit_events": events, "label": "saved incomplete trace"})
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(raw)):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = audit_replay.main(["audit_replay.py", "-"])
        summary = json.loads(out.getvalue())
        self.assertEqual(code, 1)
        self.assertTrue(summary["chain_valid"])
        self.assertFalse(summary["ok"])
        self.assertTrue(summary["issues"])
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
