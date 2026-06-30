### Task 12: README & 수동 E2E 절차

**Files:**
- Create: `README.md`
- Create: `backend/.env.example`

**Interfaces:** 없음 (문서)

- [ ] **Step 1: backend/.env.example 작성**

```
# OBS WebSocket 비밀번호 (OBS > 도구 > WebSocket 서버 설정)
OBS_PASSWORD=
# 기본값이 맞으면 비워둠
OBS_HOST=localhost
OBS_PORT=4455
PORT=8000
```

- [ ] **Step 2: README.md 작성**

```markdown
# YouTube 라이브스트리밍 스케쥴러

로컬 맥에서 YouTube Live 방송을 예약하고 OBS를 자동 제어해 송출/종료한다.

## 사전 준비
1. OBS Studio 설치, 도구 > WebSocket 서버 설정에서 서버 활성화 (포트 4455)
2. 송출할 영상마다 씬을 만들고 미디어 소스 추가
3. Google Cloud 프로젝트에 OAuth 동의화면 + 본인 계정을 테스트 사용자로 등록
4. `_doc/client_secret_*.json` 위치 확인 (이미 존재)

## 실행
백엔드:
    cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/uvicorn app.main:app --port 8000
프론트엔드:
    cd frontend && npm install && npm run dev
브라우저에서 http://localhost:5173 접속.

## 최초 1회: YouTube 연결
설정 페이지 > "YouTube 연결" 클릭 → Google 동의 → 자동 복귀.

## 사용 흐름
1. 씬 페이지 > "OBS 씬 동기화"
2. 방송 페이지 > 방송 생성 > "YouTube 이벤트 생성"
3. 스케쥴 페이지 > 방송 선택, 시작/종료 시각, 시퀀스 편성 > 스케쥴 생성
4. 지정 시각에 자동으로 송출 시작 → 씬 전환 → 종료

## 테스트
    cd backend && .venv/bin/pytest
    cd frontend && npm test

## 수동 E2E (실제 OBS + private 방송)
1. private 방송으로 스케쥴 생성, 시작 시각을 2분 후로 설정
2. OBS 실행 상태 유지
3. 시작 시각에 OBS 스트리밍 시작 + 씬 전환 확인
4. YouTube 스튜디오에서 라이브 수신 확인
5. 종료 시각에 스트림 중단 + 방송 완료 확인
6. run_log 테이블에서 단계별 기록 확인
```

- [ ] **Step 3: 전체 테스트 최종 확인**

Run: `cd backend && .venv/bin/pytest && cd ../frontend && npm test`
Expected: 백엔드/프론트 모두 PASS

- [ ] **Step 4: Commit**

```bash
git add README.md backend/.env.example
git commit -m "docs: README 및 실행/E2E 절차 추가"
```

---

## 부록: 자기 검토 결과

**Spec 커버리지:**
- 데이터 모델 6테이블 → Task 1 ✓
- RRULE 반복 → Task 2, engine 재예약 ✓
- OBS 연동(씬전환/스트림키 주입/송출) → Task 3 ✓
- YouTube 연동(insert/bind/transition) → Task 4 ✓
- 실행 생명주기(go_live/시퀀스/go_complete/에러) → Task 5 ✓
- APScheduler 엔진(등록/취소/복원) → Task 6 ✓
- REST API(broadcasts/scenes/schedules) → Task 7 ✓
- YouTube 이벤트 생성/씬 동기화 → Task 8 ✓
- OAuth 인증/상태/lifespan → Task 9 ✓
- 프론트 UI 5페이지 + 시퀀스 에디터 → Task 10, 11 ✓
- TDD/테스트 전략 → 전 태스크 ✓
- 보안(.gitignore) → 이미 적용 ✓

**알려진 단순화 (수동 E2E에서 검증):**
- `live` 상태 플래그는 Task 9에서 단순화됨 → 실제 OBS is_streaming 연동은 E2E 시 보강 가능
- RTMP URL은 표준 주소 사용 (create_stream의 ingestion_url을 broadcast에 저장하는 개선은 후속)
