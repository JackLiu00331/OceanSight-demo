"""Fill the database with historical readings for demos and performance tests (DB-3).

    python database/backfill.py                      2000 readings per buoy, 5 s apart, ending now
    python database/backfill.py --count 20000        100,000 rows across the five buoys
    python database/backfill.py --buoy BUOY-03 --interval 30
    python database/backfill.py --clear              delete the existing readings first

Readings follow the same random walk as the simulator, with a few anomalies mixed in
(temperature 32-38 or pressure 40-60), so the charts have something to show.
Standard library only.
"""
import argparse
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import init_db

# Keep in sync with simulator/generator.py (PM Plan 3.3 and 3.4).
BASELINES = {
    "BUOY-01": {"temperature": 14.0, "pressure": 15.0},
    "BUOY-02": {"temperature": 16.5, "pressure": 18.0},
    "BUOY-03": {"temperature": 18.5, "pressure": 20.0},
    "BUOY-04": {"temperature": 12.5, "pressure": 22.0},
    "BUOY-05": {"temperature": 13.5, "pressure": 17.0},
}
TEMPERATURE_BAND = (8.0, 26.0)
PRESSURE_BAND = (12.0, 28.0)
ANOMALY_TEMPERATURE = (32.0, 38.0)
ANOMALY_PRESSURE = (40.0, 60.0)


def _clamp(value: float, band: tuple) -> float:
    return max(band[0], min(band[1], value))


def make_rows(buoy_id, count, interval, end, rng, anomaly_rate):
    """Rows for one buoy, oldest first, the last one stamped `end`."""
    baseline = BASELINES[buoy_id]
    temperature, pressure = baseline["temperature"], baseline["pressure"]
    rows = []
    for i in range(count):
        temperature = _clamp(temperature + 0.1 * (baseline["temperature"] - temperature) + rng.gauss(0, 0.15), TEMPERATURE_BAND)
        pressure = _clamp(pressure + 0.1 * (baseline["pressure"] - pressure) + rng.gauss(0, 0.10), PRESSURE_BAND)
        shown_temperature, shown_pressure = temperature, pressure
        if rng.random() < anomaly_rate:
            if rng.random() < 0.5:
                shown_temperature = rng.uniform(*ANOMALY_TEMPERATURE)
            else:
                shown_pressure = rng.uniform(*ANOMALY_PRESSURE)
        moment = end - timedelta(seconds=(count - 1 - i) * interval)
        stamp = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append((buoy_id, stamp, round(shown_temperature, 2), round(shown_pressure, 2), stamp))
    return rows


def backfill(connection, buoy_ids, count, interval=5, anomaly_rate=0.002, seed=None, end=None) -> int:
    """Insert `count` readings for each buoy in one transaction. Returns the number of rows inserted."""
    rng = random.Random(seed)
    end = end or datetime.now(timezone.utc)
    inserted = 0
    for buoy_id in buoy_ids:
        rows = make_rows(buoy_id, count, interval, end, rng, anomaly_rate)
        connection.executemany(
            "INSERT INTO sensor_data (buoy_id, timestamp, temperature, pressure, received_at) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        inserted += len(rows)
    connection.commit()
    return inserted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Insert historical readings for demos and performance tests.")
    parser.add_argument("--count", type=int, default=2000, help="readings per buoy (default 2000)")
    parser.add_argument("--interval", type=int, default=5, help="seconds between readings (default 5)")
    parser.add_argument("--buoy", help="only this buoy (default: all five)")
    parser.add_argument("--anomaly-rate", type=float, default=0.002, help="chance a reading is an anomaly (default 0.002)")
    parser.add_argument("--seed", type=int, help="make the data repeatable")
    parser.add_argument("--clear", action="store_true", help="delete the existing readings first")
    args = parser.parse_args(argv)

    if args.buoy and args.buoy not in BASELINES:
        parser.error(f"unknown buoy_id: {args.buoy}")
    path = init_db.db_path()
    if not path.exists():
        parser.error(f"database not found: {path} (run python database/init_db.py first)")

    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        if args.clear:
            connection.execute("DELETE FROM sensor_data")
            connection.execute("DELETE FROM sqlite_sequence WHERE name = 'sensor_data'")
        buoys = [args.buoy] if args.buoy else list(BASELINES)
        inserted = backfill(connection, buoys, args.count, args.interval, args.anomaly_rate, args.seed)
    finally:
        connection.close()
    print(f"inserted {inserted} readings for {', '.join(buoys)} into {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
