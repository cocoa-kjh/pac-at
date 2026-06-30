### Task 0: 백엔드 프로젝트 초기화

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`

**Interfaces:**
- Produces: `app.config.settings` — `Settings` 인스턴스 (`db_path: str`, `obs_host: str`, `obs_port: int`, `obs_password: str | None`, `port: int`, `client_secret_path: str`)

- [ ] **Step 1: pyproject.toml 작성**

```toml
[project]
name = "yt-livestream-scheduler"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlalchemy>=2.0",
    "apscheduler>=3.10",
    "obsws-python>=1.6",
    "google-api-python-client>=2.120",
    "google-auth-oauthlib>=1.2",
    "python-dateutil>=2.9",
    "pydantic>=2.6",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27"]

[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
```

- [ ] **Step 2: config.py 작성**

```python
from dataclasses import dataclass
from pathlib import Path
import os

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
```

- [ ] **Step 3: 빈 `app/__init__.py`, `tests/__init__.py` 생성** (내용 없음)

- [ ] **Step 4: 의존성 설치 확인**

Run: `cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"`
Expected: 설치 성공, 에러 없음

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/app/config.py backend/tests/__init__.py
git commit -m "chore: 백엔드 프로젝트 스캐폴딩 및 설정"
```

---

## Phase 1 — 데이터 모델 & DB

