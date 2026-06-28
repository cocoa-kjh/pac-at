import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Broadcasts from "./pages/Broadcasts";
import Scenes from "./pages/Scenes";
import Schedules from "./pages/Schedules";
import Settings from "./pages/Settings";
export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ display: "flex", gap: 12 }}>
        <Link to="/">대시보드</Link><Link to="/broadcasts">방송</Link>
        <Link to="/schedules">스케쥴</Link><Link to="/scenes">씬</Link>
        <Link to="/settings">설정</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/broadcasts" element={<Broadcasts />} />
        <Route path="/schedules" element={<Schedules />} />
        <Route path="/scenes" element={<Scenes />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>);
}
