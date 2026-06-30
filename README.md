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
