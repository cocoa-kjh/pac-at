# YT Livestream Scheduler (Backend) 설계 문서

## 1. 개요 (Overview)
본 프로젝트는 YouTube 실시간 스트리밍(Livestream)과 OBS Studio를 연동하여, 정해진 스케줄에 따라 자동으로 방송을 시작하고, 화면(장면, Scene)을 전환하며, 방송을 종료하는 자동화 시스템의 백엔드입니다. FastAPI를 기반으로 REST API를 제공하며, 내부적으로 APScheduler를 사용해 스케줄링을 처리합니다.

## 2. 주요 기술 스택 (Tech Stack)
- **Framework**: FastAPI (`main.py`, `routers/`)
- **Database**: SQLite (SQLAlchemy ORM 사용 - `db.py`, `models.py`)
- **Scheduler**: APScheduler (`scheduler/engine.py`)
- **OBS Control**: `obsws-python` (OBS WebSocket 통신 - `clients/obs_client.py`)
- **YouTube API**: `google-api-python-client`, `google-auth-oauthlib` (`clients/youtube_client.py`)

## 3. 시스템 아키텍처 (Architecture)
시스템은 크게 4가지 계층으로 나뉘어 작동합니다.
1. **REST API Layer (`routers/`)**: 클라이언트(프론트엔드)의 요청을 받아 Pydantic(`schemas.py`)으로 유효성을 검증하고, 비즈니스 로직 및 CRUD(`crud.py`) 작업을 수행합니다.
2. **Database Layer (`models.py`)**: 방송, 스케줄, 장면, OAuth 인증 정보 등의 메타데이터를 RDBMS에 영속적으로 저장합니다.
3. **Scheduler Engine Layer (`scheduler/engine.py`)**: DB에 저장된 `Schedule` 데이터를 바탕으로 특정 시간에 실행될 작업(방송 시작, 중간 장면 전환, 방송 종료)을 APScheduler 백그라운드 워커에 등록(Register)하고 실행합니다.
4. **Client Layer (`clients/`)**: 외부 시스템인 OBS Studio와 YouTube 서버에 직접 명령을 내리고 통신하는 역할을 합니다.

## 4. 데이터 모델 (Data Models)
주요 데이터베이스 엔티티는 다음과 같습니다.
- **`OAuthToken`**: YouTube API 사용을 위한 사용자 인증 토큰(Access Token, Refresh Token) 정보.
- **`Scene`**: OBS 내부의 장면(Scene) 이름과 시스템 내에서 관리할 식별자를 매핑.
- **`Broadcast`**: YouTube 방송 자체의 메타데이터(제목, 설명, 공개 여부, YouTube 내부 Broadcast ID 및 Stream ID).
- **`Schedule`**: 특정 Broadcast가 실제 송출될 시간(start_at, end_at) 및 반복(Recurrence - RRULE 형식) 정보.
- **`SequenceItem`**: 하나의 Schedule 내에서 시간 흐름에 따라 전환될 Scene들의 순서(order_index)와 해당 장면을 유지할 시간(duration_seconds).
- **`RunLog`**: 스케줄러가 실행한 내역(방송 시작, 종료, 실패 등)을 기록하는 로그 테이블.

## 5. 핵심 비즈니스 로직 (Core Business Logic)

### 5.1 방송 스케줄링 프로세스
1. 클라이언트(사용자)가 특정 방송(Broadcast)에 대한 스케줄(Schedule)을 생성하고, 방송 중 사용할 장면 순서(SequenceItem)를 설정합니다.
2. `ScheduleEngine.register()`가 호출되어 APScheduler에 세 종류의 작업(Job)을 예약합니다:
   - **`run_date = start_at`**: `go_live` 작업 실행. (OBS에 스트림 키 설정 및 방송 송출 시작, YouTube 상태 변경, 첫 번째 장면 전환)
   - **`run_date = start_at + 누적 offset`**: 각 `SequenceItem`의 `duration_seconds`에 맞춰 중간 `switch_to_item` 작업(OBS 장면 전환)들을 순차 예약.
   - **`run_date = end_at`**: `go_complete` 작업 실행. (OBS 송출 중단 및 YouTube 방송 종료)
3. 만약 스케줄에 **반복(RRULE)**이 설정되어 있다면, `go_complete` 처리 마지막에 `next_occurrence()`를 통해 다음 실행 시각을 계산하여 DB 일정을 업데이트하고 새 작업을 스케줄러에 재등록(Reschedule)합니다.

### 5.2 OBS Studio 연동 (`OBSClient`)
- OBS WebSocket API(`obsws-python`)를 통해 OBS Studio와 통신합니다.
- 스케줄이 시작될 때 YouTube API로부터 받은 RTMP URL과 Stream Key를 OBS의 `rtmp_custom` 설정에 주입(`set_stream_key`)하고, 실제 송출을 명령(`start_stream`, `stop_stream`)합니다.
- 지정된 시간에 OBS 화면을 변경(`switch_scene`)하여 방송의 흐름을 자동화합니다.

### 5.3 YouTube 연동 (`YouTubeClient`)
- OAuth 2.0을 통해 인증된 세션으로 YouTube Data API v3(LiveBroadcasts, LiveStreams)를 호출합니다.
- 방송 예약 시 YouTube에 Broadcast 엔티티와 Stream 엔티티를 생성하고 둘을 바인딩(bind)합니다.
- 실제 방송 송출 시간에 맞춰 YouTube 측 방송 상태를 'testing' -> 'live' -> 'complete' 순서로 트랜지션 처리합니다.

## 6. 디렉토리 구조 (Directory Structure)
```
backend/
├── app/
│   ├── clients/        # OBS, YouTube 외부 통신 클라이언트 계층
│   │   ├── obs_client.py
│   │   └── youtube_client.py
│   ├── routers/        # FastAPI 엔드포인트(API 라우팅)
│   ├── scheduler/      # 작업 예약 엔진 및 실제 실행 스텝 로직
│   │   ├── engine.py       # 스케줄 등록/관리 메인 엔진
│   │   ├── recurrence.py   # 반복 일정(RRULE) 계산
│   │   └── steps.py        # 엔진이 호출하는 단일 작업(go_live 등) 구현
│   ├── config.py       # Pydantic BaseSettings 기반 환경변수 관리
│   ├── crud.py         # 데이터베이스 CRUD 헬퍼 함수
│   ├── db.py           # SQLAlchemy 엔진 및 세션 팩토리 설정
│   ├── main.py         # FastAPI 애플리케이션 진입점 및 Lifespan(초기화)
│   ├── models.py       # 데이터베이스 ORM 스키마 선언
│   └── schemas.py      # 요청/응답 Pydantic 유효성 검증 모델
├── pyproject.toml      # 패키지 의존성 및 프로젝트 메타 정보 (Poetry/Pipenv 호환)
└── scheduler.db        # 로컬 SQLite 데이터베이스 파일
```
