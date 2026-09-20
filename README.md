# OceanSight

Simulated buoys → server → SQLite → dashboard. Ownership, schedule and the API contract are in [`../OceanSight_PM_Plan.md`](../OceanSight_PM_Plan.md); this file is the short version for running it.

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/) — uv installs the dependencies of the Python modules
- Node 20.19+ or 22.12+ (developed on Node 24)

## Run it

Four terminals, all from `OceanSight/`:

```
python database/init_db.py                       # once: creates database/oceansight.db with the five buoys
python database/backfill.py                      # optional: demo history, so the charts are not empty on first load
uv run --directory server uvicorn main:app --port 8000
uv run --directory simulator python main.py
npm --prefix frontend install                    # once
npm --prefix frontend run dev
```

Open <http://localhost:5173>. The server is on port 8000 and the simulator's control API on 8001.

## Try the simulator's control API

Send a reading right now, or one that trips the alert thresholds (`anomaly` is `none`, `temperature` or `pressure`):

```
curl -X POST "http://127.0.0.1:8001/simulate/BUOY-03?anomaly=temperature"
```

The reading is stored like any other and comes back from `GET /api/buoys/BUOY-03/data` with `"out_of_range": true`. The dashboard does not highlight it yet (FE-6, Sprint R1-3).

## Tests

```
uv run --directory server pytest
uv run --directory simulator python -m unittest
npm --prefix frontend run build                  # the frontend has no unit tests yet; this checks that it compiles
```

## Layout

| Directory | What | Owner |
|---|---|---|
| `server/` | FastAPI: ingest, validation, read API | Chao |
| `database/` | SQLite schema, seed data, init / backfill / performance scripts | Mohammad |
| `simulator/` | Buoy readings: scheduled loop and control API | Delon |
| `frontend/` | Vue 3 dashboard | Trey |

Each directory has its own README.
