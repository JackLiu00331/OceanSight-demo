"""Helpers for readings: canonical timestamps and the out-of-range flag."""
from datetime import datetime, timezone

import config
from models import SensorData
from schemas import ReadingOut


def format_utc(moment: datetime) -> str:
    """Canonical form: UTC, second precision, trailing Z (PM Plan 3.2)."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now() -> str:
    return format_utc(datetime.now(timezone.utc))


def out_of_range_fields(temperature: float, pressure: float) -> list[str]:
    fields = []
    if not config.TEMPERATURE_ALERT[0] <= temperature <= config.TEMPERATURE_ALERT[1]:
        fields.append("temperature")
    if not config.PRESSURE_ALERT[0] <= pressure <= config.PRESSURE_ALERT[1]:
        fields.append("pressure")
    return fields


def to_reading(row: SensorData) -> ReadingOut:
    fields = out_of_range_fields(row.temperature, row.pressure)
    return ReadingOut(
        id=row.id,
        timestamp=row.timestamp,
        temperature=row.temperature,
        pressure=row.pressure,
        out_of_range=bool(fields),
        out_of_range_fields=fields,
    )
