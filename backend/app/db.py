from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

def get_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

def _migrate(engine):
    """create_all은 기존 테이블에 새 컬럼을 추가하지 않으므로, 누락된 컬럼을 직접 보강."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "scene" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("scene")}
    if "active" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE scene ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1"))

    if "schedule" in insp.get_table_names():
        sched_cols = {c["name"] for c in insp.get_columns("schedule")}
        if "series_id" not in sched_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE schedule ADD COLUMN series_id INTEGER"))

def init_db(engine):
    Base.metadata.create_all(bind=engine)
    _migrate(engine)
    SessionLocal.configure(bind=engine)
