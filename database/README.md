# database/ — SQLite database

The database is one SQLite file, `database/oceansight.db` (set `OCEANSIGHT_DB` to use another; a relative path is resolved against `OceanSight/`). It is created from `schema.sql`, which is the source of truth: the server's ORM models mirror it. Standard library only.

## Commands

From `OceanSight/` (they also work from any other directory):

```
python database/init_db.py              # create the database and the five buoys; safe to re-run
python database/init_db.py --reset      # delete it first (development only)
python database/backfill.py             # 2000 readings per buoy, 5 s apart, ending now
python database/backfill.py --count 20000        # 100,000 rows
python database/backfill.py --buoy BUOY-03 --interval 30
python database/backfill.py --clear     # delete the existing readings first
python database/perf_check.py           # the DB-4 measurement below, on a throwaway database
```

Check what is in it:

```
sqlite3 database/oceansight.db "SELECT buoy_id, COUNT(*), MAX(timestamp) FROM sensor_data GROUP BY buoy_id"
```

## Files

| File | What |
|---|---|
| `schema.sql` | Tables `buoys` and `sensor_data`, and the index. |
| `seed.sql` | The five buoys (`INSERT OR IGNORE`, so it can run again). |
| `init_db.py` | Builds the database from the two files above and turns on WAL. |
| `backfill.py` | Historical readings for demos and performance tests. They follow the simulator's random walk, with a few anomalies (temperature 32–38 or pressure 40–60). Keep its baselines in sync with `simulator/generator.py`. |
| `perf_check.py` | Query plan and timings for "latest 50 readings of a buoy" on 100,000 rows. |

## Notes

- Timestamps are TEXT in one form, `YYYY-MM-DDTHH:MM:SSZ` (UTC, second precision), so string order is time order. Do not use SQLite `DATETIME` types.
- There is no `UNIQUE (buoy_id, timestamp)`: a "request update" can land in the same second as a scheduled reading. Readings from the same second are ordered by `id`.
- SQLite ignores foreign keys unless `PRAGMA foreign_keys=ON` is set on each connection; the server does this.
- WAL mode (set by `init_db.py`) lets the server read while the simulator's readings are written.
- Any change to `schema.sql` must be agreed with the server owner first: the ORM models have to match.

## Performance (DB-4)

`python database/perf_check.py` — 100,000 rows (5 buoys × 20,000), the query the server runs for `GET /api/buoys/{id}/data`, 200 runs each:

```
SEARCH sensor_data USING INDEX idx_sensor_data_buoy_ts (buoy_id=?)      no separate sort step

                 median        max
with index      0.027 ms    0.108 ms
without index  13.060 ms   22.536 ms
```

The index `(buoy_id, timestamp, id)` serves the `ORDER BY timestamp DESC, id DESC` directly. The original design's Test 8 asks for 95% of queries under 2 s; this is far inside that. Measured on the development laptop, so treat the numbers as an order of magnitude.
