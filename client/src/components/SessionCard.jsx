import { useState } from 'react';
import { addDays, shortDate, today } from '../lib/dates.js';

function dayOptions(selected, due) {
  const t = today();
  const start = selected < t ? selected : t;
  const end = due && due > t ? due : addDays(t, 6);
  const out = [];
  for (let d = start; d <= end; d = addDays(d, 1)) out.push(d);
  return out;
}

export default function SessionCard({ session: s, assignment: a, color, dispatch, onBreakDown }) {
  const [task, setTask] = useState(s.task);
  const [thinking, setThinking] = useState(false);
  const update = (patch) => dispatch({ type: 'updateSession', id: s.id, patch });

  function toggleStep(i, done) {
    const steps = s.steps.map((x, j) => (j === i ? { ...x, done } : x));
    update({ steps, done: steps.every((x) => x.done) || s.done });
  }

  async function breakDown() {
    setThinking(true);
    await onBreakDown(s);
    setThinking(false);
  }

  return (
    <div className={`s ${s.done ? 'done' : ''}`} style={{ '--cc': `var(--c${color})` }}>
      <input type="checkbox" checked={s.done} onChange={(e) => update({ done: e.target.checked })} aria-label="Mark session done" />
      <div className="main">
        <input
          className="task"
          value={task}
          maxLength={80}
          aria-label="Session step"
          onChange={(e) => setTask(e.target.value)}
          onBlur={() => (task.trim() ? update({ task: task.trim() }) : setTask(s.task))}
          onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
        />
        <div className="meta">
          <span className="course">{a ? `${a.course ? `${a.course} · ` : ''}${a.title}` : 'Unknown assignment'}</span>
          {a && <span>due {shortDate(a.due)}</span>}
        </div>
        {s.why && (
          <p className="why">
            <b>Why:</b> {s.why}
          </p>
        )}
      </div>
      <div className="ctrl">
        <div className="ctrl-row">
          <input
            className="mins"
            type="number"
            min={10}
            max={300}
            step={5}
            value={s.minutes}
            aria-label="Minutes"
            onChange={(e) => update({ minutes: Math.max(5, Math.min(300, Number(e.target.value) || 0)) })}
          />
          <span className="unit">min</span>
        </div>
        <select className="mv" value={s.date} aria-label="Move to day" onChange={(e) => update({ date: e.target.value, why: 'Moved by you.' })}>
          {dayOptions(s.date, a?.due).map((d) => (
            <option key={d} value={d}>{shortDate(d)}</option>
          ))}
        </select>
        <div className="ctrl-row">
          {!s.steps?.length && (
            <button className="btn ghost" type="button" onClick={breakDown} disabled={thinking} title="Split into a checklist">
              {thinking ? 'Thinking…' : 'Break down'}
            </button>
          )}
          <button className="btn ghost" type="button" onClick={() => dispatch({ type: 'deleteSession', id: s.id })} aria-label="Delete session">
            ✕
          </button>
        </div>
      </div>
      {s.steps?.length > 0 && (
        <ul className="steps">
          {s.steps.map((step, i) => (
            <li key={i}>
              <label>
                <input type="checkbox" checked={step.done} onChange={(e) => toggleStep(i, e.target.checked)} />
                <span className={step.done ? 'x' : ''}>{step.t}</span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
