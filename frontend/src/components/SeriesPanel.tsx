import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Scene, SequenceItem, Series, Schedule } from "../types";
import SequenceEditor from "./SequenceEditor";

const WEEKDAYS: { code: string; label: string }[] = [
  { code: "MO", label: "월" }, { code: "TU", label: "화" }, { code: "WE", label: "수" },
  { code: "TH", label: "목" }, { code: "FR", label: "금" }, { code: "SA", label: "토" },
  { code: "SU", label: "일" },
];

export default function SeriesPanel(
  { scenes, onOccurrenceCreated }:
  { scenes: Scene[]; onOccurrenceCreated: () => void }
) {
  const [series, setSeries] = useState<Series[]>([]);
  const [freq, setFreq] = useState<"WEEKLY" | "DAILY">("WEEKLY");
  const [days, setDays] = useState<Set<string>>(new Set(["MO"]));
  const [firstStart, setFirstStart] = useState("");
  const [firstEnd, setFirstEnd] = useState("");
  const [leadTime, setLeadTime] = useState(3);
  const [titleTemplate, setTitleTemplate] = useState("{date} 정기방송");
  const [description, setDescription] = useState("");
  const [privacy, setPrivacy] = useState("private");
  const [items, setItems] = useState<SequenceItem[]>([]);
  const [occurrences, setOccurrences] = useState<Record<number, Schedule[]>>({});

  const reload = () => api.listSeries().then(setSeries);
  useEffect(() => { reload(); }, []);

  const toggleDay = (code: string) => {
    setDays(prev => {
      const next = new Set(prev);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
  };

  const create = async () => {
    if (!firstStart || !firstEnd) {
      alert("첫 회차 시작/종료 시각을 입력하세요"); return;
    }
    if (freq === "WEEKLY" && days.size === 0) {
      alert("반복할 요일을 하나 이상 선택하세요"); return;
    }
    if (!titleTemplate.trim()) {
      alert("제목 템플릿을 입력하세요"); return;
    }
    if (leadTime < 1) {
      alert("사전 생성 기간은 1일 이상이어야 함"); return;
    }
    const start = new Date(firstStart);
    const end = new Date(firstEnd);
    if (end <= start) {
      alert("종료 시각은 시작 시각보다 늦어야 함"); return;
    }
    const rule = freq === "WEEKLY" ? `FREQ=WEEKLY;BYDAY=${[...days].join(",")}` : "FREQ=DAILY";
    try {
      await api.createSeries({
        first_start_at: start.toISOString(),
        duration_seconds: Math.round((end.getTime() - start.getTime()) / 1000),
        recurrence_rule: rule,
        title_template: titleTemplate,
        description_template: description,
        privacy,
        lead_time_days: leadTime,
        items,
      });
      setFirstStart(""); setFirstEnd(""); setItems([]);
      reload();
      onOccurrenceCreated();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const toggleOccurrences = (id: number) => {
    if (occurrences[id]) {
      setOccurrences(prev => { const n = { ...prev }; delete n[id]; return n; });
    } else {
      api.listSeriesOccurrences(id).then(list =>
        setOccurrences(prev => ({ ...prev, [id]: list })));
    }
  };

  const stopSeries = async (id: number) => {
    if (!confirm("이 시리즈의 향후 회차 생성을 중단할까요? (이미 생성된 회차는 유지됩니다)")) return;
    await api.deleteSeries(id);
    reload();
  };

  const generateNow = async (id: number) => {
    try {
      const created = await api.generateSeriesNow(id);
      alert(created.length > 0 ? `${created.length}개 회차 생성됨` : "생성할 회차 없음 (사전 생성 기간 밖이거나 이미 최신 상태)");
      reload();
      if (occurrences[id]) {
        api.listSeriesOccurrences(id).then(list =>
          setOccurrences(prev => ({ ...prev, [id]: list })));
      }
      onOccurrenceCreated();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div>
      <div className="card">
        <h3>반복 시리즈 생성</h3>
        <div className="form-group">
          <label>반복 주기</label>
          <div className="form-row">
            <select value={freq} onChange={e => setFreq(e.target.value as "WEEKLY" | "DAILY")}>
              <option value="WEEKLY">매주</option>
              <option value="DAILY">매일</option>
            </select>
            {freq === "WEEKLY" && (
              <div style={{ display: "flex", gap: 4 }}>
                {WEEKDAYS.map(w => (
                  <button
                    key={w.code}
                    type="button"
                    className={days.has(w.code) ? "btn-primary btn-sm" : "btn-secondary btn-sm"}
                    onClick={() => toggleDay(w.code)}
                  >
                    {w.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="form-row">
          <div className="form-group" style={{ flex: 1 }}>
            <label>첫 회차 시작</label>
            <input type="datetime-local" value={firstStart} onChange={e => setFirstStart(e.target.value)} />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>첫 회차 종료</label>
            <input type="datetime-local" value={firstEnd} onChange={e => setFirstEnd(e.target.value)} />
          </div>
          <div className="form-group">
            <label>사전 생성 기간(일)</label>
            <input type="number" value={leadTime} min={1}
                   onChange={e => setLeadTime(Number(e.target.value))} style={{ width: 80 }} />
          </div>
        </div>
        <div className="form-group">
          <label>제목 템플릿 ({"{date}"} = 회차 날짜로 치환)</label>
          <input type="text" value={titleTemplate} onChange={e => setTitleTemplate(e.target.value)} />
        </div>
        <div className="form-group">
          <label>설명</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2} />
        </div>
        <div className="form-group">
          <label>공개 범위</label>
          <select value={privacy} onChange={e => setPrivacy(e.target.value)}>
            <option value="private">private</option>
            <option value="unlisted">unlisted</option>
            <option value="public">public</option>
          </select>
        </div>
        <SequenceEditor value={items} onChange={setItems} scenes={scenes} />
        <div style={{ marginTop: 16 }}>
          <button className="btn-primary" onClick={create}>시리즈 생성</button>
        </div>
      </div>

      <ul className="item-list" style={{ marginTop: 12 }}>
        {series.map(sr => (
          <li key={sr.id} className="item-row" style={{ flexDirection: "column", alignItems: "stretch" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="item-title">{sr.title_template}</span>
              <span className="item-meta">{sr.recurrence_rule}</span>
              {!sr.active && <span className="badge badge-error">중단됨</span>}
              {sr.generation_error && <span className="badge badge-error">생성 오류</span>}
              <div className="item-actions">
                <button className="btn-secondary btn-sm" onClick={() => toggleOccurrences(sr.id)}>
                  {occurrences[sr.id] ? "회차 숨기기" : "회차 보기"}
                </button>
                {sr.active && (
                  <button className="btn-secondary btn-sm" onClick={() => generateNow(sr.id)}>
                    지금 생성 확인
                  </button>
                )}
                {sr.active && (
                  <button className="btn-danger btn-sm" onClick={() => stopSeries(sr.id)}>중단</button>
                )}
              </div>
            </div>
            {sr.generation_error && (
              <div style={{ marginTop: 6, fontSize: 12, color: "#f08080" }}>{sr.generation_error}</div>
            )}
            {occurrences[sr.id] && (
              <ul style={{ marginTop: 8, paddingLeft: 16, fontSize: 13 }}>
                {occurrences[sr.id].map(o => (
                  <li key={o.id}>
                    #{o.id} {new Date(o.start_at).toLocaleString("ko-KR")} — {o.status}
                  </li>
                ))}
                {occurrences[sr.id].length === 0 && <li style={{ color: "var(--text-dim)" }}>생성된 회차 없음</li>}
              </ul>
            )}
          </li>
        ))}
        {series.length === 0 && (
          <li style={{ color: "var(--text-dim)", padding: "8px 0" }}>반복 시리즈가 없습니다.</li>
        )}
      </ul>
    </div>
  );
}
