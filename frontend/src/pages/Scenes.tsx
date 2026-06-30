import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Scene } from "../types";
export default function Scenes() {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const reload = () => api.listScenes().then(setScenes);
  useEffect(() => { reload(); }, []);
  return (
    <div><h2>씬 매핑</h2>
      <button onClick={() => api.syncScenes().then(reload)}>OBS 씬 동기화</button>
      <ul>{scenes.map(s => <li key={s.id}>{s.name} ({s.obs_scene_name})</li>)}</ul>
    </div>);
}
