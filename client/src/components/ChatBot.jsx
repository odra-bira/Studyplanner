import { useEffect, useRef, useState } from 'react';
import { api, UPLOAD_ACCEPT } from '../lib/api.js';
import { addDays, shortDate, today } from '../lib/dates.js';
import { Clip, Send, Sparkle } from './Icons.jsx';

const WELCOME = {
  role: 'assistant',
  content: 'Hi! Upload an assignment sheet (PDF, photo or text file) and I’ll tell you how difficult it is and how long it should take. You can also ask me about your plan.',
};

/** Text version of a message, sent back to the server as chat history. */
function historyText(m) {
  if (m.role === 'user') return m.content || (m.fileName ? `(Uploaded ${m.fileName})` : '');
  if (!m.assessment) return m.content;
  const a = m.assessment;
  return `${m.content}\n[Assessment of "${a.title}": ${a.difficulty}, about ${a.hours} hours${a.due ? `, due ${a.due}` : ''}.]`;
}

export default function ChatBot({ open, onClose, state, aiOn, aiName, onAddToPlanner }) {
  const [messages, setMessages] = useState([WELCOME]);
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [sending, setSending] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);
  const listEnd = useRef(null);

  // Braces matter: newer browsers make scrollIntoView return a Promise, and an effect may only return a cleanup function.
  useEffect(() => {
    listEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, sending]);

  async function send(e) {
    e?.preventDefault();
    if (sending || (!text.trim() && !file)) return;
    const userMsg = { role: 'user', content: text.trim(), fileName: file?.name };
    const next = [...messages, userMsg];
    setMessages(next);
    setText('');
    const sentFile = file;
    setFile(null);
    setSending(sentFile ? 'file' : 'text');
    try {
      const payload = {
        today: today(),
        messages: next.filter((m) => m !== WELCOME).map((m) => ({ role: m.role, content: historyText(m) })).filter((m) => m.content),
        assignments: state.assignments,
        sessions: state.sessions,
      };
      const res = await api.chat(payload, sentFile);
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, assessment: res.assessment }]);
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: err.message, error: true }]);
    } finally {
      setSending(false);
    }
  }

  function pick(f) {
    if (f) setFile(f);
  }

  return (
    <aside
      className={`chat ${open ? 'open' : ''} ${dragging ? 'drag' : ''}`}
      aria-label="Ask StudyEase"
      aria-hidden={!open}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files?.[0]); }}
    >
      <div className="chat-head">
        <div>
          <b><Sparkle /> Ask StudyEase</b>
          <span className="chat-mode">{aiOn ? `Powered by ${aiName}` : 'Demo mode: text files and text PDFs'}</span>
        </div>
        <button className="btn ghost" type="button" onClick={onClose} aria-label="Close chat">✕</button>
      </div>

      <div className="chat-list">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role} ${m.error ? 'error' : ''}`}>
            {m.fileName && <div className="file-chip">📄 {m.fileName}</div>}
            {m.content && <p>{m.content}</p>}
            {m.assessment && <AssessmentCard a={m.assessment} onAdd={onAddToPlanner} />}
          </div>
        ))}
        {sending && <div className="msg assistant"><p className="pulse">{sending === 'file' ? 'Reading your file…' : 'Thinking…'}</p></div>}
        <div ref={listEnd} />
      </div>

      <form className="chat-input" onSubmit={send}>
        {file && (
          <div className="file-chip pending">
            📄 {file.name}
            <button type="button" className="btn ghost" onClick={() => setFile(null)} aria-label="Remove file">✕</button>
          </div>
        )}
        <div className="chat-row">
          <button type="button" className="btn ghost clip" onClick={() => fileInput.current?.click()} aria-label="Attach an assignment file">
            <Clip />
          </button>
          <input ref={fileInput} type="file" accept={UPLOAD_ACCEPT} hidden onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ''; }} />
          <textarea
            value={text}
            rows={1}
            placeholder={file ? 'Add a note (optional)…' : 'Ask, or attach an assignment'}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) send(e); }}
          />
          <button className="btn primary send" type="submit" disabled={sending || (!text.trim() && !file)} aria-label="Send">
            <Send />
          </button>
        </div>
      </form>
    </aside>
  );
}

function AssessmentCard({ a, onAdd }) {
  const [due, setDue] = useState(a.due || addDays(today(), 7));
  const [hours, setHours] = useState(a.hours);
  const [state, setState] = useState('idle'); // idle | adding | added

  async function add() {
    setState('adding');
    const ok = await onAdd({ title: a.title, course: a.course, due, difficulty: a.difficulty, hours: Number(hours) || a.hours });
    setState(ok ? 'added' : 'idle');
  }

  return (
    <div className="assess">
      <div className="assess-top">
        <span className={`diff ${a.difficulty}`}>{a.difficulty}</span>
        <span className="assess-title">{a.course ? `${a.course} · ` : ''}{a.title}</span>
      </div>
      <div className="assess-nums">
        <div><b>{a.hours}h</b><span>estimated work</span></div>
        <div><b>{a.due ? shortDate(a.due) : '—'}</b><span>{a.due ? 'due date found' : 'no due date found'}</span></div>
      </div>
      {a.reasons?.length > 0 && (
        <>
          <h4>Why this rating</h4>
          <ul>{a.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </>
      )}
      {a.firstSteps?.length > 0 && (
        <>
          <h4>Start with</h4>
          <ul>{a.firstSteps.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </>
      )}
      {state === 'added' ? (
        <p className="added">Added to your plan ✓</p>
      ) : (
        <div className="assess-add">
          <label className="f">Due<input type="date" value={due} min={today()} onChange={(e) => setDue(e.target.value)} /></label>
          <label className="f">Hours<input type="number" min={0.5} max={40} step={0.5} value={hours} onChange={(e) => setHours(e.target.value)} /></label>
          <button className="btn primary" type="button" onClick={add} disabled={state === 'adding'}>
            {state === 'adding' ? 'Planning…' : 'Add to planner'}
          </button>
        </div>
      )}
    </div>
  );
}
