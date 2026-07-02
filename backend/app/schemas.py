from datetime import datetime
from pydantic import BaseModel

class BroadcastCreate(BaseModel):
    title: str
    description: str = ""
    privacy: str = "private"

class BroadcastUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    privacy: str | None = None

class BroadcastOut(BroadcastCreate):
    id: int
    youtube_broadcast_id: str | None = None
    status: str
    class Config: from_attributes = True

class SceneCreate(BaseModel):
    name: str
    obs_scene_name: str
    note: str = ""

class SceneOut(SceneCreate):
    id: int
    active: bool = True
    class Config: from_attributes = True

class SequenceItemIn(BaseModel):
    scene_id: int
    order_index: int
    duration_seconds: int | None = None

class ScheduleCreate(BaseModel):
    broadcast_id: int
    start_at: datetime
    end_at: datetime
    recurrence: str = "none"
    recurrence_rule: str | None = None
    items: list[SequenceItemIn] = []

class ScheduleUpdate(BaseModel):
    broadcast_id: int | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    recurrence: str | None = None
    recurrence_rule: str | None = None
    items: list[SequenceItemIn] | None = None   # None = 시퀀스 유지, []나 값 = 전체 교체

class ScheduleOut(BaseModel):
    id: int
    broadcast_id: int
    series_id: int | None = None
    start_at: datetime
    end_at: datetime
    recurrence: str
    recurrence_rule: str | None = None
    status: str
    items: list[SequenceItemIn] = []
    class Config: from_attributes = True


class SeriesCreate(BaseModel):
    first_start_at: datetime
    duration_seconds: int
    recurrence_rule: str          # DTSTART 없는 순수 RRULE, 예: "FREQ=WEEKLY;BYDAY=MO"
    title_template: str           # "{date}" 치환 가능
    description_template: str = ""
    privacy: str = "private"
    lead_time_days: int = 3
    items: list[SequenceItemIn] = []

class SeriesUpdate(BaseModel):
    recurrence_rule: str | None = None
    duration_seconds: int | None = None
    title_template: str | None = None
    description_template: str | None = None
    privacy: str | None = None
    lead_time_days: int | None = None
    active: bool | None = None
    items: list[SequenceItemIn] | None = None

class SeriesOut(BaseModel):
    id: int
    first_start_at: datetime
    duration_seconds: int
    recurrence_rule: str
    title_template: str
    description_template: str
    privacy: str
    lead_time_days: int
    active: bool
    youtube_stream_id: str | None = None
    last_generated_start: datetime | None = None
    generation_error: str | None = None
    items: list[SequenceItemIn] = []
    class Config: from_attributes = True
