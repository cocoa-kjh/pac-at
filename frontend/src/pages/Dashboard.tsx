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
