-- OceanSight database schema (SQLite). This file is the source of truth: the server's
-- ORM models mirror it, and the database is always created from it (PM Plan 3.7).
--
-- Timestamps are TEXT in one canonical form: YYYY-MM-DDTHH:MM:SSZ (UTC, second precision),
-- so string order is time order.

CREATE TABLE IF NOT EXISTS buoys (
    buoy_id      TEXT PRIMARY KEY,
    name         TEXT,
    location_lat REAL,
    location_lng REAL,
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- No UNIQUE (buoy_id, timestamp): a "request update" can land in the same second as a
-- scheduled reading, and duplicates are allowed.
CREATE TABLE IF NOT EXISTS sensor_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    buoy_id     TEXT NOT NULL REFERENCES buoys (buoy_id),
    timestamp   TEXT NOT NULL,  -- when the sensor took the reading (set by the simulator)
    temperature REAL NOT NULL,  -- degrees C
    pressure    REAL NOT NULL,  -- dbar
    received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))  -- when the server stored it
);

-- Serves "latest N readings for a buoy": WHERE buoy_id = ? ORDER BY timestamp DESC, id DESC.
CREATE INDEX IF NOT EXISTS idx_sensor_data_buoy_ts ON sensor_data (buoy_id, timestamp, id);
