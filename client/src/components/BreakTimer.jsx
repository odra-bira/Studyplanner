import { useEffect, useRef, useState } from 'react';
import { BREAK_SECONDS } from '../lib/breaks.js';

const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

export default function BreakTimer({ mood }) {
  const total = BREAK_SECONDS[mood];
  const [left, setLeft] = useState(total);
  const [running, setRunning] = useState(false);
  const endRef = useRef(0);

  // A new mood means a new break length.
  useEffect(() => { setLeft(total); setRunning(false); }, [total]);

  useEffect(() => {
    if (!running) return undefined;
    const id = setInterval(() => {
      const s = Math.max(0, Math.round((endRef.current - Date.now()) / 1000));
      setLeft(s);
      if (s === 0) setRunning(false);
    }, 250);
    return () => clearInterval(id);
  }, [running]);

  if (!total) return <p className="hint">Pick how you’re feeling to get a timed break: Low 1 min, Medium 2 min, High 5 min.</p>;

  const start = () => { endRef.current = Date.now() + left * 1000; setRunning(true); };
  const pause = () => setRunning(false);
  const reset = () => { setRunning(false); setLeft(total); };
  const finished = left === 0;
  const pct = ((total - left) / total) * 100;

  return (
    <div className="tmr">
      <div className="tmr-top">
        <span className="tmr-time" role="timer" aria-live="off">{fmt(left)}</span>
        <span className="hint">{total / 60} min break</span>
      </div>
      <div className="prog" aria-hidden="true"><i style={{ width: `${pct}%` }} /></div>
      <div className="brk-actions">
        {!running && !finished && <button className="btn primary" type="button" onClick={start}>{left === total ? 'Start break' : 'Resume'}</button>}
        {running && <button className="btn" type="button" onClick={pause}>Pause</button>}
        {(left !== total || finished) && <button className="btn" type="button" onClick={reset}>Reset</button>}
      </div>
      {finished && <p className="brk-ok" role="status">Break’s over. Ready for the next session?</p>}
    </div>
  );
}
