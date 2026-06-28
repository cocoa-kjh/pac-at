# YouTube 라이브스트리밍 스케쥴러 — 설계 문서

- **작성일**: 2026-06-28
- **상태**: 승인됨 (구현 계획 대기)
- **범위**: 첫 번째 서브프로젝트 — 스케쥴 기반 라이브스트리밍 관리

## 1. 개요

로컬 맥에서 실행되는 개인용 웹앱. YouTube Live 방송 이벤트를 예약/생성하고,
지정한 시각에 OBS Studio를 WebSocket으로 제어해 송출을 자동으로 시작·종료한다.
고급 스케쥴링(반복, 방송별 씬 지정, 시퀀스 편성)을 지원한다.

본 프로젝트의 전체 비전은 (1) 스케쥴 기반 라이브스트리밍, (2) 영상 수집→편집→자동
업로드 파이프라인, (3) YouTube API 전반 대시보드의 세 서브프로젝트로 구성되며,
이 문서는 (1)을 다룬다. 각 서브프로젝트는 자체 spec → plan → 구현 사이클을 가진다.

### 결정 사항 요약
- 사용자: 개인 (단일 YouTube 계정, 로그인 불필요)
- 플랫폼: 웹앱
- 실행 환경: 로컬 맥 (localhost)
- 송출 방식: OBS WebSocket v5로 OBS 제어 (서버 직접 송출 아님)
- 영상 재생: 영상마다 별도 OBS 씬 사전 구성 → 씬 전환 방식
- 스트림 키: 방송별로 OBS에 자동 주입
- 스케쥴링: 고급 (반복 + 방송별 씬 지정 + 시퀀스 편성)

## 2. 기술 스택

| 영역 | 선택 |
|------|------|
| 프론트엔드 | React + Vite + TypeScript (SPA) |
| 백엔드 | Python + FastAPI |
| 스케쥴러 | APScheduler |
| 데이터 저장 | SQLite |
| OBS 연동 | obs-websocket v5 (obs-websocket-py) |
| YouTube 연동 | YouTube Data API v3 (OAuth 2.0) |

## 3. 아키텍처

```
Frontend (React+Vite+TS, :5173)
   │  REST + WebSocket(상태)
   ▼
Backend (FastAPI, :8000)
   ├─ REST API
   ├─ APScheduler (스케쥴 실행 엔진)
   ├─ SQLite (스케쥴/방송/씬/토큰)
   ├─ OBSClient  ──── OBS WebSocket(:4455) ──► OBS Studio ─► YouTube RTMP
   └─ YouTubeClient ─ YouTube Data API v3 ───► YouTube Live
```

핵심 흐름: 예약 시각 도래 → YouTube 방송 라이브 전환 → 스트림 키 OBS 주입 →
OBS 스트리밍 시작 + 씬 전환 → (시퀀스 진행) → 종료 시각 → OBS 중단 →
YouTube 방송 종료.

### 프로젝트 구조
```
Youtube/
├─ backend/   (FastAPI, APScheduler, SQLite, clients/)
├─ frontend/  (React+Vite+TS)
└─ docs/superpowers/specs/
```

## 4. 데이터 모델 (SQLite)

- **oauth_token** — YouTube 인증 토큰 1행: access_token, refresh_token, expiry, scopes
- **scene** — OBS 씬 매핑: id, name(표시명), obs_scene_name, note
- **broadcast** — 방송 정의(YouTube Live 이벤트): id, title, description,
  privacy(public/unlisted/private), youtube_broadcast_id, youtube_stream_key,
  status(draft/scheduled/live/completed/error)
- **schedule** — 스케쥴: id, broadcast_id(FK), start_at, end_at,
  recurrence(none/daily/weekly/...), recurrence_rule(RFC 5545 RRULE),
  status(pending/running/done/canceled)
- **sequence_item** — 편성(방송 내 씬 순서): id, schedule_id(FK), scene_id(FK),
  order_index, duration_seconds
- **run_log** — 실행 이력: id, schedule_id, event, detail, timestamp

고급 스케쥴링은 `schedule`(반복 규칙) + `sequence_item`(씬 순서·지속시간)으로 표현.
예: "월 20:00, 인트로 60초 → 메인 3600초 → 아웃트로 30초" = sequence_item 3개.

## 5. 스케쥴 실행 엔진 (APScheduler)

백엔드 시작 시 DB의 `pending` 스케쥴을 모두 등록, 변경 시 동적 재등록.

### 한 방송의 생명주기
1. **T-0 (start_at)**: YouTube broadcast를 'live'로 전환 → 스트림 키를 OBS에
   주입(SetStreamServiceSettings) → OBS StartStream → 첫 sequence_item 씬으로 전환
   → status=live, run_log 기록
