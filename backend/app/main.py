from fastapi import FastAPI, Depends
from app.db import SessionLocal

app = FastAPI(title="YT Livestream Scheduler")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# 실제 ScheduleEngine은 lifespan에서 구성. 기본 의존성은 앱 상태에서 가져옴.
def get_engine_dep():
    return app.state.engine

def get_youtube_dep():
    return app.state.youtube

def get_obs_dep():
    return app.state.obs

from app.routers import broadcasts, scenes, schedules  # noqa: E402
app.include_router(broadcasts.router)
app.include_router(scenes.router)
app.include_router(schedules.router)
