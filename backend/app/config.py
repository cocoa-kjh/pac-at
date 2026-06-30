from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    db_path: str = os.getenv("DB_PATH", str(BASE_DIR / "scheduler.db"))
    obs_host: str = os.getenv("OBS_HOST", "localhost")
    obs_port: int = int(os.getenv("OBS_PORT", "4455"))
    obs_password: str | None = os.getenv("OBS_PASSWORD") or None
    port: int = int(os.getenv("PORT", "8000"))
    client_secret_path: str = os.getenv(
        "CLIENT_SECRET_PATH",
        str(BASE_DIR.parent / "_doc" /
            "client_secret_95002751475-aa4krs09rj7ul96q80nbbn8dokc9t8v4.apps.googleusercontent.com.json"),
    )

settings = Settings()
