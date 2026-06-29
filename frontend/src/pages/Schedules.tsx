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
        <li key={s.id}>
          #{s.id} {s.start_at} — <strong>{s.status}</strong>
          {(s.status === "pending" || s.status === "error") && (
            <button onClick={() => api.manualGoLive(s.id).then(reload).catch(e => alert(e.message))}>
              지금 시작
            </button>
          )}
          {s.status === "running" && (
            <button onClick={() => api.manualGoComplete(s.id).then(reload).catch(e => alert(e.message))}>
              지금 종료
            </button>
          )}
          {s.status !== "running" && (
            <button onClick={() => api.deleteSchedule(s.id).then(reload)}>취소</button>
          )}
        </li>))}</ul>
    </div>);
}
