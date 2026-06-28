### Task 11: 페이지 구성 (Dashboard / Broadcasts / Scenes / Schedules / Settings)

**Files:**
- Modify: `frontend/src/App.tsx` (라우터)
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/Broadcasts.tsx`
- Create: `frontend/src/pages/Scenes.tsx`
- Create: `frontend/src/pages/Schedules.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/components/SequenceEditor.tsx`
- Create: `frontend/tests/Broadcasts.test.tsx`

**Interfaces:**
- Consumes: `api`, types
- Produces: 라우팅된 5개 페이지. `SequenceEditor`는 `value: SequenceItem[]`, `onChange(items)`, `scenes: Scene[]` props를 받아 씬 추가/순서/지속시간 편집.

- [ ] **Step 1: 실패 테스트 작성 (Broadcasts 페이지)**

`frontend/tests/Broadcasts.test.tsx`:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Broadcasts from "../src/pages/Broadcasts";
import { api } from "../src/api/client";

vi.mock("../src/api/client");

beforeEach(() => {
  (api.listBroadcasts as any) = vi.fn(async () => [
    { id: 1, title: "내 방송", description: "", privacy: "private",
      youtube_broadcast_id: null, status: "draft" }]);
});

describe("Broadcasts page", () => {
  it("renders broadcast titles", async () => {
    render(<Broadcasts />);
    await waitFor(() => expect(screen.getByText("내 방송")).toBeDefined());
  });
});
```

추가 devDependency 필요: `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`.
`frontend/package.json`의 devDependencies에 추가하고 `frontend/vite.config.ts`에 `test: { environment: "jsdom" }` 추가.

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm install && npx vitest run tests/Broadcasts.test.tsx`
Expected: FAIL — `src/pages/Broadcasts` 없음

- [ ] **Step 3: Broadcasts.tsx 구현**

```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Broadcast } from "../types";

