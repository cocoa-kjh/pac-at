from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.db import SessionLocal, get_engine, init_db
from app.config import settings
from app.clients.obs_client import OBSClient
from app.scheduler.engine import ScheduleEngine

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_engine_dep():
    return app.state.engine

def get_youtube_dep():
    return app.state.youtube

def get_obs_dep():
    return app.state.obs

def setup_logging():
    import logging
    try:
        from uvicorn.logging import ColourizedFormatter, AccessFormatter
    except ImportError:
        return
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            formatter = handler.formatter
            if not formatter:
                continue
            is_access = name == "uvicorn.access"
            if is_access:
                new_fmt = '[%(asctime)s] %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
                new_formatter = AccessFormatter(
                    fmt=new_fmt,
                    datefmt="%Y-%m-%d %H:%M:%S",
                    use_colors=getattr(formatter, "use_colors", None)
                )
            else:
                new_fmt = '[%(asctime)s] %(levelprefix)s %(message)s'
                new_formatter = ColourizedFormatter(
                    fmt=new_fmt,
                    datefmt="%Y-%m-%d %H:%M:%S",
                    use_colors=getattr(formatter, "use_colors", None)
                )
            handler.setFormatter(new_formatter)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    engine = get_engine(settings.db_path)

    init_db(engine)
    obs = OBSClient(settings.obs_host, settings.obs_port, settings.obs_password)
    try:
        obs.connect()
    except Exception:
        pass
    app.state.obs = obs
    app.state.youtube = _build_youtube_client()
    scheduler = BackgroundScheduler(); scheduler.start()
    app.state.engine = ScheduleEngine(scheduler, obs, app.state.youtube, SessionLocal)
    app.state.engine.load_pending()
    scheduler.add_job(_run_generate_pending_series, "interval", hours=6,
                      id="series:generate_pending", next_run_time=datetime.now())
    yield
    scheduler.shutdown(wait=False)

def _run_generate_pending_series():
    """활성 반복 시리즈들의 lead_time 이내 회차를 생성한다 (신규 YouTube 이벤트 생성 포함)."""
    from app.scheduler.series import generate_all_pending
    db = SessionLocal()
    try:
        generate_all_pending(db, app.state.youtube, app.state.engine)
    finally:
        db.close()

def _build_youtube_client():
    from app.routers.auth import load_credentials
    from app.clients.youtube_client import build_youtube, YouTubeClient
    db = SessionLocal()
    try:
        creds = load_credentials(db)
        return YouTubeClient(build_youtube(creds)) if creds else None
    finally:
        db.close()

app = FastAPI(title="YT Livestream Scheduler", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(localhost|192\.168\.\d+\.\d+):8101",
                   allow_methods=["*"], allow_headers=["*"])

from app.routers import broadcasts, scenes, schedules, auth, status, series  # noqa: E402
app.include_router(broadcasts.router)
app.include_router(scenes.router)
app.include_router(schedules.router)
app.include_router(auth.router)
app.include_router(status.router)
app.include_router(series.router)
