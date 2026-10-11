import { addDays, daysBetween, formatMinutes, shortDate, today } from '../lib/dates.js';
import MoodBreak from './MoodBreak.jsx';

const MOODS = ['low', 'medium', 'high'];

export default function Sidebar({ state, dispatch }) {
  const t = today();
  const weekEnd = addDays(t, 6);
  const week = state.sessions.filter((s) => s.date >= t && s.date <= weekEnd);
  const planned = week.reduce((n, s) => n + s.minutes, 0);
  const done = week.filter((s) => s.done).reduce((n, s) => n + s.minutes, 0);
  const perDay = {};
  week.forEach((s) => (perDay[s.date] = (perDay[s.date] || 0) + s.minutes));
  const overDays = Object.values(perDay).filter((m) => m > state.daily).length;
  const nextDue = [...state.assignments].filter((a) => a.due >= t).sort((a, b) => a.due.localeCompare(b.due))[0];
  const sorted = [...state.assignments].sort((a, b) => a.due.localeCompare(b.due));

  return (
    <aside className="side">
      <section className="panel" aria-labelledby="h-feel">
        <h2 id="h-feel">How are you feeling?</h2>
        <div className="seg">
          {MOODS.map((m) => (
            <button key={m} type="button" className={`mood-${m}`} aria-pressed={state.mood === m} onClick={() => dispatch({ type: 'setMood', mood: m })}>
              {m[0].toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>
        <p className="hint" style={{ marginTop: 10 }}>
          Optional stress check-in. When it’s high, new plans use shorter sessions and keep busy days lighter.
        </p>
        <MoodBreak mood={state.mood} />
      </section>

      <section className="panel" aria-labelledby="h-week">
        <h2 id="h-week">This week</h2>
        <div className="stats">
          <div className="stat"><b>{formatMinutes(planned)}</b><span>planned, next 7 days</span></div>
          <div className="stat"><b>{planned ? Math.round((done / planned) * 100) : 0}%</b><span>of that done</span></div>
          <div className="stat"><b className={overDays ? 'warn-text' : ''}>{overDays}</b><span>day{overDays === 1 ? '' : 's'} over your limit</span></div>
          <div className="stat">
            <b>{nextDue ? (daysBetween(t, nextDue.due) === 0 ? 'Today' : `${daysBetween(t, nextDue.due)}d`) : '–'}</b>
            <span>{nextDue ? `until ${nextDue.title}` : 'nothing due'}</span>
          </div>
        </div>
      </section>

      <section className="panel" aria-labelledby="h-list">
        <h2 id="h-list">Assignments</h2>
        {state.example && (
          <div className="ex-note">
            <span>Example from the project deck. It clears when you add your own.</span>
            <button className="btn" type="button" onClick={() => dispatch({ type: 'clearExample' })}>Clear example</button>
          </div>
        )}
        {sorted.length ? (
          sorted.map((a) => {
            const i = state.assignments.indexOf(a) % 5;
            const mine = state.sessions.filter((s) => s.assignmentId === a.id);
            const total = mine.reduce((n, s) => n + s.minutes, 0);
            const fin = mine.filter((s) => s.done).reduce((n, s) => n + s.minutes, 0);
            const left = daysBetween(t, a.due);
            return (
              <div className="a" key={a.id} style={{ '--cc': `var(--c${i})` }}>
                <div className="a-t">{a.title}</div>
                <button className="btn ghost" type="button" aria-label={`Remove ${a.title}`} onClick={() => dispatch({ type: 'deleteAssignment', id: a.id })}>✕</button>
                <div className="a-m">
                  {a.course ? `${a.course} · ` : ''}{a.difficulty} · {a.hours}h est. ·{' '}
                  <span className={left <= 2 ? 'warn-text' : ''}>{left < 0 ? 'past due' : left === 0 ? 'due today' : `due ${shortDate(a.due)}`}</span>
                </div>
                <div className="prog"><i style={{ width: `${total ? (fin / total) * 100 : 0}%` }} /></div>
              </div>
            );
          })
        ) : (
          <p className="hint">Assignments you add show up here with their progress.</p>
        )}
      </section>
    </aside>
  );
}
