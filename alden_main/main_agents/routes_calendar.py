# alden/routers/caldav_routes.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from alden.caldav_client import AldenCalDAV, _tz

router = APIRouter(prefix="/caldav", tags=["caldav"])
cal = AldenCalDAV()

class CreateEventBody(BaseModel):
    summary: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    alarms_minutes: Optional[List[int]] = Field(default=None)
    rrule: Optional[str] = None
    categories: Optional[List[str]] = None
    x_alden: Optional[dict] = None

@router.post("/events")
def create_event(body: CreateEventBody):
    uid = cal.create_event(
        summary=body.summary,
        start=body.start,
        end=body.end,
        description=body.description,
        location=body.location,
        alarms_minutes=body.alarms_minutes,
        rrule=body.rrule,
        categories=body.categories,
        x_alden=body.x_alden,
    )
    return {"uid": uid}

@router.get("/events")
def list_events(day_start: datetime, day_end: datetime):
    return cal.list_events_between(day_start, day_end)

@router.patch("/events/{uid}")
def update_event(uid: str, patch: dict):
    cal.update_event(uid, patch)
    return {"ok": True}

@router.delete("/events/{uid}")
def delete_event(uid: str):
    cal.delete_event(uid)
    return {"ok": True}