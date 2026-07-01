import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Broadcast } from "../types";

function statusBadge(status: string) {
  const cls = ["created","pending","running","complete","error"].includes(status)
    ? `badge badge-${status}` : "badge badge-created";
  return <span className={cls}>{status}</span>;
}

const PRIVACY_OPTIONS = ["private", "unlisted", "public"];

export default function Broadcasts() {
  const [items, setItems] = useState<Broadcast[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [privacy, setPrivacy] = useState("private");

  // 편집 상태
  const [editId, setEditId] = useState<number | null>(null);
  const [eTitle, setETitle] = useState("");
  const [eDescription, setEDescription] = useState("");
  const [ePrivacy, setEPrivacy] = useState("private");

  const reload = () => api.listBroadcasts().then(setItems);
  useEffect(() => { reload(); }, []);

  const create = async () => {
    if (!title.trim()) return;
    await api.createBroadcast({ title, description, privacy });
    setTitle(""); setDescription(""); setPrivacy("private");
    reload();
  };

  const startEdit = (b: Broadcast) => {
    setEditId(b.id);
    setETitle(b.title);
    setEDescription(b.description ?? "");
    setEPrivacy(b.privacy);
  };

  const cancelEdit = () => setEditId(null);

  const saveEdit = async (id: number) => {
    try {
      await api.updateBroadcast(id, { title: eTitle, description: eDescription, privacy: ePrivacy });
      setEditId(null);
      reload();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div>
      <div className="section-header">
        <h2>방송 관리</h2>
      </div>

      <div className="card">
        <h3>새 방송 생성</h3>
        <div className="form-group">
          <label>제목</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="방송 제목"
          />
        </div>
        <div className="form-group">
          <label>설명</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="방송 설명"
            rows={3}
          />
        </div>
        <div className="form-group">
          <label>공개 범위</label>
          <select value={privacy} onChange={e => setPrivacy(e.target.value)}>
            {PRIVACY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="btn-primary" onClick={create}>방송 생성</button>
        </div>
      </div>

      <hr className="divider" />

      <ul className="item-list">
        {items.map(b => (
          <li key={b.id} className="item-row" style={{ flexDirection: "column", alignItems: "stretch" }}>
            {editId === b.id ? (
              <div className="form-group" style={{ width: "100%" }}>
                <label>제목</label>
                <input type="text" value={eTitle} onChange={e => setETitle(e.target.value)} />
                <label style={{ marginTop: 8 }}>설명</label>
                <textarea value={eDescription} onChange={e => setEDescription(e.target.value)} rows={3} />
                <label style={{ marginTop: 8 }}>공개 범위</label>
                <select value={ePrivacy} onChange={e => setEPrivacy(e.target.value)}>
                  {PRIVACY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                  <button className="btn-primary btn-sm" onClick={() => saveEdit(b.id)}>저장</button>
                  <button className="btn-secondary btn-sm" onClick={cancelEdit}>취소</button>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 8, width: "100%" }}>
                <span className="item-title">{b.title}</span>
                {statusBadge(b.status)}
                <span className="item-meta">{b.privacy}</span>
                {b.youtube_broadcast_id
                  ? <span className="item-meta">YT: {b.youtube_broadcast_id}</span>
                  : <button className="btn-secondary btn-sm"
                      onClick={() => api.createYoutubeEvent(b.id).then(reload)}>
                      YouTube 이벤트 생성
                    </button>}
                <div className="item-actions">
                  {b.status !== "live" && b.status !== "completed" && (
                    <button className="btn-secondary btn-sm" onClick={() => startEdit(b)}>수정</button>
                  )}
                </div>
              </div>
            )}
          </li>
        ))}
        {items.length === 0 && (
          <li style={{ color: "var(--text-dim)", padding: "16px 0" }}>방송이 없습니다.</li>
        )}
      </ul>
    </div>
  );
}
