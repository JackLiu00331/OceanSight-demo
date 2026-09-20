"""Test setup: a throwaway database built from database/schema.sql and seed.sql.

The environment variable has to be set before `main` (and so `config`) is imported.
"""
import atexit
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

CODE_ROOT = Path(__file__).resolve().parents[2]
_folder = tempfile.mkdtemp(prefix="oceansight-test-")
atexit.register(shutil.rmtree, _folder, ignore_errors=True)
TEST_DB = Path(_folder) / "test.db"

_setup = sqlite3.connect(TEST_DB)
for name in ("schema.sql", "seed.sql"):
    _setup.executescript((CODE_ROOT / "database" / name).read_text(encoding="utf-8"))
_setup.close()
os.environ["OCEANSIGHT_DB"] = str(TEST_DB)

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


@pytest.fixture(autouse=True)
def empty_readings():
    connection = sqlite3.connect(TEST_DB)
    connection.execute("DELETE FROM sensor_data")
    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'sensor_data'")
    connection.commit()
    connection.close()


@pytest.fixture
def client():
    # Unhandled errors should come back as a 500 response, as they do under uvicorn.
    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def db():
    connection = sqlite3.connect(TEST_DB)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()
