// Calls to the StudyEase server. Every call throws an Error with a readable message on failure.

async function request(path, options) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new Error("Can't reach the StudyEase server. Is it running (npm run dev)?");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status}).`);
  return data;
}

/** File types the server can read (also used by the paperclip button and the upload box). */
export const UPLOAD_ACCEPT = '.pdf,.txt,.md,image/png,image/jpeg,image/webp,image/gif';
export const MAX_UPLOAD_MB = 10;

const postJson = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const api = {
  health: () => request('/api/health'),
  plan: (body) => postJson('/api/plan', body),
  rebalance: (body) => postJson('/api/rebalance', body),
  breakdown: (body) => postJson('/api/breakdown', body),

  /** Chat turn, optionally with one uploaded file (multipart). */
  chat(payload, file) {
    const form = new FormData();
    form.append('payload', JSON.stringify(payload));
    if (file) form.append('file', file);
    return request('/api/chat', { method: 'POST', body: form });
  },
};
