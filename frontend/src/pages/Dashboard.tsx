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

  if (!s) return <div className="loading">로딩 중...</div>;

  return (
    <div>
      <h2>대시보드</h2>
      <div className="card-grid">
        <div className="stat-card">
          <div className="label">OBS 연결</div>
          <div className="value">
            <span className={`dot ${s.obs_connected ? "dot-green" : "dot-gray"}`} />
            {s.obs_connected ? "연결됨" : "끊김"}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">YouTube 인증</div>
          <div className="value">
            <span className={`dot ${s.youtube_authed ? "dot-green" : "dot-gray"}`} />
            {s.youtube_authed ? "인증됨" : "미인증"}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">현재 LIVE</div>
          <div className="value">
            <span className={`dot ${s.live ? "dot-red" : "dot-gray"}`} />
            {s.live ? "방송 중" : "대기"}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">다음 방송</div>
          <div className="value" style={{ fontSize: 14 }}>
            {s.next_schedule
              ? new Date(s.next_schedule.start_at).toLocaleString("ko-KR")
              : "예정 없음"}
          </div>
        </div>
      </div>
    </div>
  );
}
