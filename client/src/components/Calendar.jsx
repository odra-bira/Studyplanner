import { useState } from 'react';
import { addDays, formatMinutes, parse, shortDate, today, toIso, weekday, monthDay } from '../lib/dates.js';

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

/** Month grid of planned sessions and due dates. Selecting a day lists its sessions underneath. */
export default function Calendar({ state, renderCard }) {
  const t = today();
  const [month, setMonth] = useState(t.slice(0, 7)); // "YYYY-MM"
  const [sel, setSel] = useState(t);

  const first = `${month}-01`;
  const gridStart = addDays(first, -parse(first).getDay());
  const cells = Array.from({ length: 42 }, (_, i) => addDays(gridStart, i));
  const rows = cells.slice(35).every((d) => d.slice(0, 7) !== month) ? 5 : 6;
  const label = parse(first).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const colorOf = (id) => Math.max(0, state.assignments.findIndex((a) => a.id === id)) % 5;
  const shift = (n) => {
    const d = parse(first);
    d.setMonth(d.getMonth() + n);
    setMonth(toIso(d).slice(0, 7));
  };
  const goToday = () => { setMonth(t.slice(0, 7)); setSel(t); };

  const selSessions = state.sessions.filter((s) => s.date === sel);
  const selDues = state.assignments.filter((a) => a.due === sel);
  const selBooked = selSessions.reduce((n, s) => n + s.minutes, 0);

  return (
    <div className="cal">
      <div className="cal-head">
        <button type="button" className="btn ghost" onClick={() => shift(-1)} aria-label="Previous month">‹</button>
        <b className="cal-title">{label}</b>
        <button type="button" className="btn ghost" onClick={() => shift(1)} aria-label="Next month">›</button>
        <button type="button" className="btn ghost cal-today" onClick={goToday}>Today</button>
      </div>

      <div className="cal-grid" role="grid" aria-label={label}>
        {DOW.map((d) => <div key={d} className="cal-dow" role="columnheader">{d}</div>)}
        {cells.slice(0, rows * 7).map((d) => {
          const ss = state.sessions.filter((s) => s.date === d);
          const dues = state.assignments.filter((a) => a.due === d);
          const booked = ss.reduce((n, s) => n + s.minutes, 0);
          const cls = ['cal-day', d.slice(0, 7) !== month && 'other', d === t && 'is-today', d === sel && 'sel', d < t && 'past']
            .filter(Boolean).join(' ');
          return (
            <button
              key={d}
              type="button"
              role="gridcell"
              className={cls}
              aria-selected={d === sel}
              aria-label={`${shortDate(d)}: ${ss.length} session${ss.length === 1 ? '' : 's'}${dues.length ? `, ${dues.length} due` : ''}`}
              onClick={() => setSel(d)}
            >
              <span className="cal-num">{parse(d).getDate()}</span>
              {dues.length > 0 && <span className="cal-due" title={dues.map((a) => a.title).join(', ')}>Due</span>}
              <span className="cal-dots">
                {ss.slice(0, 6).map((s) => (
                  <i key={s.id} className={s.done ? 'done' : ''} style={{ background: `var(--c${colorOf(s.assignmentId)})` }} />
                ))}
              </span>
              {booked > 0 && <span className={`cal-min ${booked > state.daily ? 'over' : ''}`}>{formatMinutes(booked)}</span>}
            </button>
          );
        })}
      </div>

      <div className="cal-sel">
        <div className="day-h">
          <span className="day-name">{weekday(sel)}</span>
          <span className="day-date">{monthDay(sel)}</span>
          {sel === t && <span className="tag today">Today</span>}
          {selDues.map((a) => <span key={a.id} className="tag due">Due: {a.title}</span>)}
          {selBooked > 0 && <span className="load">{formatMinutes(selBooked)} / {formatMinutes(state.daily)}</span>}
        </div>
        {selSessions.length ? selSessions.map(renderCard) : <p className="free">Nothing planned for this day.</p>}
      </div>
    </div>
  );
}
