import { useState } from 'react';
import { JOKES, MOOD_LINES, REASONS, RIDDLES } from '../lib/breaks.js';
import BreakTimer from './BreakTimer.jsx';

const pick = (list, not) => {
  if (list.length < 2) return 0;
  let i;
  do i = Math.floor(Math.random() * list.length);
  while (i === not);
  return i;
};

const norm = (s) => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim();

export default function MoodBreak({ mood }) {
  const [kind, setKind] = useState(mood === 'high' ? 'joke' : 'riddle');
  const [idx, setIdx] = useState({ joke: pick(JOKES), riddle: pick(RIDDLES) });
  const [shown, setShown] = useState(false);
  const [guess, setGuess] = useState('');
  const [result, setResult] = useState(null); // 'right' | 'wrong' | null
  const [score, setScore] = useState(0);
  const [reason, setReason] = useState(null);

  const list = kind === 'joke' ? JOKES : RIDDLES;
  const item = list[idx[kind]];

  const reset = () => { setShown(false); setGuess(''); setResult(null); };
  const switchKind = (k) => { setKind(k); reset(); };
  const next = () => { setIdx((p) => ({ ...p, [kind]: pick(list, p[kind]) })); reset(); };

  const submit = (e) => {
    e.preventDefault();
    const g = norm(guess);
    if (!g) return;
    const ok = item.accept.some((w) => g.includes(w));
    setResult(ok ? 'right' : 'wrong');
    if (ok) { setShown(true); setScore((s) => s + 1); }
  };

  return (
    <div className="brk">
      <h3 className="brk-h">Take a break</h3>
      {mood && <p className="hint">{MOOD_LINES[mood]}</p>}
      {mood && (
        <>
          <div className="chips" role="group" aria-label="Why do you feel this way?">
            <span className="hint">Why?</span>
            {REASONS.map((r) => (
              <button key={r.id} type="button" className="chip" aria-pressed={reason === r.id} onClick={() => setReason(reason === r.id ? null : r.id)}>
                {r.label}
              </button>
            ))}
          </div>
          {reason && <p className="hint">{REASONS.find((r) => r.id === reason).tip}</p>}
        </>
      )}
      <BreakTimer mood={mood} />
      <div className="seg seg2" role="group" aria-label="Break type">
        <button type="button" aria-pressed={kind === 'joke'} onClick={() => switchKind('joke')}>Jokes</button>
        <button type="button" aria-pressed={kind === 'riddle'} onClick={() => switchKind('riddle')}>Riddles</button>
      </div>

      <div className="brk-card" aria-live="polite">
        <p className="brk-q">{item.q}</p>

        {kind === 'riddle' && !shown && (
          <form className="brk-guess" onSubmit={submit}>
            <input
              value={guess}
              onChange={(e) => { setGuess(e.target.value); setResult(null); }}
              placeholder="Your guess"
              aria-label="Your guess"
            />
            <button className="btn soft" type="submit">Guess</button>
          </form>
        )}
        {result === 'wrong' && <p className="brk-msg warn-text">Not quite. Try again or reveal the answer.</p>}
        {result === 'right' && <p className="brk-msg brk-ok">Correct!</p>}

        {shown && <p className="brk-a">{item.a}</p>}

        <div className="brk-actions">
          {!shown && (
            <button className="btn" type="button" onClick={() => setShown(true)}>
              {kind === 'joke' ? 'Punchline' : 'Reveal'}
            </button>
          )}
          <button className="btn primary" type="button" onClick={next}>Another one</button>
        </div>
      </div>

      {score > 0 && <p className="hint">Riddles solved this session: {score}</p>}
    </div>
  );
}