export default function Broadcasts() {
  const [items, setItems] = useState<Broadcast[]>([]);
  const [title, setTitle] = useState("");
  const reload = () => api.listBroadcasts().then(setItems);
  useEffect(() => { reload(); }, []);
  const create = async () => { await api.createBroadcast({ title }); setTitle(""); reload(); };
  return (
    <div>
      <h2>방송 관리</h2>
      <input value={title} onChange={e => setTitle(e.target.value)} placeholder="제목" />
      <button onClick={create}>방송 생성</button>
      <ul>{items.map(b => (
        <li key={b.id}>{b.title} — {b.status}
          {!b.youtube_broadcast_id &&
            <button onClick={() => api.createYoutubeEvent(b.id).then(reload)}>YouTube 이벤트 생성</button>}
        </li>))}</ul>
    </div>
  );
}
```

- [ ] **Step 4: 나머지 페이지 + SequenceEditor + App 라우터 구현**

`frontend/src/pages/Scenes.tsx`:
```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Scene } from "../types";
export default function Scenes() {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const reload = () => api.listScenes().then(setScenes);
  useEffect(() => { reload(); }, []);
  return (
    <div><h2>씬 매핑</h2>
      <button onClick={() => api.syncScenes().then(reload)}>OBS 씬 동기화</button>
      <ul>{scenes.map(s => <li key={s.id}>{s.name} ({s.obs_scene_name})</li>)}</ul>
    </div>);
}
```

`frontend/src/components/SequenceEditor.tsx`:
```typescript
import type { Scene, SequenceItem } from "../types";
export default function SequenceEditor(
  { value, onChange, scenes }:
  { value: SequenceItem[]; onChange: (v: SequenceItem[]) => void; scenes: Scene[] }) {
  const add = (scene_id: number) =>
    onChange([...value, { scene_id, order_index: value.length, duration_seconds: 60 }]);
  const setDur = (i: number, d: number) =>
    onChange(value.map((it, idx) => idx === i ? { ...it, duration_seconds: d } : it));
  return (
    <div><h4>시퀀스 편성</h4>
      <select onChange={e => add(Number(e.target.value))} value="">
        <option value="" disabled>씬 추가...</option>
        {scenes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <ol>{value.map((it, i) => {
        const sc = scenes.find(s => s.id === it.scene_id);
        return <li key={i}>{sc?.name}
          <input type="number" value={it.duration_seconds ?? 0}
                 onChange={e => setDur(i, Number(e.target.value))} /> 초</li>;
      })}</ol>
    </div>);
}
```

`frontend/src/pages/Schedules.tsx`:
```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Schedule, Scene, Broadcast, SequenceItem } from "../types";
import SequenceEditor from "../components/SequenceEditor";

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [broadcastId, setBroadcastId] = useState<number | null>(null);
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [rrule, setRrule] = useState("");
  const [items, setItems] = useState<SequenceItem[]>([]);
  const reload = () => api.listSchedules().then(setSchedules);
  useEffect(() => {
    reload(); api.listScenes().then(setScenes); api.listBroadcasts().then(setBroadcasts);
  }, []);
  const create = async () => {
    if (broadcastId == null) return;
    await api.createSchedule({
      broadcast_id: broadcastId,
      start_at: new Date(startAt).toISOString(),
      end_at: new Date(endAt).toISOString(),
      recurrence: rrule ? "custom" : "none",
      recurrence_rule: rrule || null, items });
    setItems([]); reload();
  };
  return (
    <div><h2>스케쥴</h2>
      <select onChange={e => setBroadcastId(Number(e.target.value))} value={broadcastId ?? ""}>
        <option value="" disabled>방송 선택</option>
        {broadcasts.map(b => <option key={b.id} value={b.id}>{b.title}</option>)}
      </select>
      <label>시작 <input type="datetime-local" value={startAt} onChange={e => setStartAt(e.target.value)} /></label>
      <label>종료 <input type="datetime-local" value={endAt} onChange={e => setEndAt(e.target.value)} /></label>
      <label>RRULE <input value={rrule} onChange={e => setRrule(e.target.value)} placeholder="RRULE:FREQ=WEEKLY;BYDAY=MO" /></label>
      <SequenceEditor value={items} onChange={setItems} scenes={scenes} />
      <button onClick={create}>스케쥴 생성</button>
      <ul>{schedules.map(s => (
        <li key={s.id}>#{s.id} {s.start_at} — {s.status}
          <button onClick={() => api.deleteSchedule(s.id).then(reload)}>취소</button>
        </li>))}</ul>
    </div>);
}
```

`frontend/src/pages/Dashboard.tsx`:
```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Status } from "../types";
export default function Dashboard() {
  const [s, setS] = useState<Status | null>(null);
  useEffect(() => {
    const t = setInterval(() => api.getStatus().then(setS), 3000);
    api.getStatus().then(setS);
    return () => clearInterval(t);
  }, []);
  if (!s) return <div>로딩...</div>;
  return (
    <div><h2>대시보드</h2>
      <p>OBS: {s.obs_connected ? "●연결" : "○끊김"}</p>
      <p>YouTube: {s.youtube_authed ? "●인증" : "○미인증"}</p>
      <p>다음 방송: {s.next_schedule ? s.next_schedule.start_at : "없음"}</p>
      <p>현재 LIVE: {s.live ? "예" : "아니오"}</p>
    </div>);
}
```

`frontend/src/pages/Settings.tsx`:
```typescript
export default function Settings() {
  return (
    <div><h2>설정</h2>
      <a href="http://localhost:8000/auth/youtube">YouTube 연결/재인증</a>
    </div>);
}
```

`frontend/src/App.tsx`:
```typescript
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Broadcasts from "./pages/Broadcasts";
import Scenes from "./pages/Scenes";
import Schedules from "./pages/Schedules";
import Settings from "./pages/Settings";
export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ display: "flex", gap: 12 }}>
        <Link to="/">대시보드</Link><Link to="/broadcasts">방송</Link>
        <Link to="/schedules">스케쥴</Link><Link to="/scenes">씬</Link>
        <Link to="/settings">설정</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/broadcasts" element={<Broadcasts />} />
        <Route path="/schedules" element={<Schedules />} />
        <Route path="/scenes" element={<Scenes />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>);
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend && npx vitest run`
Expected: PASS (모든 테스트 통과)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ frontend/tests/ frontend/package.json frontend/vite.config.ts
git commit -m "feat: 프론트엔드 5개 페이지 및 시퀀스 에디터 추가"
```

---

## Phase 7 — 통합 & 문서

