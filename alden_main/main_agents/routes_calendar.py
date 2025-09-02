# alden_main/main_agents/routes_calendar.py
from __future__ import annotations

from datetime import datetime
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.requests import Request

from alden_main.main_agents.caldav_client import AldenCalDAV

router = APIRouter(prefix="/caldav", tags=["caldav"])


# ---------- App state accessors ----------
def get_caldav(request: Request) -> AldenCalDAV:
    caldav: AldenCalDAV = getattr(request.app.state, "caldav", None)
    if caldav is None:
        raise HTTPException(status_code=500, detail="CalDAV client not initialized")
    return caldav


def get_db(request: Request) -> Generator:
    """Yield a SQLAlchemy session if SessionLocal was provided at mount time."""
    SessionLocal = getattr(request.app.state, "SessionLocal", None)
    if SessionLocal is None:
        # You can remove this if you always mount with SessionLocal
        raise HTTPException(status_code=500, detail="DB SessionLocal not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Schemas ----------
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


# ---------- Routes ----------
@router.get("/health")
def health(caldav: AldenCalDAV = Depends(get_caldav)):
    # Light touch to verify connectivity without crashing
    try:
        _ = caldav.get_calendars()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/calendars")
def list_cals(caldav: AldenCalDAV = Depends(get_caldav)):
    return [getattr(c, "url", str(c)) for c in caldav.get_calendars()]


@router.post("/events")
def create_event(
    body: CreateEventBody,
    caldav: AldenCalDAV = Depends(get_caldav),
    # db: Session = Depends(get_db),  # uncomment if you use DB here
):
    uid = caldav.create_event(
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
def list_events(
    day_start: datetime,
    day_end: datetime,
    caldav: AldenCalDAV = Depends(get_caldav),
):
    return caldav.list_events_between(day_start, day_end)


@router.patch("/events/{uid}")
def update_event(
    uid: str,
    patch: dict,
    caldav: AldenCalDAV = Depends(get_caldav),
):
    caldav.update_event(uid, patch)
    return {"ok": True}


@router.delete("/events/{uid}")
def delete_event(
    uid: str,
    caldav: AldenCalDAV = Depends(get_caldav),
):
    caldav.delete_event(uid)
    return {"ok": True}


# ---------- Mount helper ----------
def mount_calendar_routes(app, SessionLocal, caldav: AldenCalDAV) -> None:
    """
    Attach CalDAV and DB to app.state and include this router.
    Call from main.py like:
        from alden_main.main_agents.routes_calendar import mount_calendar_routes
        mount_calendar_routes(app, SessionLocal, caldav)
    """
    app.state.caldav = caldav
    app.state.SessionLocal = SessionLocal  # optional but handy for future endpoints
    app.include_router(router)


__all__ = ["router", "mount_calendar_routes"]