import type { Scene, SequenceItem } from "../types";
export default function SequenceEditor(
  { value, onChange, scenes }:
  { value: SequenceItem[]; onChange: (v: SequenceItem[]) => void; scenes: Scene[] }) {
  const add = (scene_id: number) =>
    onChange([...value, { scene_id, order_index: value.length, duration_seconds: 60 }]);
  const setDur = (i: number, d: number) =>
    onChange(value.map((it, idx) => idx === i ? { ...it, duration_seconds: d } : it));
  return (
    <div><h4>시퀀스 편성</h4>
      <select onChange={e => add(Number(e.target.value))} value="">
        <option value="" disabled>씬 추가...</option>
        {scenes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <ol>{value.map((it, i) => {
        const sc = scenes.find(s => s.id === it.scene_id);
        return <li key={i}>{sc?.name}
          <input type="number" value={it.duration_seconds ?? 0}
                 onChange={e => setDur(i, Number(e.target.value))} /> 초</li>;
      })}</ol>
    </div>);
}