2. **시퀀스 진행**: 각 item의 duration_seconds 후 다음 씬으로 전환
   (APScheduler one-off job으로 순차 실행)
3. **T-end (end_at 또는 마지막 시퀀스 종료)**: OBS StopStream → YouTube broadcast
   'complete' 전환 → status=completed, run_log 기록

### 설계 결정
- 각 단계는 독립 함수로 분리(`youtube_go_live()`, `obs_inject_stream_key()`,
  `obs_start_stream()`, `obs_switch_scene()`, `obs_stop_stream()`,
  `youtube_complete()`) → 단위 테스트 가능
- 반복 스케쥴: RRULE로 다음 발생 시각 계산 후 자동 재등록
- 재시작 복원력: DB에서 미완료 스케쥴 복원(best-effort), run_log로 상태 파악
- 사전 점검: 방송 시작 전 OBS 연결·YouTube 토큰 유효성 체크, 실패 시 알림
- 에러 처리: 단계 실패 시 status=error, run_log 상세 기록, 이미 시작된 스트림은
  안전하게 중단 시도(보상)

## 6. 외부 연동

### YouTube Data API v3 (OAuth 2.0)
- 인증: 프론트 "YouTube 연결" → /auth/youtube → Google 동의 →
  /auth/youtube/callback → refresh_token을 oauth_token에 저장 → access_token 만료
  시 자동 갱신
- 스코프: `youtube.force-ssl`
- 사용 엔드포인트: liveBroadcasts.insert / liveStreams.insert /
  liveBroadcasts.bind / liveBroadcasts.transition / liveBroadcasts.list
- **쿼터 절약**: 방송 이벤트는 예약 시점에 미리 생성, 실행 시점엔 transition만 호출
  (liveBroadcasts.insert는 쿼터 비용이 큼; 기본 일일 10,000 units)
- OAuth `client_secret` 파일은 `.gitignore` 처리, 토큰은 SQLite에 저장

### OBS WebSocket v5 (obs-websocket-py)
- 연결: ws://localhost:4455 (비밀번호 설정 시 인증)
- 사용 요청: GetSceneList / SetCurrentProgramScene / StartStream / StopStream /
  GetStreamStatus / SetStreamServiceSettings(스트림 키 자동 주입)
- 전제: 사용자가 OBS에 씬별 미디어 소스를 사전 구성. 스트리밍 출력의 RTMP 서버 +
  스트림 키는 백엔드가 방송별로 자동 주입

### 연동 설계 결정
- 각 연동은 독립 클라이언트 클래스(`YouTubeClient`, `OBSClient`)로 캡슐화 →
  외부 API 모킹으로 테스트 가능

## 7. 프론트엔드 UI

- **Dashboard**: 연결 상태(OBS/YouTube), 다음 예약 방송, 현재 LIVE 상태
- **Broadcasts**: 방송 생성/편집(제목·설명·공개범위), YouTube 이벤트 생성
- **Schedules**: 캘린더/리스트 뷰, 시작·종료 시각, 반복 규칙(RRULE),
  시퀀스 편성 에디터(씬 순서·지속시간 드래그앤드롭)
- **Scenes**: OBS 씬 목록 동기화, 표시명·메모 매핑
- **Settings**: OBS 연결 정보, YouTube 재인증, 로그 뷰
- 실시간 상태(LIVE 진행, 씬 전환)는 WebSocket 또는 폴링으로 업데이트

## 8. 테스트 전략 (TDD)

- **백엔드 단위**: YouTubeClient/OBSClient 모킹, 실행 엔진 각 단계 함수,
  RRULE 다음 시각 계산, 시퀀스 진행 로직
- **통합**: 인메모리 SQLite로 API 엔드포인트 + 스케쥴 등록/취소 흐름
- **프론트엔드**: Vitest로 컴포넌트, 폼 검증, API 클라이언트
- **수동 E2E**: 실제 OBS + 테스트용 private YouTube 방송으로 전체 흐름 검증

## 9. 보안

- `client_secret_*.json`, OAuth 토큰, `*.db`, `.env`는 `.gitignore`로 제외
- 토큰은 로컬 SQLite에만 저장 (로컬 개인 도구)

## 10. 범위 외 (YAGNI)

- 멀티 유저 / 권한 관리
- 클라우드 배포 / 외부 접속
- 서버 직접 FFmpeg 송출
- 영상 수집·편집·업로드 파이프라인 (별도 서브프로젝트)
- YouTube 통계/분석 대시보드 (별도 서브프로젝트)
