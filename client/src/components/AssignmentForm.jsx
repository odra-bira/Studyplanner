import { useRef, useState } from 'react';
import { api, MAX_UPLOAD_MB, UPLOAD_ACCEPT } from '../lib/api.js';
import { addDays, formatMinutes, shortDate, today } from '../lib/dates.js';
import { Clip, Sparkle, Status } from './Icons.jsx';

const HOURS = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 15, 20];
const DAILY = [30, 45, 60, 90, 120, 150, 180, 240];
const DIFFICULTIES = ['easy', 'medium', 'hard'];

const nearestHours = (h) => HOURS.reduce((best, v) => (Math.abs(v - h) < Math.abs(best - h) ? v : best), HOURS[0]);
let uploadId = 0;

export default function AssignmentForm({ daily, onDailyChange, onSubmit, busy, status, aiOn, aiName }) {
  const [title, setTitle] = useState('');
  const [course, setCourse] = useState('');
  const [due, setDue] = useState(addDays(today(), 5));
  const [difficulty, setDifficulty] = useState('medium');
  const [hours, setHours] = useState(3);
  const [error, setError] = useState(null);
  const [uploads, setUploads] = useState([]); // { id, name, status: 'reading' | 'done' | 'error', a?, note? }
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);

  const patchUpload = (id, patch) => setUploads((u) => u.map((x) => (x.id === id ? { ...x, ...patch } : x)));

  function fillFrom(a) {
    setTitle(a.title);
    setCourse(a.course || '');
    if (a.due && a.due >= today()) setDue(a.due);
    setDifficulty(a.difficulty);
    setHours(nearestHours(a.hours));
    setError(null);
  }

  /** Reads each file one at a time; the first result fills an empty form. */
  async function readFiles(fileList) {
    const files = [...fileList];
    if (!files.length) return;
    const rows = files.map((f) => ({ id: ++uploadId, file: f, name: f.name, status: 'reading' }));
    setUploads((u) => [...rows.map(({ file, ...r }) => r), ...u]);
    let filled = Boolean(title.trim());
    for (const { id, file } of rows) {
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        patchUpload(id, { status: 'error', note: `Over ${MAX_UPLOAD_MB} MB. Try a smaller file.` });
        continue;
      }
      try {
        const res = await api.chat({ today: today(), messages: [], assignments: [], sessions: [] }, file);
        if (res.assessment) {
          patchUpload(id, { status: 'done', a: res.assessment, note: res.reply });
          if (!filled) {
            fillFrom(res.assessment);
            filled = true;
          }
        } else {
          patchUpload(id, { status: 'error', note: res.reply || 'Could not read this file.' });
        }
      } catch (err) {
        patchUpload(id, { status: 'error', note: err.message });
      }
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (!title.trim()) return setError('Give the assignment a name.');
    if (!due || due < today()) return setError('Pick a due date from today onward.');
    setError(null);
    const ok = await onSubmit({ title: title.trim(), course: course.trim(), due, difficulty, hours: Number(hours) });
    if (ok) setTitle('');
  }

  return (
    <section className="panel" aria-labelledby="h-assign">
      <h2 id="h-assign">Task</h2>
      <form className="stack" onSubmit={submit} autoComplete="off">
        <div
          className={`drop ${dragging ? 'drag' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); readFiles(e.dataTransfer.files); }}
        >
          <button type="button" className="btn soft" onClick={() => fileInput.current?.click()}>
            <Clip /> Upload PDF or study materials
          </button>
          <input ref={fileInput} type="file" accept={UPLOAD_ACCEPT} multiple hidden onChange={(e) => { readFiles(e.target.files); e.target.value = ''; }} />
          <p className="hint">Or drop files here. {aiOn ? 'Title, difficulty, hours and due date are filled in for you.' : 'Demo mode reads text files and text PDFs.'}</p>
        </div>
        {uploads.length > 0 && (
          <ul className="ups" aria-live="polite">
            {uploads.map((u) => (
              <li key={u.id} className={`up ${u.status}`}>
                <div className="up-top">
                  <span className="up-name">📄 {u.name}</span>
                  <button type="button" className="btn ghost" aria-label={`Remove ${u.name}`} onClick={() => setUploads((x) => x.filter((r) => r.id !== u.id))}>✕</button>
                </div>
                {u.status === 'reading' && <span className="hint pulse">Reading…</span>}
                {u.status === 'error' && <span className="hint warn-text">{u.note}</span>}
                {u.status === 'done' && (
                  <>
                    <span className="hint">
                      <span className={`diff ${u.a.difficulty}`}>{u.a.difficulty}</span> {u.a.title} · about {u.a.hours}h
                      {u.a.due ? ` · due ${shortDate(u.a.due)}` : ''}
                    </span>
                    <button type="button" className="btn soft up-use" onClick={() => fillFrom(u.a)}>Use these details</button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
        <label className="f">
          What is it?
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Lab report on enzyme kinetics" maxLength={80} />
        </label>
        <div className="row2">
          <label className="f">
            Course
            <input value={course} onChange={(e) => setCourse(e.target.value)} placeholder="BIO 201" maxLength={20} />
          </label>
          <label className="f">
            Due
            <input type="date" value={due} min={today()} onChange={(e) => setDue(e.target.value)} />
          </label>
        </div>
        <div className="f" role="group" aria-label="Difficulty">
          <span>Difficulty</span>
          <div className="seg">
            {DIFFICULTIES.map((d) => (
              <button key={d} type="button" aria-pressed={difficulty === d} onClick={() => setDifficulty(d)}>
                {d[0].toUpperCase() + d.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div className="row2">
          <label className="f">
            Estimated work
            <select value={hours} onChange={(e) => setHours(Number(e.target.value))}>
              {HOURS.map((h) => (
                <option key={h} value={h}>{h} hour{h === 1 ? '' : 's'}</option>
              ))}
            </select>
          </label>
          <label className="f">
            Available / day
            <select value={daily} onChange={(e) => onDailyChange(Number(e.target.value))}>
              {DAILY.map((m) => (
                <option key={m} value={m}>{formatMinutes(m)} / day</option>
              ))}
            </select>
          </label>
        </div>
        <button className="btn primary" type="submit" disabled={busy}>
          <Sparkle /> {busy ? 'Planning…' : 'Suggest a plan'}
        </button>
        <Status status={error ? { kind: 'err', text: error } : status} />
        {!aiOn && (
          <p className="hint">Running without an AI provider: the built-in planner spreads the work across your free days.</p>
        )}
      </form>
    </section>
  );
}
