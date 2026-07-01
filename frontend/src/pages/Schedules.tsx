import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Schedule, Scene, Broadcast, SequenceItem } from "../types";
import SequenceEditor from "../components/SequenceEditor";

function statusBadge(status: string) {
  const cls = ["pending","running","complete","error"].includes(status)
    ? `badge badge-${status}` : "badge badge-created";
  return <span className={cls}>{status}</span>;
}

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
    reload();
    api.listScenes().then(setScenes);
    api.listBroadcasts().then(setBroadcasts);
  }, []);

  const create = async () => {
    if (broadcastId == null || !startAt || !endAt) return;
    await api.createSchedule({
      broadcast_id: broadcastId,
      start_at: new Date(startAt).toISOString(),
      end_at: new Date(endAt).toISOString(),
      recurrence: rrule ? "custom" : "none",
      recurrence_rule: rrule || null,
      items,
    });
    setItems([]);
    reload();
  };

  return (
    <div>
      <div className="section-header">
        <h2>스케쥴</h2>
      </div>

      <div className="card">
        <h3>새 스케쥴 생성</h3>
        <div className="form-group">
          <label>방송 선택</label>
          <select
            onChange={e => setBroadcastId(Number(e.target.value))}
            value={broadcastId ?? ""}
          >
            <option value="" disabled>방송을 선택하세요</option>
            {broadcasts.map(b => (
              <option key={b.id} value={b.id}>{b.title}</option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <div className="form-group" style={{ flex: 1 }}>
            <label>시작 시간</label>
            <input type="datetime-local" value={startAt} onChange={e => setStartAt(e.target.value)} />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>종료 시간</label>
            <input type="datetime-local" value={endAt} onChange={e => setEndAt(e.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label>반복 (RRULE)</label>
          <input
            type="text"
            value={rrule}
            onChange={e => setRrule(e.target.value)}
            placeholder="RRULE:FREQ=WEEKLY;BYDAY=MO  (빈칸 = 반복 없음)"
          />
        </div>
        <SequenceEditor value={items} onChange={setItems} scenes={scenes} />
        <div style={{ marginTop: 16 }}>
          <button className="btn-primary" onClick={create}>스케쥴 생성</button>
        </div>
      </div>

      <hr className="divider" />

      <ul className="item-list">
        {schedules.map(s => (
          <li key={s.id} className="item-row">
            <span className="item-meta" style={{ minWidth: 24 }}>#{s.id}</span>
            <span className="item-title">
              {new Date(s.start_at).toLocaleString("ko-KR")}
            </span>
            {statusBadge(s.status)}
            <div className="item-actions">
              {(s.status === "pending" || s.status === "error") && (
                <button
                  className="btn-success btn-sm"
                  onClick={() => api.manualGoLive(s.id).then(reload).catch(e => alert(e.message))}
                >
                  지금 시작
                </button>
              )}
              {s.status === "running" && (
                <button
                  className="btn-secondary btn-sm"
                  onClick={() => api.manualGoComplete(s.id).then(reload).catch(e => alert(e.message))}
                >
                  지금 종료
                </button>
              )}
              {s.status !== "running" && (
                <button
                  className="btn-danger btn-sm"
                  onClick={() => api.deleteSchedule(s.id).then(reload)}
                >
                  삭제
                </button>
              )}
            </div>
          </li>
        ))}
        {schedules.length === 0 && (
          <li style={{ color: "var(--text-dim)", padding: "16px 0" }}>스케쥴이 없습니다.</li>
        )}
      </ul>
    </div>
  );
}
