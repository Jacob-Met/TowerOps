"""Exercise the additive explanation route through the real local HTTP handler."""
import copy
import http.client
import json
import threading
import unittest

from explorer import Handler, ThreadingHTTPServer
from scenarios import run_scenario


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class ExplanationHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        if cls.thread.is_alive():
            raise RuntimeError("Local test server did not close")

    def post(self, route, value):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request("POST", route, json.dumps(value), {"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def test_match_adds_empty_differences_and_preserves_ordinary_reply_bytes(self):
        value = run_scenario("approved")
        before = self.post("/api/replay", value)
        status, raw, headers = self.post("/api/replay/explain", value)
        after = self.post("/api/replay", value)
        self.assertEqual((before[0], status, after[0]), (200, 200, 200))
        self.assertEqual(before[1], after[1])
        reply = json.loads(raw)
        self.assertEqual({key: item for key, item in reply.items()
                          if key not in {"difference_limit", "differences", "differences_truncated"}},
                         json.loads(before[1]))
        self.assertTrue(reply["matches"])
        self.assertEqual(reply["difference_limit"], 32)
        self.assertEqual(reply["differences"], [])
        self.assertIs(reply["differences_truncated"], False)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_one_changed_field_reports_literal_typed_sides(self):
        value = run_scenario("approved")
        value["after"]["version"] = 3
        unchanged = copy.deepcopy(value)
        status, raw, _ = self.post("/api/replay/explain", value)
        self.assertEqual(status, 200)
        reply = json.loads(raw)
        self.assertIs(reply["matches"], False)
        self.assertEqual(reply["differences"], [{"path": "/after/version", "kind": "value",
            "expected": {"present": True, "type": "number", "value": 2},
            "actual": {"present": True, "type": "number", "value": 3}}])
        self.assertIs(reply["differences_truncated"], False)
        self.assertEqual(value, unchanged)

    def test_unexpected_fields_are_ordered_and_capped(self):
        value = run_scenario("approved")
        for index in range(33):
            value[f"extra-{index:02}"] = "<b>literal λ</b>"
        status, raw, _ = self.post("/api/replay/explain", value)
        self.assertEqual(status, 200)
        reply = json.loads(raw)
        self.assertIs(reply["matches"], False)
        self.assertIs(reply["differences_truncated"], True)
        self.assertEqual(reply["difference_limit"], 32)
        self.assertEqual(reply["differences"], [{"path": f"/extra-{index:02}", "kind": "unexpected",
            "expected": {"present": False},
            "actual": {"present": True, "type": "string", "value": "<b>literal λ</b>"}}
            for index in range(32)])

    def test_refusal_has_existing_error_shape_and_next_explicit_request_recovers(self):
        status, raw, _ = self.post("/api/replay/explain", {})
        self.assertEqual(status, 400)
        self.assertEqual(set(json.loads(raw)), {"error"})
        status, raw, _ = self.post("/api/replay/explain", run_scenario("approved"))
        self.assertEqual(status, 200)
        self.assertIs(json.loads(raw)["matches"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
