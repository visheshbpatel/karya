// Client-side bookkeeping for verification codes.
// The API gives no signal about cooldowns, expiry or remaining tries, so the client tracks them.
export const COOLDOWN_S = 60;       // matches COOLDOWN_SECONDS on the server
export const MAX_SENDS = 5;         // MAX_OTP_REQUESTS per rolling hour (registration counts as the first)
export const EXPIRY_MIN = 10;       // OTP lifetime
export const MAX_TRIES = 5;         // MAX_OTP_ATTEMPTS per code
const HOUR = 3600e3;

const key = (email) => "karya.otp." + email.trim().toLowerCase();

export function loadOtp(email) {
  try { return JSON.parse(localStorage.getItem(key(email))) || { sends: [], sentAt: null, attempts: 0 }; }
  catch { return { sends: [], sentAt: null, attempts: 0 }; }
}
export function saveOtp(email, s) {
  try { localStorage.setItem(key(email), JSON.stringify(s)); } catch { /* storage unavailable */ }
}
export function clearOtp(email) {
  try { localStorage.removeItem(key(email)); } catch { /* storage unavailable */ }
}
export function recordSend(email) {
  const now = Date.now();
  const s = loadOtp(email);
  s.sends = (s.sends || []).filter((t) => now - t < HOUR);
  s.sends.push(now);
  s.sentAt = now;
  s.attempts = 0;
  saveOtp(email, s);
  return s;
}
export function cooldownLeft(s) {
  if (!s.sentAt) return 0;
  return Math.max(0, Math.ceil(COOLDOWN_S - (Date.now() - s.sentAt) / 1000));
}
export function limitedFor(s) {
  const recent = (s.sends || []).filter((t) => Date.now() - t < HOUR);
  if (recent.length < MAX_SENDS) return 0;
  return Math.max(0, Math.ceil((Math.min(...recent) + HOUR - Date.now()) / 60e3));
}
export function isExpired(s) {
  return !!s.sentAt && Date.now() - s.sentAt > EXPIRY_MIN * 60e3;
}
export function mmss(sec) {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}
