import asyncio, hashlib
from datetime import datetime, timedelta, timezone
from icalendar import Calendar
from alden_main.models.models_calendar import EventCache
from sqlalchemy.orm import Session

def _hash(ics: str) -> str:
    return hashlib.sha256(ics.encode()).hexdigest()

def _extract_dt(comp, key):
    val = comp.get(key)
    if not val: return None, 'UTC', False
    dt = val.dt
    if hasattr(dt, 'tzinfo') and dt.tzinfo: return dt, dt.tzinfo.tzname(None) or 'UTC', False
    # date-only (all-day)
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc), 'UTC', True

async def poll_loop(caldav, session_factory, seconds=60):
    while True:
        try:
            now = datetime.now(timezone.utc)
            start, end = now - timedelta(days=14), now + timedelta(days=90)
            resources = caldav.list_events(start, end)
            with session_factory() as s:
                for res in resources:
                    ics = res.data
                    h = _hash(ics)
                    etag = getattr(res, 'etag', '') or ''
                    url = str(getattr(res, 'url', ''))
                    cal = Calendar.from_ical(ics)
                    comps = [c for c in cal.walk('VEVENT')]
                    if not comps: continue
                    comp = comps[0]
                    uid = str(comp.get('UID'))
                    summary = str(comp.get('SUMMARY') or '')
                    dtstart, tzid, all_day = _extract_dt(comp, 'DTSTART')
                    dtend, _, _ = _extract_dt(comp, 'DTEND')

                    row = s.query(EventCache).filter_by(uid=uid).one_or_none()
                    if not row:
                        row = EventCache(href=url, uid=uid, etag=etag, summary=summary,
                                         dtstart=dtstart, dtend=dtend, tzid=tzid,
                                         all_day=all_day, content_hash=h, source='unknown')
                        s.add(row)
                    else:
                        if row.content_hash != h or row.etag != etag:
                            row.summary = summary; row.dtstart = dtstart; row.dtend = dtend
                            row.tzid = tzid; row.all_day = all_day; row.etag = etag; row.content_hash = h
                    s.commit()
        except Exception as e:
            print(f"[calendar poll] {e}")
        await asyncio.sleep(seconds)