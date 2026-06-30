from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

def get_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

def init_db(engine):
    Base.metadata.create_all(bind=engine)
    SessionLocal.configure(bind=engine)
