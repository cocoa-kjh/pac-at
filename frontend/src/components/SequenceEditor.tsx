import type { Scene, SequenceItem } from "../types";

export default function SequenceEditor(
  { value, onChange, scenes }:
  { value: SequenceItem[]; onChange: (v: SequenceItem[]) => void; scenes: Scene[] }
) {
  const add = (scene_id: number) =>
    onChange([...value, { scene_id, order_index: value.length, duration_seconds: 60 }]);

  const setDur = (i: number, d: number) =>
    onChange(value.map((it, idx) => idx === i ? { ...it, duration_seconds: d } : it));

  const remove = (i: number) =>
    onChange(value.filter((_, idx) => idx !== i).map((it, idx) => ({ ...it, order_index: idx })));

  return (
    <div>
      <h4>시퀀스 편성</h4>
      <div style={{ marginBottom: 8 }}>
        <select onChange={e => { add(Number(e.target.value)); (e.target as HTMLSelectElement).value = ""; }} value="">
          <option value="" disabled>+ 씬 추가...</option>
          {scenes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>
      {value.map((it, i) => {
        const sc = scenes.find(s => s.id === it.scene_id);
        return (
          <div key={i} className="seq-item">
            <div className="seq-index">{i + 1}</div>
            <span className="seq-name">{sc?.name ?? `씬 #${it.scene_id}`}</span>
            <input
              type="number"
              value={it.duration_seconds ?? 0}
              onChange={e => setDur(i, Number(e.target.value))}
              min={1}
            />
            <span style={{ color: "var(--text-dim)", fontSize: 12 }}>초</span>
            <button
              className="btn-danger btn-sm"
              onClick={() => remove(i)}
              style={{ padding: "2px 8px" }}
            >✕</button>
          </div>
        );
      })}
      {value.length === 0 && (
        <p style={{ color: "var(--text-dim)", fontSize: 12 }}>씬을 추가하세요.</p>
      )}
    </div>
  );
}
