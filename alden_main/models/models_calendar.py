from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, UniqueConstraint
from sqlalchemy.sql import func

Base = declarative_base()

class EventCache(Base):
    __tablename__ = "event_cache"
    id = Column(Integer, primary_key=True)
    href = Column(String, unique=True)          # CalDAV resource URL
    uid = Column(String, index=True)
    etag = Column(String, index=True)
    summary = Column(String)
    dtstart = Column(DateTime(timezone=True))
    dtend = Column(DateTime(timezone=True))
    all_day = Column(Boolean, default=False)
    tzid = Column(String)
    content_hash = Column(String)
    source = Column(String)                      # 'alden'|'ios'|'unknown'
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    __table_args__ = (UniqueConstraint('uid', name='uc_uid'),)

class EventMeta(Base):
    __tablename__ = "event_meta"
    id = Column(Integer, primary_key=True)
    uid = Column(String, index=True)
    habit_id = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    priority = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class ChangeLog(Base):
    __tablename__ = "calendar_change_log"
    id = Column(Integer, primary_key=True)
    uid = Column(String, index=True)
    action = Column(String)   # 'create'|'update'|'delete'|'move'
    old_time = Column(String, nullable=True)
    new_time = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    at = Column(DateTime(timezone=True), server_default=func.now())