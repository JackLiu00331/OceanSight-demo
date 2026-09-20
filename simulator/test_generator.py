import contextlib
import io
import json
import random
import re
import unittest
from datetime import datetime, timezone

import generator


class MakeReadingTests(unittest.TestCase):
    def test_roster_matches_plan(self):
        self.assertEqual(list(generator.BUOYS), [f"BUOY-0{i}" for i in range(1, 6)])

    def test_reading_has_exactly_the_contract_fields(self):
        reading = generator.make_reading("BUOY-01")
        self.assertEqual(set(reading), {"buoy_id", "timestamp", "temperature", "pressure"})
        self.assertEqual(reading["buoy_id"], "BUOY-01")

    def test_timestamp_is_utc_second_precision_with_z(self):
        stamp = generator.make_reading("BUOY-02")["timestamp"]
        self.assertRegex(stamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        parsed = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertLess(abs((datetime.now(timezone.utc) - parsed).total_seconds()), 5)

    def test_values_are_floats_inside_the_normal_band(self):
        for buoy_id in generator.BUOYS:
            for _ in range(1000):
                reading = generator.make_reading(buoy_id)
                self.assertIsInstance(reading["temperature"], float)
                self.assertIsInstance(reading["pressure"], float)
                self.assertTrue(8.0 <= reading["temperature"] <= 26.0, reading)
                self.assertTrue(12.0 <= reading["pressure"] <= 28.0, reading)

    def test_unknown_buoy_raises(self):
        with self.assertRaisesRegex(ValueError, "unknown buoy_id: BUOY-99"):
            generator.make_reading("BUOY-99")


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.fleet = generator.Fleet(random.Random(7))

    def test_walk_stays_inside_the_normal_band(self):
        for buoy_id in generator.BUOYS:
            for _ in range(2000):
                reading = self.fleet.next_reading(buoy_id)
                self.assertTrue(8.0 <= reading["temperature"] <= 26.0, reading)
                self.assertTrue(12.0 <= reading["pressure"] <= 28.0, reading)

    def test_consecutive_readings_move_gently(self):
        previous = self.fleet.next_reading("BUOY-01")
        for _ in range(1000):
            current = self.fleet.next_reading("BUOY-01")
            self.assertLess(abs(current["temperature"] - previous["temperature"]), 1.0)
            self.assertLess(abs(current["pressure"] - previous["pressure"]), 1.0)
            previous = current

    def test_temperature_anomaly_trips_the_alert_but_stays_valid(self):
        reading = self.fleet.next_reading("BUOY-03", "temperature")
        self.assertTrue(30.0 < reading["temperature"] <= 38.0, reading)  # above the alert threshold, below the validity limit (40)
        self.assertTrue(12.0 <= reading["pressure"] <= 28.0, reading)  # the other value stays normal

    def test_pressure_anomaly_trips_the_alert_but_stays_valid(self):
        reading = self.fleet.next_reading("BUOY-03", "pressure")
        self.assertTrue(40.0 <= reading["pressure"] <= 60.0, reading)  # above the alert threshold (30), below the validity limit (100)
        self.assertTrue(8.0 <= reading["temperature"] <= 26.0, reading)

    def test_anomaly_does_not_disturb_the_walk(self):
        self.fleet.next_reading("BUOY-02", "temperature")
        reading = self.fleet.next_reading("BUOY-02")
        self.assertTrue(8.0 <= reading["temperature"] <= 26.0, reading)

    def test_unknown_buoy_and_unknown_anomaly_raise(self):
        with self.assertRaisesRegex(ValueError, "unknown buoy_id: BUOY-99"):
            self.fleet.next_reading("BUOY-99")
        with self.assertRaisesRegex(ValueError, "unknown anomaly: flood"):
            self.fleet.next_reading("BUOY-01", "flood")


class CliTests(unittest.TestCase):
    def test_prints_one_json_reading(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = generator.main(["BUOY-03"])
        self.assertEqual(code, 0)
        reading = json.loads(out.getvalue())
        self.assertEqual(reading["buoy_id"], "BUOY-03")

    def test_defaults_to_buoy_01(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            generator.main([])
        self.assertEqual(json.loads(out.getvalue())["buoy_id"], "BUOY-01")

    def test_unknown_buoy_exits_2_with_message_on_stderr(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = generator.main(["BUOY-99"])
        self.assertEqual(code, 2)
        self.assertIn("unknown buoy_id: BUOY-99", err.getvalue())


if __name__ == "__main__":
    unittest.main()
