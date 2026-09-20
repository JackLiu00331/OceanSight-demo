"""Check the "latest 50 readings for a buoy" query on 100,000 rows (DB-4).

Builds a throwaway database in a temp folder (your real database is not touched), prints
the query plan and the timings with and without the index.

    python database/perf_check.py

Standard library only.
"""
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

import backfill
import init_db

ROWS_PER_BUOY = 20_000  # x 5 buoys = 100,000 rows
RUNS_PER_BUOY = 40

# The same query the server runs (server/repository.py).
LATEST_50 = """
    SELECT id, timestamp, temperature, pressure
    FROM sensor_data {hint}
    WHERE buoy_id = ?
    ORDER BY timestamp DESC, id DESC
    LIMIT 50
"""


def time_query(connection, sql, buoy_ids) -> list:
    """Milliseconds for each run of `sql`."""
    timings = []
    for buoy_id in buoy_ids:
        for _ in range(RUNS_PER_BUOY):
            started = time.perf_counter()
            connection.execute(sql, (buoy_id,)).fetchall()
            timings.append((time.perf_counter() - started) * 1000)
    return timings


def report(label, timings) -> None:
    print(f"  {label:<14} median {statistics.median(timings):8.3f} ms   max {max(timings):8.3f} ms")


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "perf.db"
        init_db.create_database(path)
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA foreign_keys=ON")
        buoy_ids = list(backfill.BASELINES)
        rows = backfill.backfill(connection, buoy_ids, ROWS_PER_BUOY, seed=1)
        print(f"{rows} rows inserted\n")

        indexed = LATEST_50.format(hint="")
        plan = [row[3] for row in connection.execute("EXPLAIN QUERY PLAN " + indexed, (buoy_ids[0],))]
        print("query plan:")
        for line in plan:
            print("  " + line)
        uses_index = any("idx_sensor_data_buoy_ts" in line for line in plan)
        needs_sort = any("TEMP B-TREE" in line for line in plan)
        print(f"\nuses idx_sensor_data_buoy_ts: {uses_index}   extra sort step: {needs_sort}\n")

        print(f"timings ({len(buoy_ids) * RUNS_PER_BUOY} runs each):")
        report("with index", time_query(connection, indexed, buoy_ids))
        report("without index", time_query(connection, LATEST_50.format(hint="NOT INDEXED"), buoy_ids))
        connection.close()
    return 0 if uses_index and not needs_sort else 1


if __name__ == "__main__":
    raise SystemExit(main())
