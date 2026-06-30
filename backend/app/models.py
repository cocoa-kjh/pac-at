from datetime import datetime, timezone
from sqlalchemy import (Column, Integer, String, Text, DateTime, ForeignKey)
from sqlalchemy.orm import relationship
from app.db import Base

def _utcnow():
    return datetime.now(timezone.utc)

class OAuthToken(Base):
    __tablename__ = "oauth_token"
    id = Column(Integer, primary_key=True)
    access_token = Column(Text)
    refresh_token = Column(Text)
    expiry = Column(DateTime)
    scopes = Column(Text)

class Scene(Base):
    __tablename__ = "scene"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    obs_scene_name = Column(String, nullable=False)
    note = Column(Text, default="")

class Broadcast(Base):
    __tablename__ = "broadcast"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    privacy = Column(String, default="private")   # public/unlisted/private
    youtube_broadcast_id = Column(String)
    youtube_stream_key = Column(String)
    status = Column(String, default="draft")       # draft/scheduled/live/completed/error
    schedules = relationship("Schedule", back_populates="broadcast")

class Schedule(Base):
    __tablename__ = "schedule"
    id = Column(Integer, primary_key=True)
    broadcast_id = Column(Integer, ForeignKey("broadcast.id"), nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    recurrence = Column(String, default="none")    # none/daily/weekly/...
    recurrence_rule = Column(Text)                 # RRULE
    status = Column(String, default="pending")     # pending/running/done/canceled
    broadcast = relationship("Broadcast", back_populates="schedules")
    items = relationship("SequenceItem", back_populates="schedule",
                         order_by="SequenceItem.order_index")

class SequenceItem(Base):
    __tablename__ = "sequence_item"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedule.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scene.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    duration_seconds = Column(Integer)             # None = end_at까지
    schedule = relationship("Schedule", back_populates="items")
    scene = relationship("Scene")

class RunLog(Base):
    __tablename__ = "run_log"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedule.id"))
    event = Column(String, nullable=False)
    detail = Column(Text, default="")
    timestamp = Column(DateTime, default=_utcnow)
