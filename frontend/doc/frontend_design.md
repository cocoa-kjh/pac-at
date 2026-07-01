# Frontend Design Document

## 1. 개요 (Overview)
이 문서는 YouTube 라이브스트리밍 스케쥴러의 프론트엔드(`frontend`) 디렉토리 구조, 사용된 기술 스택, 프로그램 설계 및 파일 확장자들에 대한 설명을 포함합니다.

## 2. 파일 확장자 설명 (.js, .ts, .tsx)
현재 프로젝트 `src` 폴더 내에 `App.js`와 `App.tsx`, `client.js`와 `client.ts` 처럼 동일한 이름의 파일들이 여러 개 존재하는 이유는 **타입스크립트(TypeScript) 컴파일 설정의 부작용(Side-effect)** 때문입니다.

* **.ts (TypeScript)**: JavaScript에 정적 타입을 추가한 언어입니다. API 클라이언트 로직, 타입 정의 등 UI가 포함되지 않은 순수 로직 파일에 주로 사용됩니다.
* **.tsx (TypeScript JSX)**: TypeScript 환경에서 React 컴포넌트(HTML 형태의 JSX 코드)를 작성할 때 사용하는 확장자입니다. 화면에 그려지는 UI 파일들입니다.
* **.js (JavaScript)**: 브라우저가 실제로 읽고 실행할 수 있는 기본 언어입니다.

**왜 중복해서 존재하는가?**
Vite 기반의 프로젝트에서는 Vite 도구가 코드 변환을 담당합니다. 하지만 개발 중 타입스크립트 컴파일러(`tsc`) 명령어가 실행될 때, 설정 파일(`tsconfig.json`)에 빌드된 결과물을 다른 곳(예: `dist` 폴더)에 저장하거나 파일을 생성하지 말라는 옵션(`"noEmit": true`)이 빠져 있어서 발생한 현상입니다. 작성된 `.ts`, `.tsx` 파일들이 그 자리에서 곧바로 `.js` 파일로 변환되어 원본 파일 옆에 생성된 것입니다.
실제 프로젝트 개발 시에는 **`.ts`와 `.tsx` 파일만 수정하고 개발**하면 되며, 실수로 생성된 `.js` 파일들은 삭제해도 무방합니다. (추후 `tsconfig.json`에 `"noEmit": true` 추가 권장)

## 3. 기술 스택 (Tech Stack)
* **UI 라이브러리**: React 18
* **라우팅**: React Router DOM (싱글 페이지 어플리케이션 라우팅)
* **개발 언어**: TypeScript, CSS
* **빌드 툴 및 번들러**: Vite 5
* **테스트 프레임워크**: Vitest, React Testing Library

## 4. 디렉토리 구조 (Directory Structure)
```text
frontend/
├── package.json       # 프로젝트 의존성(라이브러리) 및 npm 스크립트 정의
├── tsconfig.json      # 타입스크립트 컴파일러 설정
├── vite.config.ts     # Vite 빌드 도구 설정 파일
├── index.html         # React 앱이 마운트되는 메인 HTML 파일
└── src/
    ├── main.tsx       # React 앱의 진입점 (최상위 App 컴포넌트를 DOM에 렌더링)
    ├── App.tsx        # 최상위 컴포넌트 및 React Router 라우팅 설정 (사이드바 및 메인 화면)
    ├── index.css      # 전역 스타일시트
    ├── types.ts       # TypeScript 인터페이스 (Broadcast, Scene, Schedule 등 데이터 구조 정의)
    ├── api/
    │   └── client.ts  # 백엔드(FastAPI) 서버와 통신하는 Fetch API 래퍼
    ├── components/    # 재사용 가능한 UI 공통 컴포넌트가 모이는 폴더
    └── pages/         # 라우터에 의해 연결되는 각 페이지 컴포넌트
        ├── Dashboard.tsx  # 대시보드 메인 화면
        ├── Broadcasts.tsx # 유튜브 방송 관리 화면
        ├── Schedules.tsx  # 스트리밍 스케쥴 관리 화면
        ├── Scenes.tsx     # OBS 씬 동기화 및 씬 목록 화면
        └── Settings.tsx   # 앱 환경 설정 화면
```

## 5. 아키텍처 및 프로그램 설계 (Architecture & Design)

### 5.1 컴포넌트 및 화면 구조
* 애플리케이션 화면은 크게 좌측의 **사이드바(Sidebar)**와 우측의 **메인 컨텐츠(Main Content)** 영역으로 분리되어 있습니다 (`App.tsx`에서 정의).
* 사용자가 사이드바의 네비게이션 메뉴를 클릭하면 `react-router-dom`을 통해 브라우저의 새로고침 없이 메인 컨텐츠 영역의 컴포넌트만 교체되는 **SPA(Single Page Application)** 방식으로 동작합니다. 이를 통해 빠르고 부드러운 사용자 경험을 제공합니다.

### 5.2 데이터 통신 계층 (API Layer)
* 모든 백엔드 로컬 서버(`http://localhost:8000`)와의 통신은 `src/api/client.ts` 파일 한 곳으로 집중시켰습니다.
* 브라우저 내장 `fetch` API를 사용하여 REST API 요청을 보내고, 백엔드의 응답을 JSON 객체로 파싱합니다.
* 통신을 통해 주고받는 데이터는 `types.ts`에 정의된 인터페이스를 적극 활용하여 타입 안정성을 보장합니다. 이는 런타임 오류를 방지하고 자동완성 등 개발자의 생산성을 크게 향상시킵니다.
