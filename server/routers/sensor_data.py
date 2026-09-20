"""POST /api/sensor-data: ingest one reading from a buoy (SRV-1, SRV-2, SRV-3)."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import readings
import repository
from db import get_session
from errors import ApiError
from schemas import IngestOut, SensorDataIn

router = APIRouter(prefix="/api")
logger = logging.getLogger("oceansight_server")


@router.post("/sensor-data", status_code=201, response_model=IngestOut)
def receive_sensor_data(data: SensorDataIn, session: Session = Depends(get_session)):
    # Anything that reaches this point already passed the type, timezone and range checks.
    if repository.get_buoy(session, data.buoy_id) is None:
        raise ApiError(400, f"unknown buoy_id: {data.buoy_id}")
    try:
        row = repository.add_reading(
            session,
            buoy_id=data.buoy_id,
            timestamp=readings.format_utc(data.timestamp),
            temperature=data.temperature,
            pressure=data.pressure,
            received_at=readings.utc_now(),
        )
    except SQLAlchemyError:
        session.rollback()
        logger.exception("could not store reading %s", data.model_dump(mode="json"))
        raise ApiError(500, "failed to store reading") from None
    logger.info("stored reading id=%s %s", row.id, data.model_dump(mode="json"))
    return IngestOut(status="ok", id=row.id, received_at=row.received_at)
