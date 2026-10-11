import { useState } from 'react';
import { addDays, formatMinutes, monthDay, shortDate, today, weekday } from '../lib/dates.js';
import { Sparkle, Status } from './Icons.jsx';
import Calendar from './Calendar.jsx';
import SessionCard from './SessionCard.jsx';

/** Groups sessions by day from today through the latest planned date (at least a week). */
function buildDays(state) {
  const t = today();
  const last = state.sessions.reduce((m, s) => (s.date > m ? s.date : m), t);
  const end = last < addDays(t, 6) ? addDays(t, 6) : last;
  const out = [];
  let freeRun = [];
  const flush = () => {
    if (freeRun.length) out.push({ kind: 'free', dates: freeRun });
    freeRun = [];
  };
  for (let d = t; d <= end; d = addDays(d, 1)) {
    const sessions = state.sessions.filter((s) => s.date === d);
    if (!sessions.length && d !== t) {
      freeRun.push(d);
      continue;
    }
    flush();
    out.push({ kind: 'day', date: d, sessions });
  }
  flush();
  return out;
}

export default function PlanView({ state, dispatch, onRebalance, onBreakDown, busy, status }) {
  const t = today();
  const [view, setView] = useState('list'); // 'list' | 'calendar'
  const missed = state.sessions.filter((s) => s.date < t && !s.done);
  const colorIndex = Object.fromEntries(state.assignments.map((a, i) => [a.id, i % 5]));
  const card = (s) => (
    <SessionCard
      key={s.id}
      session={s}
      assignment={state.assignments.find((a) => a.id === s.assignmentId)}
      color={colorIndex[s.assignmentId] ?? 0}
      dispatch={dispatch}
      onBreakDown={onBreakDown}
    />
  );

  return (
    <section className="panel" aria-labelledby="h-plan">
      <div className="plan-head">
        <h2 id="h-plan">Suggested sessions</h2>
        {state.sessions.length > 0 && (
          <div className="seg seg2 view-toggle" role="group" aria-label="View">
            <button type="button" aria-pressed={view === 'list'} onClick={() => setView('list')}>List</button>
            <button type="button" aria-pressed={view === 'calendar'} onClick={() => setView('calendar')}>Calendar</button>
          </div>
        )}
        <button className="btn soft" type="button" onClick={onRebalance} disabled={busy || !state.sessions.length}>
          <Sparkle /> {busy ? 'Rebalancing…' : 'Rebalance my week'}
        </button>
      </div>
      <Status status={status} />

      {!state.sessions.length ? (
        <div className="empty">
          <b>No sessions yet</b>
          <ol className="how">
            <li><span>1</span>Add an assignment, or upload a PDF or study material</li>
            <li><span>2</span>Get a day-by-day plan with a reason for each session</li>
            <li><span>3</span>Tick sessions off, or rebalance your week anytime</li>
          </ol>
        </div>
      ) : (
        <>
          {missed.length > 0 && (
            <div className="day">
              <div className="day-h">
                <span className="day-name">Missed</span>
                <span className="tag missed">{missed.length} to reschedule</span>
                <span className="load">Use “Rebalance my week” to fit these back in</span>
              </div>
              {missed.map(card)}
            </div>
          )}
          {view === 'calendar' && <Calendar state={state} renderCard={card} />}
          {view === 'list' && buildDays(state).map((day) => {
            if (day.kind === 'free') {
              const [a, b] = [day.dates[0], day.dates.at(-1)];
              return (
                <div className="day" key={a}>
                  <p className="free">{a === b ? shortDate(a) : `${shortDate(a)} – ${shortDate(b)}`} · free</p>
                </div>
              );
            }
            const booked = day.sessions.reduce((n, s) => n + s.minutes, 0);
            const over = booked > state.daily;
            const dues = state.assignments.filter((a) => a.due === day.date);
            return (
              <div className="day" key={day.date}>
                <div className="day-h">
                  <span className="day-name">{weekday(day.date)}</span>
                  <span className="day-date">{monthDay(day.date)}</span>
                  {day.date === t && <span className="tag today">Today</span>}
                  {dues.map((a) => (
                    <span key={a.id} className="tag due">Due: {a.title}</span>
                  ))}
                  <span className={`load ${over ? 'over' : ''}`} title="Planned minutes vs your daily time">
                    <span className={`meter ${over ? 'over' : ''}`}>
                      <i style={{ width: `${Math.min(100, (booked / state.daily) * 100)}%` }} />
                    </span>
                    {formatMinutes(booked)} / {formatMinutes(state.daily)}
                    {over ? ' · over' : ''}
                  </span>
                </div>
                {day.sessions.length ? day.sessions.map(card) : <p className="free">Nothing planned today.</p>}
              </div>
            );
          })}
        </>
      )}
    </section>
  );
}
