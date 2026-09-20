import json
import unittest
from unittest import mock

import httpx
from fastapi.testclient import TestClient

import generator
import main


def stub_server(status=201, body=None, fail=None):
    """An httpx client whose 'server' answers with `status`, or raises `fail`. Returns (client, requests_seen)."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        if fail:
            raise fail
        return httpx.Response(status, json=body or {"status": "ok"})

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def make_app(**stub):
    client, seen = stub_server(**stub)
    return TestClient(main.create_app("http://server.test", 5, client, start_loop=False)), seen


class ControlApiTests(unittest.TestCase):
    def test_health(self):
        api, _ = make_app()
        response = api.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "interval_seconds": 5, "paused": False})

    def test_simulate_sends_one_reading_to_the_server(self):
        api, seen = make_app()
        response = api.post("/simulate/BUOY-03")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["server_status"], 201)
        self.assertEqual(set(body["sent"]), {"buoy_id", "timestamp", "temperature", "pressure"})
        self.assertEqual(body["sent"]["buoy_id"], "BUOY-03")
        self.assertEqual(seen, [body["sent"]])  # what the server received is what we report having sent

    def test_temperature_anomaly_is_flagged_by_value_but_valid(self):
        api, _ = make_app()
        sent = api.post("/simulate/BUOY-01?anomaly=temperature").json()["sent"]
        self.assertTrue(30.0 < sent["temperature"] <= 40.0, sent)

    def test_pressure_anomaly_is_flagged_by_value_but_valid(self):
        api, _ = make_app()
        sent = api.post("/simulate/BUOY-01?anomaly=pressure").json()["sent"]
        self.assertTrue(30.0 < sent["pressure"] <= 100.0, sent)

    def test_unknown_buoy_is_404_in_the_error_format(self):
        api, seen = make_app()
        response = api.post("/simulate/BUOY-99")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"status": "error", "message": "unknown buoy_id: BUOY-99"})
        self.assertEqual(seen, [])

    def test_unknown_anomaly_is_400(self):
        api, seen = make_app()
        response = api.post("/simulate/BUOY-01?anomaly=flood")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(seen, [])

    def test_server_rejection_is_502_with_the_reason(self):
        api, _ = make_app(status=400, body={"status": "error", "message": "unknown buoy_id: BUOY-01"})
        response = api.post("/simulate/BUOY-01")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("unknown buoy_id: BUOY-01", response.json()["message"])

    def test_unreachable_server_is_502(self):
        api, _ = make_app(fail=httpx.ConnectError("connection refused"))
        response = api.post("/simulate/BUOY-01")
        self.assertEqual(response.status_code, 502)
        self.assertIn("server unreachable", response.json()["message"])


class ScheduledRoundTests(unittest.TestCase):
    def test_one_reading_per_buoy(self):
        client, seen = stub_server()
        with self.assertLogs("oceansight_simulator", level="INFO"):
            stored = main.run_round(generator.Fleet(), client, "http://server.test")
        self.assertEqual(stored, 5)
        self.assertEqual([r["buoy_id"] for r in seen], list(generator.BUOYS))

    def test_unreachable_server_is_logged_and_does_not_raise(self):
        client, seen = stub_server(fail=httpx.ConnectError("connection refused"))
        with self.assertLogs("oceansight_simulator", level="ERROR") as logs:
            stored = main.run_round(generator.Fleet(), client, "http://server.test")
        self.assertEqual(stored, 0)
        self.assertEqual(len(seen), 5)  # it still tried every buoy
        self.assertEqual(len(logs.records), 5)

    def test_rejected_reading_is_logged_and_the_round_carries_on(self):
        client, seen = stub_server(status=400, body={"status": "error", "message": "temperature out of valid range [-5, 40]"})
        with self.assertLogs("oceansight_simulator", level="ERROR") as logs:
            stored = main.run_round(generator.Fleet(), client, "http://server.test")
        self.assertEqual(stored, 0)
        self.assertEqual(len(seen), 5)
        self.assertIn("temperature out of valid range", logs.output[0])


class FakeStop:
    """Stands in for threading.Event: runs the loop body once, and records how long it waits."""

    def __init__(self):
        self.waits = []
        self._checks = 0

    def is_set(self):
        self._checks += 1
        return self._checks > 1

    def wait(self, timeout):
        self.waits.append(timeout)


class LoopTimingTests(unittest.TestCase):
    def run_once(self, clock, round_effect=None):
        stop = FakeStop()
        with mock.patch("main.run_round", side_effect=round_effect), mock.patch("main.monotonic", side_effect=clock):
            main.run_loop(None, None, "http://server.test", 5, stop)
        return stop.waits

    def test_the_wait_is_the_interval_minus_the_time_the_round_took(self):
        self.assertEqual(self.run_once([100.0, 102.0]), [3.0])

    def test_a_round_longer_than_the_interval_is_followed_by_the_next_at_once(self):
        self.assertEqual(self.run_once([0.0, 9.0]), [0.0])

    def test_a_failing_round_is_logged_and_the_loop_carries_on(self):
        with self.assertLogs("oceansight_simulator", level="ERROR"):
            waits = self.run_once([0.0, 1.0], round_effect=RuntimeError("boom"))
        self.assertEqual(waits, [4.0])


if __name__ == "__main__":
    unittest.main()
