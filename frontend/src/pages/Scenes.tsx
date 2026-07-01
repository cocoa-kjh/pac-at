import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Scene } from "../types";

export default function Scenes() {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const reload = () => api.listScenes().then(setScenes);
  useEffect(() => { reload(); }, []);

  return (
    <div>
      <div className="section-header">
        <h2>씬 매핑</h2>
        <button className="btn-secondary" onClick={() => api.syncScenes().then(reload)}>
          OBS 씬 동기화
        </button>
      </div>
      <ul className="item-list">
        {scenes.map(s => (
          <li key={s.id} className="item-row" style={!s.active ? { opacity: 0.5 } : undefined}>
            <span className="item-title">{s.name}</span>
            <span className="item-meta">{s.obs_scene_name}</span>
            {!s.active && <span className="badge badge-error">OBS에서 제거됨</span>}
          </li>
        ))}
        {scenes.length === 0 && (
          <li style={{ color: "var(--text-dim)", padding: "16px 0" }}>
            씬이 없습니다. OBS 동기화를 실행하세요.
          </li>
        )}
      </ul>
    </div>
  );
}
