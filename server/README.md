# server/ — FastAPI server

Receives readings from the simulator, validates and stores them in SQLite, and serves them to the dashboard. The contract is `../../OceanSight_PM_Plan.md` §3.

## Run

From `OceanSight/` (the database must exist: `python database/init_db.py`):

```
uv run --directory server uvicorn main:app --port 8000
```

Interactive docs: <http://127.0.0.1:8000/docs>. The database file is `database/oceansight.db`; set `OCEANSIGHT_DB` to use another (a relative path is resolved against `OceanSight/`).

## Test

```
uv run --directory server pytest
```

The tests build a throwaway database from `database/schema.sql` and `seed.sql`, so the real one is never touched.

## Endpoints

| | |
|---|---|
| `GET /api/health` | `{"status": "ok"}` |
| `POST /api/sensor-data` | Store one reading. `201`, or `400` (missing or mistyped field, timestamp not an ISO-8601 string with a timezone, value outside the validity range, unknown `buoy_id`). |
| `GET /api/buoys` | Every buoy with its coordinates and `latest_reading` (`null` when it has none). |
| `GET /api/buoys/{buoy_id}/data?limit=50` | The latest `limit` readings, oldest first. `limit` is 1–500. `404` for an unknown buoy; `[]` for a buoy with no data. |

Every error body is `{"status": "error", "message": "..."}`, including FastAPI's own 422 (turned into 400) and 404.

A reading outside the alert thresholds but inside the validity range is accepted, stored, and flagged `out_of_range` in the responses.

Not here yet: `POST /api/buoys/{id}/request-update` (SRV-5, Sprint R1-3).

## Files

| File | What |
|---|---|
| `main.py` | The app: CORS, error handlers, health check, routers. |
| `config.py` | **Thresholds, validity ranges, CORS origins, database path.** The only place they are defined. |
| `routers/sensor_data.py`, `routers/buoys.py` | The endpoints. |
| `schemas.py` | Request and response bodies; the input checks. |
| `models.py` | ORM models. They mirror `database/schema.sql`, which is the source of truth. |
| `repository.py` | Database queries. |
| `readings.py` | Canonical timestamps and the `out_of_range` flag. |
| `errors.py` | The error format and the messages. |
| `db.py` | Engine and session. Foreign keys are switched on for every connection. |
| `tests/` | `pytest` tests for every endpoint. |

## Notes

- Handlers are plain `def`, so FastAPI runs them in a thread pool. The request-update endpoint (SRV-5) must not block inside an `async def`: the simulator calls back into this same server while it runs.
- Timestamps are stored as UTC text in the form `2026-10-09T15:00:05Z` (second precision), so string order is time order. Input with another offset or with fractions of a second is normalised.
