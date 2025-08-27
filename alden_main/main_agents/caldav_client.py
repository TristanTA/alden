from caldav import DAVClient
from caldav import Calendar as Cal
from icalendar import Calendar, Event
from typing import Optional, Dict
import hashlib
from datetime import datetime

class AldenCalDAV:
    def __init__(self, base_url, username, password, calendar_name="Alden"):
        self.client = DAVClient(url=base_url, username=username, password=password)
        self.principal = self.client.principal()
        self.calendar_name = calendar_name
        self.calendar = self._ensure_calendar()

    def _ensure_calendar(self) -> Cal:
        for c in self.principal.calendars():
            name = getattr(c, 'name', None) or c.url.path.split('/')[-2]
            if name == self.calendar_name:
                return c
        return self.principal.make_calendar(self.calendar_name)

    def list_events(self, start: datetime, end: datetime):
        return self.calendar.date_search(start, end)  # returns event resources

    def _get_by_uid(self, uid: str):
        for ev in self.calendar.events():
            cal = Calendar.from_ical(ev.data)
            for comp in cal.walk('VEVENT'):
                if str(comp.get('UID')) == uid:
                    return ev, comp
        return None, None

    def create_event(self, summary: str, start: datetime, end: datetime, description: Optional[str] = None, uid: Optional[str]=None):
        if not uid:
            uid = hashlib.md5(f"{summary}{start}{end}".encode()).hexdigest() + "@alden"
        cal = Calendar(); cal.add('prodid','-//Alden//CalDAV//EN'); cal.add('version','2.0')
        ev = Event(); ev.add('uid', uid); ev.add('summary', summary); ev.add('dtstart', start); ev.add('dtend', end)
        if description: ev.add('description', description)
        cal.add_component(ev)
        self.calendar.add_event(cal.to_ical().decode())
        return uid

    def update_event(self, uid: str, patches: Dict):
        ev, comp = self._get_by_uid(uid)
        if not ev: raise ValueError("UID not found")
        if 'summary' in patches: comp['SUMMARY'] = patches['summary']
        if 'description' in patches: comp['DESCRIPTION'] = patches['description']
        if 'start' in patches: comp['DTSTART'] = patches['start']
        if 'end' in patches: comp['DTEND'] = patches['end']
        newcal = Calendar(); newcal.add('prodid','-//Alden//CalDAV//EN'); newcal.add('version','2.0'); newcal.add_component(comp)
        ev.data = newcal.to_ical().decode(); ev.save()

    def delete_event(self, uid: str):
        ev, _ = self._get_by_uid(uid)
        if ev: ev.delete(); return True
        return False