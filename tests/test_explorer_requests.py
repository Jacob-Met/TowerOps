"""Exercise request framing at the real loopback explorer HTTP boundary."""

import http.client
import json
import socket
import threading
import unittest
from unittest.mock import patch

import explorer
from scenarios import run_scenario


class QuietHandler(explorer.Handler):
    def log_message(self, format, *args):
        pass


class ExplorerRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = explorer.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True,
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.body = json.dumps({
            "scenario": "approved", "include_approval": True, "include_ack": True,
        }).encode("utf-8")

    def request(self, body, lengths, *, path="/api/run", transfer=None, eof=True):
        headers = [
            f"POST {path} HTTP/1.1",
            f"Host: 127.0.0.1:{self.server.server_port}",
            "Content-Type: application/json",
        ]
        headers.extend(f"Content-Length: {value}" for value in lengths)
        if transfer is not None:
            headers.append(f"Transfer-Encoding: {transfer}")
        request = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + body
        connection = socket.create_connection(
            ("127.0.0.1", self.server.server_port), timeout=1.5,
        )
        response = http.client.HTTPResponse(connection)
        try:
            connection.sendall(request)
            if eof:
                connection.shutdown(socket.SHUT_WR)
            response.begin()
            return response.status, json.loads(response.read())
        finally:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            response.close()
            connection.close()

    def assert_refused(self, status, body, lengths, **kwargs):
        with (
            patch.object(explorer, "run_scenario", wraps=explorer.run_scenario) as run,
            patch.object(explorer, "replay_result", wraps=explorer.replay_result) as replay,
        ):
            actual, result = self.request(body, lengths, **kwargs)
            self.assertEqual(actual, status)
            self.assertIsInstance(result.get("error"), str)
            run.assert_not_called()
            replay.assert_not_called()

    def test_complete_run_and_replay(self):
        status, exported = self.request(self.body, [str(len(self.body))])
        self.assertEqual(status, 200)
        self.assertEqual(exported, run_scenario("approved"))
        replay_body = json.dumps(exported).encode("utf-8")
        status, result = self.request(
            replay_body, [str(len(replay_body))], path="/api/replay",
        )
        self.assertEqual(status, 200)
        self.assertTrue(result["matches"])

    def test_complete_body_at_maximum_size(self):
        body = self.body + b" " * (explorer.MAX_BODY - len(self.body))
        status, result = self.request(body, [str(len(body))])
        self.assertEqual(status, 200)
        self.assertEqual(result, run_scenario("approved"))

    def test_decimal_length_can_have_leading_zeroes(self):
        for prefix in ("0", "0" * 5000):
            with self.subTest(zeroes=len(prefix)):
                status, result = self.request(self.body, [prefix + str(len(self.body))])
                self.assertEqual(status, 200)
                self.assertEqual(result["outcome"], "simulated_actuation")

    def test_missing_length_is_required(self):
        self.assert_refused(411, self.body, [])

    def test_malformed_length_is_refused(self):
        for length in ("", "-1", "+76", "1.0", "not-a-number", "76, 76"):
            with self.subTest(length=length):
                self.assert_refused(400, self.body, [length])

    def test_duplicate_lengths_are_refused_even_when_equal(self):
        length = str(len(self.body))
        for lengths in ([length, length], [length, str(len(self.body) + 1)]):
            with self.subTest(lengths=lengths):
                self.assert_refused(400, self.body, lengths)

    def test_out_of_range_length_is_refused_before_body_read(self):
        for length in ("0", str(explorer.MAX_BODY + 1), "9" * 5000):
            with self.subTest(length_size=len(length)):
                self.assert_refused(413, b"", [length], eof=False)

    def test_all_transfer_encodings_are_refused(self):
        for transfer in ("chunked", "identity", ""):
            for lengths in ([], [str(len(self.body))]):
                with self.subTest(transfer=transfer, lengths=lengths):
                    self.assert_refused(400, self.body, lengths, transfer=transfer)

    def test_complete_json_with_truncated_framing_is_not_executed(self):
        for path, value in (
            ("/api/run", self.body),
            ("/api/replay", json.dumps(run_scenario("approved")).encode("utf-8")),
        ):
            with self.subTest(path=path):
                self.assert_refused(400, value, [str(len(value) + 1)], path=path)

    def test_empty_and_partial_idle_bodies_time_out_without_execution(self):
        # A shorter idle timeout keeps this socket-level regression fast. The
        # real server uses BODY_READ_TIMEOUT; no clock or stream is mocked.
        with patch.object(explorer, "BODY_READ_TIMEOUT", 0.1, create=True):
            for body in (b"", self.body[:10]):
                with self.subTest(received=len(body)):
                    self.assert_refused(408, body, [str(len(self.body))], eof=False)

    def test_healthy_request_after_refusal(self):
        self.assert_refused(400, self.body, [str(len(self.body) + 1)])
        status, result = self.request(self.body, [str(len(self.body))])
        self.assertEqual(status, 200)
        self.assertEqual(result, run_scenario("approved"))


if __name__ == "__main__":
    unittest.main()
