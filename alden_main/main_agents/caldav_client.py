import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

import pytz
from dateutil import tz
from icalendar import Calendar, Event, Alarm, vText
from caldav import DAVClient, Calendar as CalDAVCalendar, Principal
from caldav.lib.error import NotFoundError
from caldav.objects import Principal

# -----------------------------
# Config helpers
# -----------------------------
CALDAV_URL = os.getenv("CALDAV_URL", "http://localhost:5232")
CALDAV_USER = os.getenv("CALDAV_USER", "")
CALDAV_PASS = os.getenv("CALDAV_PASS", "")
DEFAULT_CAL_NAME = os.getenv("CALDAV_CAL_NAME", "Alden")
DEFAULT_TZ = os.getenv("ALDEN_TZ", "America/Boise")

def _tz():
    # pytz for iCalendar’s expectations
    return pytz.timezone(DEFAULT_TZ)

# -----------------------------
# Core client
# -----------------------------
class AldenCalDAV:
    def __init__(self,
                 url: str = CALDAV_URL,
                 username: str = CALDAV_USER,
                 password: str = CALDAV_PASS,
                 calendar_name: str = DEFAULT_CAL_NAME):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.calendar_name = calendar_name

        self.client = DAVClient(self.url, username=self.username, password=self.password)
        self.principal: Principal = self.client.principal()
        self.calendar: CalDAVCalendar = self._ensure_calendar(self.calendar_name)

    def _ensure_connected(self):
        if self._client is None:
            self._client = DAVClient(
                url=self.url,
                username=self.username,
                password=self.password,
                # keep default verify=True for HTTPS; irrelevant for HTTP
            )
        if self._principal is None:
            # This triggers a real request; wrap for nice errors
            self._principal = self._client.principal()

    def get_calendars(self):
        self._ensure_connected()
        return self._principal.calendars()

    # Create or fetch the working calendar
    def _ensure_calendar(self, name: str) -> CalDAVCalendar:
        calendars = self.principal.calendars()
        for c in calendars:
            try:
                props = c.get_properties([("{DAV:}", "displayname")])
                disp = props.get(("{DAV:}", "displayname"))
                # displayname may be bytes or str depending on server/back-end
                if (isinstance(disp, bytes) and disp.decode() == name) or disp == name:
                    return c
            except Exception:
                pass

        # Not found → create one
        new_cal = self.principal.make_calendar(name)
        return new_cal

    # -------------------------
    # ICS helpers
    # -------------------------
    def _build_ics(self,
                   summary: str,
                   start: datetime,
                   end: datetime,
                   description: Optional[str] = None,
                   location: Optional[str] = None,
                   uid: Optional[str] = None,
                   alarms_minutes: Optional[List[int]] = None,
                   rrule: Optional[str] = None,
                   categories: Optional[List[str]] = None,
                   x_alden: Optional[Dict[str, str]] = None) -> bytes:
        tzinfo = _tz()
        start = start.astimezone(tzinfo)
        end = end.astimezone(tzinfo)

        cal = Calendar()
        cal.add("prodid", "-//Alden//CalDAV//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")

        ev = Event()
        ev.add("uid", uid or str(uuid.uuid4()))
        ev.add("summary", vText(summary))
        ev.add("dtstart", start)
        ev.add("dtend", end)
        ev.add("dtstamp", datetime.now(tzinfo))
        if description:
            ev.add("description", vText(description))
        if location:
            ev.add("location", vText(location))
        if categories:
            ev.add("categories", categories)
        if rrule:
            # e.g., "FREQ=DAILY;COUNT=5" or "FREQ=WEEKLY;BYDAY=MO,WE,FR"
            ev.add("rrule", rrule)

        # Optional reminders
        if alarms_minutes:
            for m in alarms_minutes:
                a = Alarm()
                a.add("action", "DISPLAY")
                a.add("description", "Reminder")
                a.add("trigger", timedelta(minutes=-abs(m)))
                ev.add_component(a)

        # Custom vendor fields (Alden can tag & later parse)
        if x_alden:
            for k, v in x_alden.items():
                ev.add(f"X-ALDEN-{k.upper()}", v)

        cal.add_component(ev)
        return cal.to_ical()

    # -------------------------
    # CRUD
    # -------------------------
    def create_event(self,
                     summary: str,
                     start: datetime,
                     end: datetime,
                     description: Optional[str] = None,
                     location: Optional[str] = None,
                     uid: Optional[str] = None,
                     alarms_minutes: Optional[List[int]] = None,
                     rrule: Optional[str] = None,
                     categories: Optional[List[str]] = None,
                     x_alden: Optional[Dict[str, str]] = None) -> str:
        ics = self._build_ics(summary, start, end, description, location, uid,
                              alarms_minutes, rrule, categories, x_alden)
        ev = self.calendar.add_event(ics)
        return ev.icalendar_instance["UID"]

    def get_event_by_uid(self, uid: str):
        # Radicale supports searching; simplest is to iterate events and match UID
        for e in self.calendar.events():
            try:
                cal = e.icalendar_instance
                if "UID" in cal.subcomponents[0]:
                    if str(cal.subcomponents[0]["UID"]) == uid:
                        return e
            except Exception:
                continue
        raise NotFoundError("Event with UID not found")

    def update_event(self, uid: str, patch: Dict[str, Any]) -> None:
        """
        patch keys supported:
        summary, description, location, start, end, rrule, alarms_minutes (list[int]),
        categories (list[str]), x_alden (dict[str,str])
        """
        ev = self.get_event_by_uid(uid)
        cal = ev.icalendar_instance
        comp = cal.subcomponents[0]

        # Replace fields if present
        tzinfo = _tz()
        if "summary" in patch:
            comp["SUMMARY"] = vText(patch["summary"])
        if "description" in patch:
            comp["DESCRIPTION"] = vText(patch["description"] or "")
        if "location" in patch:
            comp["LOCATION"] = vText(patch["location"] or "")
        if "start" in patch:
            comp["DTSTART"] = patch["start"].astimezone(tzinfo)
        if "end" in patch:
            comp["DTEND"] = patch["end"].astimezone(tzinfo)
        if "rrule" in patch:
            if patch["rrule"]:
                comp["RRULE"] = patch["rrule"]
            elif "RRULE" in comp:
                del comp["RRULE"]
        if "categories" in patch:
            if patch["categories"]:
                comp["CATEGORIES"] = patch["categories"]
            elif "CATEGORIES" in comp:
                del comp["CATEGORIES"]

        if "alarms_minutes" in patch:
            # wipe existing VALARMs and add new
            comp.subcomponents = [c for c in comp.subcomponents if c.name != "VALARM"]
            if patch["alarms_minutes"]:
                for m in patch["alarms_minutes"]:
                    a = Alarm()
                    a.add("action", "DISPLAY")
                    a.add("description", "Reminder")
                    a.add("trigger", timedelta(minutes=-abs(m)))
                    comp.add_component(a)

        if "x_alden" in patch:
            # remove prior X-ALDEN-* then add
            for k in list(comp.keys()):
                if k.startswith("X-ALDEN-"):
                    del comp[k]
            for k, v in (patch["x_alden"] or {}).items():
                comp.add(f"X-ALDEN-{k.upper()}", v)

        ev.data = cal.to_ical()
        ev.save()

    def delete_event(self, uid: str) -> None:
        ev = self.get_event_by_uid(uid)
        ev.delete()

    # -------------------------
    # Queries
    # -------------------------
    def list_events_between(self,
                            start: datetime,
                            end: datetime) -> List[Dict[str, Any]]:
        """Return minimal dicts (fast + easy for planning)."""
        results = []
        tzinfo = _tz()
        start = start.astimezone(tzinfo)
        end = end.astimezone(tzinfo)
        for e in self.calendar.date_search(start, end):
            try:
                cal = e.icalendar_instance
                comp = cal.subcomponents[0]
                results.append({
                    "uid": str(comp.get("UID")),
                    "summary": str(comp.get("SUMMARY", "")),
                    "start": comp.get("DTSTART").dt,
                    "end": comp.get("DTEND").dt,
                    "location": str(comp.get("LOCATION", "")) if comp.get("LOCATION") else "",
                    "description": str(comp.get("DESCRIPTION", "")) if comp.get("DESCRIPTION") else "",
                    "rrule": str(comp.get("RRULE")) if comp.get("RRULE") else None,
                    "categories": list(comp.get("CATEGORIES", [])) if comp.get("CATEGORIES") else [],
                    "x_alden": {k[8:].lower(): str(comp.get(k)) for k in comp.keys() if k.startswith("X-ALDEN-")},
                })
            except Exception:
                continue
        return results

    def sync_token(self) -> Optional[str]:
        """Get or initialize sync token (if server supports it)."""
        try:
            return self.calendar.get_sync_token()
        except Exception:
            return None

    def sync_changes(self, token: Optional[str]) -> Tuple[Optional[str], Dict[str, List[str]]]:
        """
        Incremental sync—returns (new_token, {"added":[uids], "modified":[uids], "deleted":[uids]}).
        Falls back to full scan if not supported.
        """
        try:
            resp = self.calendar.sync(sync_token=token)
            # caldav lib returns raw response; normalize best-effort
            added, modified, deleted = [], [], []
            for ch in resp:
                try:
                    e = ch["href"]
                    # Fetch UID:
                    ev = self.client.calendar(self.calendar.url).event_by_url(e)
                    cal = ev.icalendar_instance
                    uid = str(cal.subcomponents[0]["UID"])
                    status = ch.get("status")
                    if status == "201":
                        added.append(uid)
                    elif status in ("200", "204"):
                        modified.append(uid)
                except Exception:
                    # Deleted events might not resolve
                    if "href" in ch and ch.get("status") == "404":
                        deleted.append(ch["href"])
            return self.calendar.get_sync_token(), {"added": added, "modified": modified, "deleted": deleted}
        except Exception:
            # Fallback: no delta—return everything as "modified"
            all_uids = []
            for e in self.calendar.events():
                try:
                    cal = e.icalendar_instance
                    all_uids.append(str(cal.subcomponents[0]["UID"]))
                except Exception:
                    pass
            return None, {"added": [], "modified": all_uids, "deleted": []}