"""Simulator process (SIM-2, SIM-3): scheduled readings plus a small control API.

    uv run python main.py        (from OceanSight/simulator)

Every SIM_INTERVAL_SECONDS it sends one reading per buoy to the server. The control API
(default port 8001) sends a reading right now, optionally an anomalous one.
"""
import logging
import os
import threading
from contextlib import asynccontextmanager
from time import monotonic

import httpx
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

import generator

# 127.0.0.1, not localhost: on Windows "localhost" tries IPv6 first, which costs about 2 s per new connection.
SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
INTERVAL_SECONDS = float(os.environ.get("SIM_INTERVAL_SECONDS", "5"))
CONTROL_PORT = int(os.environ.get("SIM_PORT", "8001"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # it logs every request; our own lines are enough
logger = logging.getLogger("oceansight_simulator")


def send_reading(client: httpx.Client, server_url: str, reading: dict) -> tuple:
    """POST one reading to the server. Returns (status_code, detail); never raises."""
    try:
        response = client.post(f"{server_url}/api/sensor-data", json=reading)
    except httpx.HTTPError as exc:
        return None, f"server unreachable: {exc}"
    if response.status_code == 201:
        return 201, "ok"
    try:
        detail = response.json()["message"]
    except (ValueError, KeyError, TypeError):
        detail = response.text[:200]
    return response.status_code, f"HTTP {response.status_code}: {detail}"


def run_round(fleet: generator.Fleet, client: httpx.Client, server_url: str) -> int:
    """Send one reading per buoy. Failures are logged and skipped. Returns how many were stored."""
    stored = 0
    for buoy_id in generator.BUOYS:
        reading = fleet.next_reading(buoy_id)
        status, detail = send_reading(client, server_url, reading)
        if status == 201:
            stored += 1
            logger.info("sent %s temperature=%.2f pressure=%.2f", buoy_id, reading["temperature"], reading["pressure"])
        else:
            logger.error("could not send %s reading: %s", buoy_id, detail)
    return stored


def run_loop(fleet, client, server_url, interval, stop: threading.Event) -> None:
    while not stop.is_set():
        started = monotonic()
        try:
            run_round(fleet, client, server_url)
        except Exception:
            logger.exception("round failed; carrying on")
        # A round starts every `interval` seconds, however long the previous one took.
        stop.wait(max(0.0, interval - (monotonic() - started)))


def error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"status": "error", "message": message})


def create_app(server_url=SERVER_URL, interval=INTERVAL_SECONDS, client=None, start_loop=True) -> FastAPI:
    fleet = generator.Fleet()
    http = client or httpx.Client(timeout=3.0)
    stop = threading.Event()

    @asynccontextmanager
    async def lifespan(_app):
        if start_loop:
            logger.info("sending a reading per buoy to %s every %g s", server_url, interval)
            threading.Thread(
                target=run_loop, args=(fleet, http, server_url, interval, stop),
                daemon=True, name="scheduled-readings",
            ).start()
        yield
        stop.set()

    app = FastAPI(title="OceanSight Simulator", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "interval_seconds": interval, "paused": False}

    @app.post("/simulate/{buoy_id}")
    def simulate(buoy_id: str, anomaly: str = Query("none")):
        """Generate one reading for this buoy now and send it to the server."""
        if buoy_id not in generator.BUOYS:
            return error(404, f"unknown buoy_id: {buoy_id}")
        if anomaly not in generator.ANOMALIES:
            return error(400, f"unknown anomaly: {anomaly} (expected one of: {', '.join(generator.ANOMALIES)})")
        reading = fleet.next_reading(buoy_id, anomaly)
        status, detail = send_reading(http, server_url, reading)
        if status != 201:
            logger.error("on-demand %s reading failed: %s", buoy_id, detail)
            return error(502, detail)
        logger.info("on-demand %s reading (anomaly=%s): %s", buoy_id, anomaly, reading)
        return {"status": "ok", "sent": reading, "server_status": status}

    return app


if __name__ == "__main__":
    uvicorn.run(create_app(), host="127.0.0.1", port=CONTROL_PORT, log_level="warning")
