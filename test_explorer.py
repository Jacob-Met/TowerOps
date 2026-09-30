import copy
import http.client
import json
import threading
import unittest
from explorer import Handler, ThreadingHTTPServer
from scenarios import SCENARIOS, replay_result, run_scenario
from towerops import AuditLog, canonical_bytes

EXPECTED = {"approved": None, "missing_approval": "human_approval_required", "missing_ack": "ack_missing",
            "late_ack": "ack_late", "stale_state": "stale_state", "stale_binding": "world_hash_mismatch",
            "wrong_ack": "ack_invalid", "expired": "expired_advisory"}


class ScenarioTests(unittest.TestCase):
    def test_all_cases_and_fixture_switches(self):
        for case in SCENARIOS:
            for approval in (False, True):
                for ack in (False, True):
                    with self.subTest(case=case, approval=approval, ack=ack):
                        result = run_scenario(case, approval, ack)
                        self.assertTrue(result["before_conflict"])
                        self.assertTrue(AuditLog.verify(result["audit_events"]))
                        self.assertTrue(replay_result(result)["matches"])
                        actuation = [e for e in result["audit_events"] if e["kind"] == "simulated_actuation"]
                        if case == "approved" and approval and ack:
                            self.assertEqual(result["outcome"], "simulated_actuation")
                            self.assertFalse(result["after_conflict"])
                            self.assertEqual(len(actuation), 1)
                            self.assertEqual(result["after"]["version"], result["before"]["version"] + 1)
                        else:
                            self.assertEqual(result["outcome"], "rejected")
                            self.assertEqual(result["before"], result["after"])
                            self.assertEqual(actuation, [])
                        if approval and ack:
                            self.assertEqual(result["rejection_reason"], EXPECTED[case])

    def test_replay_checks_whole_export(self):
        for case in SCENARIOS:
            original = run_scenario(case)
            for field in ("after", "audit_events", "disclaimer", "audit_head", "outcome"):
                with self.subTest(case=case, field=field):
                    changed = copy.deepcopy(original)
                    if field == "after":
                        changed[field]["version"] += 1
                    elif field == "audit_events":
                        changed[field][0]["payload"]["simulation_only"] = False
                    else:
                        changed[field] = "tampered"
                    self.assertFalse(replay_result(changed)["matches"])
        changed = run_scenario("approved")
        changed["audit_valid"] = 1
        self.assertFalse(replay_result(changed)["matches"])

    def test_javascript_numeric_roundtrip(self):
        original = run_scenario("approved")
        def integers(value):
            if type(value) is float and value.is_integer():
                return int(value)
            if isinstance(value, dict):
                return {k: integers(v) for k, v in value.items()}
            if isinstance(value, list):
                return [integers(v) for v in value]
            return value
        self.assertTrue(replay_result(integers(original))["matches"])
        changed = copy.deepcopy(original)
        changed["before"]["aircraft"][0]["vx_nm_min"] += 0.001
        self.assertFalse(replay_result(changed)["matches"])

    def test_no_baseline_changes_or_nondeterminism(self):
        self.assertEqual(canonical_bytes(run_scenario("approved")), canonical_bytes(run_scenario("approved")))

    def test_invalid_input(self):
        for value in (None, [], {}, {"format": "invalid"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replay_result(value)
        with self.assertRaises(ValueError):
            run_scenario("unknown")
        with self.assertRaises(ValueError):
            run_scenario("approved", 1, True)  # type: ignore[arg-type]


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, value=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = json.dumps(value) if value is not None else raw
        supplied = {"Content-Type": "application/json"}
        supplied.update(headers or {})
        connection.request(method, path, body, supplied)
        response = connection.getresponse()
        status, content, response_headers = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return status, content, response_headers

    def test_real_run_export_replay(self):
        status, content, _ = self.request("GET", "/api/scenarios")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(content)["scenarios"]), len(SCENARIOS))
        for case in SCENARIOS:
            with self.subTest(case=case):
                status, content, _ = self.request("POST", "/api/run", {"scenario": case, "include_approval": True, "include_ack": True})
                self.assertEqual(status, 200)
                exported = json.loads(content)
                self.assertEqual(exported["rejection_reason"], EXPECTED[case])
                status, content, _ = self.request("POST", "/api/replay", exported)
                self.assertEqual(status, 200)
                self.assertTrue(json.loads(content)["matches"])
                exported["after"]["version"] += 1
                self.assertFalse(json.loads(self.request("POST", "/api/replay", exported)[1])["matches"])

    def test_static_assets_and_unknown_routes(self):
        for path in ("/", "/app.js", "/style.css"):
            status, content, headers = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertGreater(len(content), 100)
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for path in ("/towerops.py", "/../LICENSE", "/.git/config"):
            self.assertEqual(self.request("GET", path)[0], 404)

    def test_invalid_requests_fail(self):
        self.assertEqual(self.request("POST", "/api/run", {"scenario": "approved"})[0], 400)
        self.assertEqual(self.request("POST", "/api/run", raw="not-json")[0], 400)
        self.assertEqual(self.request("POST", "/api/run", raw='{"x": NaN}')[0], 400)
        self.assertEqual(self.request("POST", "/api/run", raw="[]")[0], 400)
        self.assertEqual(self.request("POST", "/api/run", raw="{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/run", raw="x" * 262145)[0], 413)
        self.assertEqual(self.request("POST", "/api/run", raw="{}")[0], 400)
        self.assertEqual(self.request("GET", "/", headers={"Host": "foreign.invalid"})[0], 403)
        self.assertEqual(self.request("POST", "/api/run", raw="{}", headers={"Origin": "https://foreign.invalid"})[0], 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
