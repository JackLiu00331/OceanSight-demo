"""Create the OceanSight SQLite database from schema.sql and seed.sql (DB-1, DB-2).

    python database/init_db.py            create the database if it is missing; safe to re-run
    python database/init_db.py --reset    delete it first (development only)

The file is database/oceansight.db under OceanSight/, or OCEANSIGHT_DB if that is set
(a relative value is resolved against OceanSight/). Standard library only.
"""
import argparse
import os
import sqlite3
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent
CODE_ROOT = DATABASE_DIR.parent


def db_path() -> Path:
    path = Path(os.environ.get("OCEANSIGHT_DB", "database/oceansight.db"))
    return path if path.is_absolute() else CODE_ROOT / path


def create_database(path: Path, reset: bool = False) -> None:
    if reset:
        for suffix in ("", "-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        # WAL lets the server read while the simulator's readings are being written.
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript((DATABASE_DIR / "schema.sql").read_text(encoding="utf-8"))
        connection.executescript((DATABASE_DIR / "seed.sql").read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


def summary(path: Path) -> tuple:
    connection = sqlite3.connect(path)
    try:
        buoys = connection.execute("SELECT COUNT(*) FROM buoys").fetchone()[0]
        readings = connection.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    finally:
        connection.close()
    return buoys, readings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create the OceanSight SQLite database.")
    parser.add_argument("--reset", action="store_true", help="delete the existing database first (development only)")
    args = parser.parse_args(argv)
    path = db_path()
    create_database(path, reset=args.reset)
    buoys, readings = summary(path)
    print(f"database ready: {path}")
    print(f"  buoys: {buoys}, readings: {readings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
