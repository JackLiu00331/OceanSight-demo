"""Simulated buoy readings (SIM-1, SIM-2).

Produces readings in the contract format (OceanSight_PM_Plan.md, section 3.5):
    {"buoy_id": "BUOY-01", "timestamp": "2026-10-09T15:00:05Z",
     "temperature": 14.12, "pressure": 15.03}

Print one reading:  python simulator/generator.py [BUOY-ID]
"""
import argparse
import json
import random
import sys
import threading
from datetime import datetime, timezone

# Roster and per-buoy baselines: PM Plan section 3.4.
BUOYS = {
    "BUOY-01": {"temperature": 14.0, "pressure": 15.0},
    "BUOY-02": {"temperature": 16.5, "pressure": 18.0},
    "BUOY-03": {"temperature": 18.5, "pressure": 20.0},
    "BUOY-04": {"temperature": 12.5, "pressure": 22.0},
    "BUOY-05": {"temperature": 13.5, "pressure": 17.0},
}

# Normal band: PM Plan section 3.3. Normal readings never leave it.
TEMPERATURE_BAND = (8.0, 26.0)  # degrees C
PRESSURE_BAND = (12.0, 28.0)  # dbar

# Spread of one stand-alone reading around its baseline (make_reading and the command line).
TEMPERATURE_NOISE = 0.5
PRESSURE_NOISE = 0.3

# Scheduled readings (Fleet) follow a random walk: each step pulls the value back towards the
# baseline and adds Gaussian noise, so a chart looks like a sea and not like static.
WALK_PULL = 0.1
TEMPERATURE_STEP = 0.15
PRESSURE_STEP = 0.10

# Anomaly injection: PM Plan section 3.3. Inside the server's validity range (so it is stored),
# outside its alert thresholds (so it is flagged).
ANOMALIES = ("none", "temperature", "pressure")
ANOMALY_TEMPERATURE = (32.0, 38.0)
ANOMALY_PRESSURE = (40.0, 60.0)


def utc_timestamp() -> str:
    """Capture time in the contract format: UTC, second precision, trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp(value: float, band: tuple) -> float:
    low, high = band
    return max(low, min(high, value))


def make_reading(buoy_id: str) -> dict:
    """Return one reading for buoy_id. Raises ValueError for a buoy outside the roster."""
    if buoy_id not in BUOYS:
        raise ValueError(f"unknown buoy_id: {buoy_id}")
    baseline = BUOYS[buoy_id]
    temperature = random.gauss(baseline["temperature"], TEMPERATURE_NOISE)
    pressure = random.gauss(baseline["pressure"], PRESSURE_NOISE)
    return {
        "buoy_id": buoy_id,
        "timestamp": utc_timestamp(),
        "temperature": round(_clamp(temperature, TEMPERATURE_BAND), 2),
        "pressure": round(_clamp(pressure, PRESSURE_BAND), 2),
    }


def _step(value: float, baseline: float, step: float, band: tuple, rng: random.Random) -> float:
    return _clamp(value + WALK_PULL * (baseline - value) + rng.gauss(0, step), band)


class Fleet:
    """The random-walk state of every buoy in the roster (SIM-2). Safe to use from several threads."""

    def __init__(self, rng: random.Random = None):
        self._rng = rng or random.Random()
        self._lock = threading.Lock()
        self._state = {buoy_id: dict(baseline) for buoy_id, baseline in BUOYS.items()}

    def next_reading(self, buoy_id: str, anomaly: str = "none") -> dict:
        """Advance the buoy one step and return its reading.

        An anomaly replaces one value in this reading only; the walk itself carries on unchanged.
        """
        if buoy_id not in BUOYS:
            raise ValueError(f"unknown buoy_id: {buoy_id}")
        if anomaly not in ANOMALIES:
            raise ValueError(f"unknown anomaly: {anomaly}")
        baseline = BUOYS[buoy_id]
        with self._lock:
            state = self._state[buoy_id]
            state["temperature"] = _step(state["temperature"], baseline["temperature"], TEMPERATURE_STEP, TEMPERATURE_BAND, self._rng)
            state["pressure"] = _step(state["pressure"], baseline["pressure"], PRESSURE_STEP, PRESSURE_BAND, self._rng)
            temperature, pressure = state["temperature"], state["pressure"]
            if anomaly == "temperature":
                temperature = self._rng.uniform(*ANOMALY_TEMPERATURE)
            elif anomaly == "pressure":
                pressure = self._rng.uniform(*ANOMALY_PRESSURE)
        return {
            "buoy_id": buoy_id,
            "timestamp": utc_timestamp(),
            "temperature": round(temperature, 2),
            "pressure": round(pressure, 2),
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Print one simulated buoy reading as JSON.")
    parser.add_argument("buoy_id", nargs="?", default="BUOY-01", help="one of: " + ", ".join(BUOYS))
    args = parser.parse_args(argv)
    try:
        reading = make_reading(args.buoy_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(reading))
    return 0


if __name__ == "__main__":
    sys.exit(main())
