"""Database access for the routers."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Buoy, SensorData


def get_buoy(session: Session, buoy_id: str) -> Buoy | None:
    return session.get(Buoy, buoy_id)


def list_buoys(session: Session) -> list[Buoy]:
    return list(session.scalars(select(Buoy).order_by(Buoy.buoy_id)))


def add_reading(session: Session, *, buoy_id: str, timestamp: str, temperature: float,
                pressure: float, received_at: str) -> SensorData:
    row = SensorData(buoy_id=buoy_id, timestamp=timestamp, temperature=temperature,
                     pressure=pressure, received_at=received_at)
    session.add(row)
    session.commit()
    return row


def latest_reading(session: Session, buoy_id: str) -> SensorData | None:
    statement = (
        select(SensorData)
        .where(SensorData.buoy_id == buoy_id)
        .order_by(SensorData.timestamp.desc(), SensorData.id.desc())
        .limit(1)
    )
    return session.scalars(statement).first()


def recent_readings(session: Session, buoy_id: str, limit: int) -> list[SensorData]:
    """The most recent `limit` readings, oldest first."""
    statement = (
        select(SensorData)
        .where(SensorData.buoy_id == buoy_id)
        .order_by(SensorData.timestamp.desc(), SensorData.id.desc())
        .limit(limit)
    )
    return list(reversed(list(session.scalars(statement))))
