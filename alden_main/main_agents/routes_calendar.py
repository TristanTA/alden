from fastapi import APIRouter
from sqlalchemy.orm import sessionmaker
from dateutil import parser as dtparse
from alden_main.models.models_calendar import EventCache, ChangeLog
from alden_main.main_agents.caldav_client import AldenCalDAV

router = APIRouter(prefix="/calendar", tags=["calendar"])

def mount_calendar_routes(app, session_factory: sessionmaker, caldav: AldenCalDAV):
    @router.get("/events")
    def list_events(start: str, end: str):
        s = session_factory()
        q = (s.query(EventCache)
             .filter(EventCache.dtstart != None)
             .filter(EventCache.dtstart < dtparse.parse(end))
             .filter(EventCache.dtend > dtparse.parse(start))
             .order_by(EventCache.dtstart.asc()))
        out = [{"uid": r.uid, "summary": r.summary,
                "start": r.dtstart.isoformat() if r.dtstart else None,
                "end": r.dtend.isoformat() if r.dtend else None,
                "all_day": r.all_day, "tz": r.tzid, "etag": r.etag} for r in q.all()]
        s.close(); return out

    @router.post("/events")
    def create_event(summary: str, start: str, end: str, description: str = ""):
        uid = caldav.create_event(summary, dtparse.parse(start), dtparse.parse(end), description=description)
        s = session_factory(); s.add(ChangeLog(uid=uid, action="create", reason="api")); s.commit(); s.close()
        return {"ok": True, "uid": uid}

    @router.put("/events/{uid}")
    def update_event(uid: str, summary: str = None, start: str = None, end: str = None, description: str = None):
        patches = {}
        if summary is not None: patches["summary"] = summary
        if description is not None: patches["description"] = description
        if start is not None: patches["start"] = dtparse.parse(start)
        if end is not None: patches["end"] = dtparse.parse(end)
        caldav.update_event(uid, patches)
        return {"ok": True}

    @router.delete("/events/{uid}")
    def delete_event(uid: str):
        return {"ok": caldav.delete_event(uid)}

    app.include_router(router)