import { useEffect, useState } from 'react';
import { api } from './lib/api.js';
import { formatMinutes, today } from './lib/dates.js';
import { newId, usePlanner } from './hooks/usePlanner.js';
import AssignmentForm from './components/AssignmentForm.jsx';
import PlanView from './components/PlanView.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatBot from './components/ChatBot.jsx';
import { Sparkle } from './components/Icons.jsx';

export default function App() {
  const [state, dispatch] = usePlanner();
  const [ai, setAi] = useState({ mode: 'checking' });
  const [chatOpen, setChatOpen] = useState(false);
  const [busy, setBusy] = useState(null); // 'plan' | 'rebalance' | null
  const [formStatus, setFormStatus] = useState(null);
  const [planStatus, setPlanStatus] = useState(null);

  useEffect(() => {
    api.health().then((h) => setAi({ mode: h.ai, model: h.model, label: h.label })).catch(() => setAi({ mode: 'offline' }));
  }, []);

  const aiOn = ['claude', 'gemini', 'ollama'].includes(ai.mode);
  const aiName = ai.label || 'AI';

  const context = () => ({ today: today(), daily: state.daily, mood: state.mood });

  /** Used by the form and by the chatbot's "Add to planner" button. */
  async function planAssignment(fields) {
    const assignment = { id: newId(), ...fields };
    setBusy('plan');
    setPlanStatus(null);
    setFormStatus({ kind: 'busy', text: aiOn ? `${aiName} is drafting your sessions…` : 'Planning…' });
    try {
      const res = await api.plan({ ...context(), assignment, sessions: state.sessions });
      dispatch({ type: 'addPlan', assignment, sessions: res.sessions });
      const total = res.sessions.reduce((n, s) => n + s.minutes, 0);
      const head = res.source === 'ai' ? res.note || `Planned ${res.sessions.length} sessions.` : `Built-in planner: ${res.sessions.length} sessions, ${formatMinutes(total)} total.`;
      setFormStatus({ kind: res.warnings?.length ? 'warn' : 'ok', text: [head, ...(res.warnings || [])].join(' ') });
      return true;
    } catch (err) {
      setFormStatus({ kind: 'err', text: err.message });
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function rebalance() {
    setBusy('rebalance');
    setPlanStatus({ kind: 'busy', text: aiOn ? `${aiName} is rebalancing your week…` : 'Rebalancing…' });
    try {
      const res = await api.rebalance({ ...context(), assignments: state.assignments, sessions: state.sessions });
      dispatch({ type: 'applyMoves', moves: res.moves });
      setPlanStatus({ kind: 'ok', text: res.note });
    } catch (err) {
      setPlanStatus({ kind: 'err', text: err.message });
    } finally {
      setBusy(null);
    }
  }

  async function breakDown(session) {
    const assignment = state.assignments.find((a) => a.id === session.assignmentId);
    try {
      const { steps } = await api.breakdown({ session, assignment });
      dispatch({ type: 'updateSession', id: session.id, patch: { steps: steps.map((t) => ({ t, done: false })) } });
    } catch (err) {
      setPlanStatus({ kind: 'err', text: err.message });
    }
  }

  const left = state.sessions.filter((s) => !s.done).length;

  return (
    <>
      <header className="bar">
        <div className="bar-in">
          <div className="brand"><span className="logo" aria-hidden="true">✓</span>StudyEase</div>
          <div className="bar-meta">
            <span className="pill">
              <span className={`dot ${aiOn ? 'on' : ''}`} />
              {aiOn ? `${aiName} on` : ai.mode === 'demo' ? 'Demo mode' : ai.mode === 'offline' ? 'Server offline' : 'Connecting…'}
            </span>
            <button className="btn chat-toggle" type="button" onClick={() => setChatOpen((o) => !o)} aria-expanded={chatOpen}>
              <Sparkle /> Ask StudyEase
            </button>
          </div>
        </div>
      </header>

      <main>
        <div className="hero">
          <h1>Your study plan</h1>
          <p className="sub">
            {state.assignments.length
              ? `${state.assignments.length} assignment${state.assignments.length > 1 ? 's' : ''} · ${left} sessions to go · ${formatMinutes(state.daily)} a day`
              : 'Add an assignment or upload PDFs and study materials, review the suggested sessions, then adjust anything.'}
          </p>
          <ul className="feat" aria-label="What StudyEase does">
            <li>Difficulty-aware</li>
            <li>Balances your daily workload</li>
            <li>Adapts to your stress level</li>
            <li>Reads PDFs and photos</li>
          </ul>
        </div>

        <div className="grid">
          <AssignmentForm
            daily={state.daily}
            onDailyChange={(daily) => dispatch({ type: 'setDaily', daily })}
            onSubmit={planAssignment}
            busy={busy === 'plan'}
            status={formStatus}
            aiOn={aiOn}
            aiName={aiName}
          />
          <PlanView
            state={state}
            dispatch={dispatch}
            onRebalance={rebalance}
            onBreakDown={breakDown}
            busy={busy === 'rebalance'}
            status={planStatus}
          />
          <Sidebar state={state} dispatch={dispatch} />
        </div>
        <p className="foot">Time estimates are guesses. Edit any step, move a session to another day, or change its minutes.</p>
      </main>

      <ChatBot
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        state={state}
        aiOn={aiOn}
        aiName={aiName}
        onAddToPlanner={planAssignment}
      />
    </>
  );
}
