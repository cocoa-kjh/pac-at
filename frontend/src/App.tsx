import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Broadcasts from "./pages/Broadcasts";
import Scenes from "./pages/Scenes";
import Schedules from "./pages/Schedules";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <aside className="sidebar">
          <div className="sidebar-logo">
            ● LiveSched
            <span>YouTube 스트리밍 스케쥴러</span>
          </div>
          <nav className="sidebar-nav">
            <NavLink to="/" end>🏠 대시보드</NavLink>
            <NavLink to="/broadcasts">📡 방송</NavLink>
            <NavLink to="/schedules">📅 스케쥴</NavLink>
            <NavLink to="/scenes">🎬 씬</NavLink>
            <NavLink to="/settings">⚙️ 설정</NavLink>
          </nav>
        </aside>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/broadcasts" element={<Broadcasts />} />
            <Route path="/schedules" element={<Schedules />} />
            <Route path="/scenes" element={<Scenes />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
