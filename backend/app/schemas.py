from datetime import datetime
from pydantic import BaseModel

class BroadcastCreate(BaseModel):
    title: str
    description: str = ""
    privacy: str = "private"

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

class ScheduleOut(BaseModel):
    id: int
    broadcast_id: int
    start_at: datetime
    end_at: datetime
    recurrence: str
    status: str
    class Config: from_attributes = True
