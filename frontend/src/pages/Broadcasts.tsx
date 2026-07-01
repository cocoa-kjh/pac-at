import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Broadcast } from "../types";

function statusBadge(status: string) {
  const cls = ["created","pending","running","complete","error"].includes(status)
    ? `badge badge-${status}` : "badge badge-created";
  return <span className={cls}>{status}</span>;
}

export default function Broadcasts() {
  const [items, setItems] = useState<Broadcast[]>([]);
  const [title, setTitle] = useState("");
  const reload = () => api.listBroadcasts().then(setItems);
  useEffect(() => { reload(); }, []);

  const create = async () => {
    if (!title.trim()) return;
    await api.createBroadcast({ title });
    setTitle("");
    reload();
  };

  return (
    <div>
      <div className="section-header">
        <h2>방송 관리</h2>
      </div>
      <div className="card">
        <h3>새 방송 생성</h3>
        <div className="form-row">
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="방송 제목"
            style={{ flex: 1 }}
            onKeyDown={e => e.key === "Enter" && create()}
          />
          <button className="btn-primary" onClick={create}>방송 생성</button>
        </div>
      </div>
      <ul className="item-list">
        {items.map(b => (
          <li key={b.id} className="item-row">
            <span className="item-title">{b.title}</span>
            {statusBadge(b.status)}
            {b.youtube_broadcast_id
              ? <span className="item-meta">YT: {b.youtube_broadcast_id}</span>
              : <button className="btn-secondary btn-sm"
                  onClick={() => api.createYoutubeEvent(b.id).then(reload)}>
                  YouTube 이벤트 생성
                </button>}
          </li>
        ))}
        {items.length === 0 && (
          <li style={{ color: "var(--text-dim)", padding: "16px 0" }}>방송이 없습니다.</li>
        )}
      </ul>
    </div>
  );
}
