// Local calendar dates as "YYYY-MM-DD" strings.
const pad = (n) => String(n).padStart(2, '0');
export const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const toIso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const parse = (s) => {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
};
export const today = () => toIso(new Date());
export const addDays = (s, n) => {
  const d = parse(s);
  d.setDate(d.getDate() + n);
  return toIso(d);
};
export const daysBetween = (a, b) => Math.round((parse(b) - parse(a)) / 86_400_000);
export const weekday = (s) => WEEKDAYS[parse(s).getDay()];
export const monthDay = (s) => `${MONTHS[parse(s).getMonth()]} ${parse(s).getDate()}`;
export const shortDate = (s) => `${weekday(s).slice(0, 3)} ${monthDay(s)}`;

export const formatMinutes = (m) => (m >= 60 ? (m % 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m / 60}h`) : `${m}m`);
