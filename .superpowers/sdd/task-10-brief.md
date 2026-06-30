### Task 10: 프론트엔드 스캐폴딩 & API 클라이언트

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/tests/client.test.ts`

**Interfaces:**
- Produces (`src/types.ts`): `Broadcast`, `Scene`, `Schedule`, `SequenceItem`, `Status` 타입 (백엔드 스키마 대응)
- Produces (`src/api/client.ts`): `api.listBroadcasts()`, `api.createBroadcast(data)`, `api.createYoutubeEvent(id)`, `api.listScenes()`, `api.syncScenes()`, `api.listSchedules()`, `api.createSchedule(data)`, `api.deleteSchedule(id)`, `api.getStatus()` — 모두 `fetch` 기반, baseURL `http://localhost:8000`

- [ ] **Step 1: package.json / vite / tsconfig / index.html 작성**

`frontend/package.json`:
```json
{
  "name": "yt-scheduler-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.0.0"
  }
}
```

`frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], server: { port: 5173 } });
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020", "module": "ESNext", "moduleResolution": "bundler",
    "jsx": "react-jsx", "strict": true, "esModuleInterop": true,
    "skipLibCheck": true, "lib": ["ES2020", "DOM", "DOM.Iterable"]
  },
  "include": ["src", "tests"]
}
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="ko">
  <head><meta charset="UTF-8" /><title>YT 라이브 스케쥴러</title></head>
  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
```

- [ ] **Step 2: types.ts 작성**

```typescript
export interface Broadcast {
  id: number; title: string; description: string; privacy: string;
  youtube_broadcast_id: string | null; status: string;
}
export interface Scene { id: number; name: string; obs_scene_name: string; note: string; }
export interface SequenceItem { scene_id: number; order_index: number; duration_seconds: number | null; }
export interface Schedule {
  id: number; broadcast_id: number; start_at: string; end_at: string;
  recurrence: string; status: string;
}
export interface Status {
  obs_connected: boolean; youtube_authed: boolean;
  next_schedule: { id: number; start_at: string } | null; live: boolean;
}
```

- [ ] **Step 3: 실패 테스트 작성 (client.test.ts)**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../src/api/client";

beforeEach(() => {
  global.fetch = vi.fn(async () =>
    ({ ok: true, json: async () => [{ id: 1, title: "t" }] }) as Response);
});

describe("api client", () => {
  it("listBroadcasts hits /broadcasts", async () => {
    const data = await api.listBroadcasts();
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/broadcasts", expect.any(Object));
    expect(data[0].id).toBe(1);
  });
  it("createSchedule POSTs JSON", async () => {
    await api.createSchedule({ broadcast_id: 1, start_at: "x", end_at: "y",
      recurrence: "none", recurrence_rule: null, items: [] } as any);
    const call = (global.fetch as any).mock.calls.at(-1);
    expect(call[1].method).toBe("POST");
  });
});
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd frontend && npm install && npx vitest run`
Expected: FAIL — `src/api/client` 없음

- [ ] **Step 5: client.ts 구현**

```typescript
import type { Broadcast, Scene, Schedule, Status } from "../types";
const BASE = "http://localhost:8000";

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

export const api = {
  listBroadcasts: () => req<Broadcast[]>("/broadcasts"),
  createBroadcast: (data: Partial<Broadcast>) =>
    req<Broadcast>("/broadcasts", { method: "POST", body: JSON.stringify(data) }),
  createYoutubeEvent: (id: number) =>
    req<Broadcast>(`/broadcasts/${id}/youtube`, { method: "POST" }),
  listScenes: () => req<Scene[]>("/scenes"),
  syncScenes: () => req<{ ok: boolean }>("/scenes/sync", { method: "POST" }),
  listSchedules: () => req<Schedule[]>("/schedules"),
  createSchedule: (data: any) =>
    req<Schedule>("/schedules", { method: "POST", body: JSON.stringify(data) }),
  deleteSchedule: (id: number) =>
    req<{ ok: boolean }>(`/schedules/${id}`, { method: "DELETE" }),
  getStatus: () => req<Status>("/status"),
};
```

- [ ] **Step 6: main.tsx / App.tsx 최소 구현**

`frontend/src/main.tsx`:
```typescript
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
createRoot(document.getElementById("root")!).render(<App />);
```

`frontend/src/App.tsx`:
```typescript
export default function App() {
  return <div><h1>YT 라이브 스케쥴러</h1></div>;
}
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd frontend && npx vitest run`
Expected: PASS (2 passed)

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src/ frontend/tests/
git commit -m "feat: 프론트엔드 스캐폴딩 및 API 클라이언트 추가"
```

---

