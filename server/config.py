"""Server configuration. Thresholds and value ranges live here and nowhere else (PM Plan 3.3)."""
import os
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]  # OceanSight/


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else CODE_ROOT / path


DB_PATH = _resolve(os.environ.get("OCEANSIGHT_DB", "database/oceansight.db"))

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Validity range: a value outside it is rejected with 400 and nothing is stored.
TEMPERATURE_VALID = (-5.0, 40.0)  # degrees C
PRESSURE_VALID = (0.0, 100.0)  # dbar

# Alert thresholds: a value outside them is accepted and stored, and flagged out_of_range.
TEMPERATURE_ALERT = (0.0, 30.0)
PRESSURE_ALERT = (10.0, 30.0)

HISTORY_LIMIT_DEFAULT = 50
HISTORY_LIMIT_MAX = 500
