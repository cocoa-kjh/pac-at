from datetime import datetime, timezone
from sqlalchemy import (Column, Integer, String, Text, DateTime, ForeignKey, Boolean)
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
    active = Column(Boolean, default=True, nullable=False)  # OBS에 현재 존재 여부 (sync 시 갱신, 행은 삭제 안 함)

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
    series_id = Column(Integer, ForeignKey("schedule_series.id"))  # 반복 시리즈에서 생성된 회차인 경우 설정
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    recurrence = Column(String, default="none")    # none/daily/weekly/...
    recurrence_rule = Column(Text)                 # RRULE (레거시 단일 스케줄 반복용, 신규는 ScheduleSeries 사용)
    status = Column(String, default="pending")     # pending/running/done/canceled
    broadcast = relationship("Broadcast", back_populates="schedules")
    series = relationship("ScheduleSeries", back_populates="schedules")
    items = relationship("SequenceItem", back_populates="schedule",
                         order_by="SequenceItem.order_index")


class ScheduleSeries(Base):
    """반복 방송의 템플릿. 실제 회차는 매번 새 Broadcast+Schedule로 생성되고,
    YouTube 스트림(stream_id/key)만 최초 1회 만들어 회차마다 재바인딩해서 재사용한다."""
    __tablename__ = "schedule_series"
    id = Column(Integer, primary_key=True)
    first_start_at = Column(DateTime, nullable=False)   # 최초 회차 시작 시각 (요일/시각 기준점)
    duration_seconds = Column(Integer, nullable=False)
    recurrence_rule = Column(Text, nullable=False)      # DTSTART 없는 순수 RRULE (예: FREQ=WEEKLY;BYDAY=MO)
    title_template = Column(String, nullable=False)     # "{date}" 치환 지원
    description_template = Column(Text, default="")
    privacy = Column(String, default="private")
    lead_time_days = Column(Integer, default=3, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    youtube_stream_id = Column(String)
    youtube_stream_key = Column(String)
    last_generated_start = Column(DateTime)
    generation_error = Column(Text)
    schedules = relationship("Schedule", back_populates="series")
    items = relationship("ScheduleSeriesItem", back_populates="series",
                         order_by="ScheduleSeriesItem.order_index")


class ScheduleSeriesItem(Base):
    """시리즈 회차 생성 시 SequenceItem으로 복제되는 템플릿 씬 편성."""
    __tablename__ = "schedule_series_item"
    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("schedule_series.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scene.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    duration_seconds = Column(Integer)
    series = relationship("ScheduleSeries", back_populates="items")
    scene = relationship("Scene")

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
