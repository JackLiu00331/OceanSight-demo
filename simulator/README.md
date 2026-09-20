# simulator/ — Simulated Sensor Layer

Sends a reading per buoy to the server every few seconds, and has a small control API to send one on demand. The contract is `../../OceanSight_PM_Plan.md` §3.5 and §3.6.

## Run

From `OceanSight/` (the server should be running):

```
uv run --directory simulator python main.py
```

Every 5 seconds it sends one reading for each of BUOY-01 … BUOY-05 to the server. If the server is down or rejects a reading, it logs the error and carries on. The control API listens on <http://127.0.0.1:8001>.

Settings, all optional environment variables: `SERVER_URL` (default `http://127.0.0.1:8000`), `SIM_INTERVAL_SECONDS` (default `5`), `SIM_PORT` (default `8001`).

## Control API

```
curl -X POST "http://127.0.0.1:8001/simulate/BUOY-03"                      # a normal reading, right now
curl -X POST "http://127.0.0.1:8001/simulate/BUOY-03?anomaly=temperature"  # 32–38 °C: stored, and flagged out_of_range
curl -X POST "http://127.0.0.1:8001/simulate/BUOY-03?anomaly=pressure"     # 40–60 dbar
curl http://127.0.0.1:8001/health
```

`POST /simulate/{buoy_id}` answers `200 {"status":"ok","sent":{…},"server_status":201}`. It answers `404` for an unknown buoy, `400` for an unknown `anomaly`, and `502` if the server could not be reached or rejected the reading.

Not here yet: `POST /pause` and `POST /resume` (SIM-4, Sprint R1-3).

## One reading from the command line

Prints one JSON reading (Git Bash, macOS, Linux):

```
python simulator/generator.py BUOY-03
python simulator/generator.py BUOY-01 | curl -X POST http://127.0.0.1:8000/api/sensor-data -H "Content-Type: application/json" -d @-
```

## Test

```
uv run --directory simulator python -m unittest
```

## Files

| File | What |
|---|---|
| `generator.py` | The roster and baselines (§3.4), the normal band (§3.3), `make_reading()` for one reading, `Fleet` for the random walk, anomaly injection, and the command line above. |
| `main.py` | The process: the scheduled loop and the control API. |
| `test_generator.py`, `test_main.py` | Tests. The server is replaced by a stub, so no server is needed. |

## Notes

- Each buoy follows a random walk that is pulled back towards its baseline, clamped to the normal band (temperature 8–26 °C, pressure 12–28 dbar). An anomaly replaces one value in that one reading only.
- The timestamp is `datetime.now(timezone.utc)` with a trailing `Z`. `datetime.utcnow().isoformat()` has no timezone and the server rejects it.
- A round starts every `SIM_INTERVAL_SECONDS`, however long the previous round took.
- The default address is `127.0.0.1`, not `localhost`: on Windows `localhost` tries IPv6 first, which costs about 2 s per new connection.
