import { API_BASE } from "./config.js";

const K = { token: "karya.token", id: "karya.identifier", user: "karya.user" };

const store = {
  get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  del(k) { try { sessionStorage.removeItem(k); } catch { /* storage unavailable */ } },
};

function decodeClaims(token) {
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(part + "=".repeat((4 - (part.length % 4)) % 4)));
  } catch { return {}; }
}

export const session = {
  get token() { return store.get(K.token); },
  get identifier() { return store.get(K.id) || ""; },
  /** Profile from GET /auth/me, cached for the tab so the header never flashes empty. */
  get user() { try { return JSON.parse(store.get(K.user)); } catch { return null; } },
  set user(u) { store.set(K.user, JSON.stringify(u)); },
  get expiresAt() {
    const t = this.token;
    const exp = t ? decodeClaims(t).exp : null;
    return exp ? exp * 1000 : null;
  },
  get valid() {
    if (!this.token) return false;
    const exp = this.expiresAt;
    return !exp || exp > Date.now();
  },
  start(token, identifier) {
    store.set(K.token, token);
    store.set(K.id, identifier);
  },
  clear() { Object.values(K).forEach((k) => store.del(k)); },
};

export function endSession(reason = "expired") {
  session.clear();
  location.replace(`login.html?reason=${reason}`);
}

function friendly(d) {
  if (d.type === "string_too_short" && d.ctx?.min_length) return `Use at least ${d.ctx.min_length} characters.`;
  if (d.type === "string_too_long" && d.ctx?.max_length) return `Use at most ${d.ctx.max_length} characters.`;
  if (d.type === "missing") return "This field is required.";
  if (d.type === "string_pattern_mismatch") return "Enter the six digits from your email.";
  return d.msg || "Check this field.";
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Request failed");
    this.status = status;
    this.detail = detail;
  }
  /** 422 detail[] -> { fieldName: message } */
  get fields() {
    const out = {};
    if (!Array.isArray(this.detail)) return out;
    for (const d of this.detail) {
      const key = d.loc && d.loc[d.loc.length - 1];
      if (key !== undefined && !(key in out)) out[key] = friendly(d);
    }
    return out;
  }
  get offline() { return this.status === 0; }
}

async function request(path, { method = "GET", body, auth = true, signal } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && session.token) headers.Authorization = `Bearer ${session.token}`;
  let res;
  try {
    res = await fetch(API_BASE + path, {
      method, headers, signal,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new ApiError(0, "Network error");
  }
  if (res.status === 401 && auth) {
    endSession("expired");
    throw new ApiError(401, "Session ended");
  }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) throw new ApiError(res.status, data && data.detail !== undefined ? data.detail : res.statusText);
  return data;
}

const qs = (params) => {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") u.set(k, String(v));
  return u.toString();
};

export const api = {
  register: (body) => request("/auth/register", { method: "POST", body, auth: false }),
  login: (body) => request("/auth/login", { method: "POST", body, auth: false }),
  verifyEmail: (body) => request("/auth/verify-email", { method: "POST", body, auth: false }),
  resendOtp: (email) => request("/auth/resend-otp", { method: "POST", body: { email }, auth: false }),
  me: () => request("/auth/me"),
  forgotPassword: (email) => request("/auth/forgot-password", { method: "POST", body: { email }, auth: false }),
  verifyResetOtp: (email, otp) => request("/auth/verify-reset-otp", { method: "POST", body: { email, otp }, auth: false }),
  resetPassword: (reset_token, new_password) => request("/auth/reset-password", { method: "POST", body: { reset_token, new_password }, auth: false }),
  listTodos: (params, signal) => request(`/todos?${qs(params)}`, { signal }),
  createTodo: (body) => request("/todo", { method: "POST", body }),
  patchTodo: (id, body) => request(`/todo/${id}`, { method: "PATCH", body }),
  deleteTodo: (id) => request(`/todo/${id}`, { method: "DELETE" }),
};
