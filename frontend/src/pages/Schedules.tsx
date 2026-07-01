import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Schedule, Scene, Broadcast, SequenceItem, SchedulePreflight } from "../types";
import SequenceEditor from "../components/SequenceEditor";

function statusBadge(status: string) {
  const cls = ["pending","running","complete","error"].includes(status)
    ? `badge badge-${status}` : "badge badge-created";
  return <span className={cls}>{status}</span>;
}

// ISO(UTC) → datetime-local 입력값(로컬 시간, 초 제외)
function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
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
  const [preflights, setPreflights] = useState<Record<number, SchedulePreflight>>({});
  const [editId, setEditId] = useState<number | null>(null);   // null = 생성 모드

  const reload = () => api.listSchedules().then(setSchedules);

  const resetForm = () => {
    setEditId(null); setBroadcastId(null);
    setStartAt(""); setEndAt(""); setRrule(""); setItems([]);
  };

  const startEdit = (s: Schedule) => {
    setEditId(s.id);
    setBroadcastId(s.broadcast_id);
    setStartAt(toLocalInput(s.start_at));
    setEndAt(toLocalInput(s.end_at));
    setRrule(s.recurrence_rule ?? "");
    setItems(s.items.map(it => ({ ...it })));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const checkPreflight = (id: number) =>
    api.preflightSchedule(id).then(p => setPreflights(prev => ({ ...prev, [id]: p })));

  const goLive = (id: number) => {
    const p = preflights[id];
    if (p && !p.ok && !confirm(`사전 점검 문제가 있습니다:\n- ${p.problems.join("\n- ")}\n\n그래도 시작할까요?`)) {
      return;
    }
    api.manualGoLive(id).then(reload).catch(e => alert(e.message));
  };
  useEffect(() => {
    reload();
    api.listScenes().then(setScenes);
    api.listBroadcasts().then(setBroadcasts);
  }, []);

  const submit = async () => {
    if (broadcastId == null || !startAt || !endAt) return;
    const payload = {
      broadcast_id: broadcastId,
      start_at: new Date(startAt).toISOString(),
      end_at: new Date(endAt).toISOString(),
      recurrence: rrule ? "custom" : "none",
      recurrence_rule: rrule || null,
      items,
    };
    try {
      if (editId == null) {
        await api.createSchedule(payload);
      } else {
        await api.updateSchedule(editId, payload);
      }
      resetForm();
      reload();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div>
      <div className="section-header">
        <h2>스케쥴</h2>
      </div>

      <div className="card">
        <h3>{editId == null ? "새 스케쥴 생성" : `스케쥴 #${editId} 수정`}</h3>
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
        <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
          <button className="btn-primary" onClick={submit}>
            {editId == null ? "스케쥴 생성" : "변경 저장"}
          </button>
          {editId != null && (
            <button className="btn-secondary" onClick={resetForm}>취소</button>
          )}
        </div>
      </div>

      <hr className="divider" />

      <ul className="item-list">
        {schedules.map(s => {
          const pf = preflights[s.id];
          return (
            <li key={s.id} className="item-row" style={{ flexDirection: "column", alignItems: "stretch" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="item-meta" style={{ minWidth: 24 }}>#{s.id}</span>
                <span className="item-title">
                  {new Date(s.start_at).toLocaleString("ko-KR")}
                </span>
                {statusBadge(s.status)}
                <div className="item-actions">
                  {(s.status === "pending" || s.status === "error") && (
                    <>
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => checkPreflight(s.id)}
                      >
                        사전 점검
                      </button>
                      <button
                        className="btn-success btn-sm"
                        onClick={() => goLive(s.id)}
                      >
                        지금 시작
                      </button>
                    </>
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
                      className="btn-secondary btn-sm"
                      onClick={() => startEdit(s)}
                    >
                      수정
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
              </div>
              {pf && (
                <div
                  style={{
                    marginTop: 8,
                    padding: 8,
                    fontSize: 12,
                    borderRadius: 4,
                    background: pf.ok ? "var(--badge-pending-bg, #163a2a)" : "var(--badge-error-bg, #3a1616)",
                    color: pf.ok ? "#7fd99a" : "#f08080",
                  }}
                >
                  <div>
                    OBS {pf.obs_connected ? "연결됨" : "연결 안 됨"} · YouTube{" "}
                    {pf.youtube_authed ? "인증됨" : "인증 안 됨"} · 방송 준비{" "}
                    {pf.broadcast_ready ? "완료" : "미완료"}
                  </div>
                  <div>
                    {pf.items.map(it => (
                      <span key={it.order_index} style={{ marginRight: 8 }}>
                        [{it.role === "first" ? "첫씬" : `#${it.order_index}`}]{" "}
                        {it.scene_name ?? "(미지정)"} {it.exists ? "✓" : "✕"}
                      </span>
                    ))}
                  </div>
                  {pf.problems.length > 0 && (
                    <ul style={{ margin: "4px 0 0", paddingLeft: 16 }}>
                      {pf.problems.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </li>
          );
        })}
        {schedules.length === 0 && (
          <li style={{ color: "var(--text-dim)", padding: "16px 0" }}>스케쥴이 없습니다.</li>
        )}
      </ul>
    </div>
  );
}
