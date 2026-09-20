"""Request and response bodies (PM Plan 3.5)."""
from pydantic import AwareDatetime, BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

import config


class SensorDataIn(BaseModel):
    """Body of POST /api/sensor-data."""

    buoy_id: str
    timestamp: AwareDatetime  # a time without a timezone is rejected
    # strict: a string such as "18.4" is rejected instead of converted
    temperature: float = Field(strict=True, ge=config.TEMPERATURE_VALID[0], le=config.TEMPERATURE_VALID[1])
    pressure: float = Field(strict=True, ge=config.PRESSURE_VALID[0], le=config.PRESSURE_VALID[1])

    @field_validator("timestamp", mode="before")
    @classmethod
    def _timestamp_must_be_text(cls, value):
        # Left alone, pydantic reads a number as a Unix time, so 12345 would be stored as 1970-01-01.
        if not isinstance(value, str):
            raise PydanticCustomError("timestamp_type", "timestamp must be an ISO-8601 string")
        return value


class IngestOut(BaseModel):
    status: str
    id: int
    received_at: str


class ReadingOut(BaseModel):
    id: int
    timestamp: str
    temperature: float
    pressure: float
    out_of_range: bool
    out_of_range_fields: list[str]


class BuoyOut(BaseModel):
    buoy_id: str
    name: str | None
    status: str
    location_lat: float | None
    location_lng: float | None
    latest_reading: ReadingOut | None
