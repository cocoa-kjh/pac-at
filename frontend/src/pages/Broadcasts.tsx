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
        <li key={b.id}><span>{b.title}</span> — {b.status}
          {!b.youtube_broadcast_id &&
            <button onClick={() => api.createYoutubeEvent(b.id).then(reload)}>YouTube 이벤트 생성</button>}
        </li>))}</ul>
    </div>
  );
}
