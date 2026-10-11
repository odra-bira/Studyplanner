export const Sparkle = () => (
  <svg className="icon" viewBox="0 0 16 16" aria-hidden="true">
    <path fill="currentColor" d="M8 0l1.8 5.2L15 7l-5.2 1.8L8 14l-1.8-5.2L1 7l5.2-1.8z" />
  </svg>
);

export const Clip = () => (
  <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M21 11.5l-8.6 8.6a5 5 0 01-7.1-7.1l8.6-8.6a3.3 3.3 0 014.7 4.7l-8.6 8.6a1.7 1.7 0 01-2.4-2.4l8-8" />
  </svg>
);

export const Send = () => (
  <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="currentColor" d="M3 20.5V14l9-2-9-2V3.5L22 12z" />
  </svg>
);

export function Status({ status }) {
  if (!status) return null;
  return (
    <div className={`status ${status.kind === 'err' ? 'err' : status.kind === 'warn' ? 'warn' : ''} ${status.kind === 'busy' ? 'pulse' : ''}`} role="status">
      {status.text}
    </div>
  );
}
