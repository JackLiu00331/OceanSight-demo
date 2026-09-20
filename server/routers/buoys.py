"""Read endpoints for the dashboard (SRV-4)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import config
import repository
from db import get_session
from errors import ApiError
from readings import to_reading
from schemas import BuoyOut, ReadingOut

router = APIRouter(prefix="/api")


@router.get("/buoys", response_model=list[BuoyOut])
def list_buoys(session: Session = Depends(get_session)):
    result = []
    for buoy in repository.list_buoys(session):
        latest = repository.latest_reading(session, buoy.buoy_id)
        result.append(BuoyOut(
            buoy_id=buoy.buoy_id,
            name=buoy.name,
            status=buoy.status,
            location_lat=buoy.location_lat,
            location_lng=buoy.location_lng,
            latest_reading=to_reading(latest) if latest else None,
        ))
    return result


@router.get("/buoys/{buoy_id}/data", response_model=list[ReadingOut])
def buoy_data(
    buoy_id: str,
    limit: int = Query(config.HISTORY_LIMIT_DEFAULT, ge=1, le=config.HISTORY_LIMIT_MAX),
    session: Session = Depends(get_session),
):
    """The most recent `limit` readings, oldest first. A buoy with no data gives []."""
    if repository.get_buoy(session, buoy_id) is None:
        raise ApiError(404, f"unknown buoy_id: {buoy_id}")
    return [to_reading(row) for row in repository.recent_readings(session, buoy_id, limit)]
