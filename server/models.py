"""ORM models. They mirror database/schema.sql, which is the source of truth."""
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Buoy(Base):
    __tablename__ = "buoys"

    buoy_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str | None]
    location_lat: Mapped[float | None]
    location_lng: Mapped[float | None]
    status: Mapped[str]
    created_at: Mapped[str]


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    buoy_id: Mapped[str] = mapped_column(ForeignKey("buoys.buoy_id"))
    timestamp: Mapped[str]  # canonical UTC text, e.g. 2026-10-09T15:00:05Z
    temperature: Mapped[float]
    pressure: Mapped[float]
    received_at: Mapped[str]
