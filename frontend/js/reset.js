import { api, ApiError } from "./api.js";
import {
  COOLDOWN_S, MAX_TRIES, loadOtp, saveOtp, clearOtp, recordSend, cooldownLeft, limitedFor, isExpired, mmss,
} from "./otp-store.js";
import {
  $, $$, esc, icons, busy, showBanner, setFieldError, clearFieldError, bindPasswordToggle, errorMessage,
} from "./ui.js";
import { mountThemeSwitch } from "./theme.js";

mountThemeSwitch($("[data-theme-slot]"));

// Reset codes are tracked under their own key so they never mix with sign-up verification codes.
let email = "";
let resetToken = "";
let mode = "email"; // email | entry | expired | exhausted | verifying | password | done
const ns = () => "reset:" + email;
const TOKEN_MIN = 10; // reset_token lifetime on the server

const el = {
  title: $("#title"), lede: $("#lede"), banner: $("#banner"),
  emailForm: $("#emailForm"), email: $("#email"), emailSubmit: $("#emailSubmit"),
  codeForm: $("#codeForm"), cells: $$("#otp .otp-cell"), cellErr: $("#cellErr"), primary: $("#primary"),
  pwForm: $("#pwForm"), pw: $("#newPw"), pwSubmit: $("#pwSubmit"), toggle: $("#toggle"),
  foot: $("#foot"), limit: $("#limitNote"), resendBtn: $("#resendBtn"), wait: $("#resendWait"), time: $("#resendTime"),
  sr: $("#timerSr"), back: $("#backFoot"),
};
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const code = () => el.cells.map((c) => c.value).join("");

el.toggle.innerHTML = icons.eye;
bindPasswordToggle(el.pw, el.toggle);
el.pw.addEventListener("input", () => clearFieldError(el.pw));
el.email.addEventListener("input", () => clearFieldError(el.email));

/* ---------- steps ---------- */
function showCodeStep() {
  el.title.textContent = "Check your email";
  el.lede.innerHTML = `If an account exists for <b style="color: var(--text); font-weight: 500">${esc(email)}</b>, we sent a six-digit code. It expires in 10 minutes.`;
  el.emailForm.hidden = true;
  el.codeForm.hidden = false;
  el.foot.hidden = false;
  setMode("entry");
  tick();
}

function showPasswordStep() {
  mode = "password";
  showBanner(el.banner, "info", "");
  el.title.textContent = "Choose a new password";
  el.lede.textContent = "Code accepted. Pick a password you don’t use anywhere else.";
  el.codeForm.hidden = true;
  el.foot.hidden = true;
  el.pwForm.hidden = false;
  el.pw.focus();
}

function backToStart(bannerHtml) {
  mode = "email";
  resetToken = "";
  el.title.textContent = "Reset your password";
  el.lede.textContent = "Enter the email you signed up with and we’ll send a code.";
  el.pwForm.hidden = true;
  el.codeForm.hidden = true;
  el.foot.hidden = true;
  el.emailForm.hidden = false;
  el.email.value = email;
  showBanner(el.banner, "warn", bannerHtml);
  el.email.focus();
}

function setMode(next, bannerType, bannerHtml) {
  mode = next;
  showBanner(el.banner, bannerType || "info", bannerHtml || "");
  el.cells.forEach((c) => (c.disabled = next !== "entry"));
  if (next === "entry") {
    el.primary.textContent = "Continue";
    el.primary.classList.remove("is-loading");
    updatePrimary();
  } else if (next === "verifying") {
    busy(el.primary, true, "Checking…");
  } else {
    busy(el.primary, false);
    el.primary.textContent = "Send a new code";
    el.primary.removeAttribute("aria-disabled");
  }
}
function updatePrimary() { if (mode === "entry") el.primary.setAttribute("aria-disabled", String(code().length < 6)); }

/* ---------- timers ---------- */
let tokenAt = 0;
function tick() {
  if (mode === "password" && tokenAt && Date.now() - tokenAt > TOKEN_MIN * 60e3) {
    return backToStart("clock:<b>That reset link timed out.</b> Request a new code to continue.");
  }
  if (el.foot.hidden) return;
  const st = loadOtp(ns());
  const left = cooldownLeft(st);
  const lim = limitedFor(st);
  if (lim > 0) {
    showBanner(el.limit, "warn", `clock:<b>Code limit reached.</b> Try again in about ${lim} minute${lim === 1 ? "" : "s"}.`);
    el.resendBtn.disabled = true;
    el.wait.hidden = true;
  } else {
    showBanner(el.limit, "info", "");
    el.resendBtn.disabled = left > 0;
    el.wait.hidden = left === 0;
    el.time.textContent = mmss(left);
    if ([30, 10, 0].includes(left) && left !== tick.last) el.sr.textContent = left === 0 ? "You can request a new code." : `You can request a new code in ${left} seconds.`;
    tick.last = left;
  }
  if (mode === "entry" && isExpired(st)) setMode("expired", "warn", "clock:<b>This code has expired.</b> Codes last 10 minutes.");
}
setInterval(tick, 1000);

/* ---------- OTP cells ---------- */
function clearCellError() {
  el.cells.forEach((c) => { c.classList.remove("is-error"); c.removeAttribute("aria-invalid"); });
  el.cellErr.innerHTML = "";
}
function setCellError(msg) {
  el.cells.forEach((c) => { c.classList.add("is-error"); c.setAttribute("aria-invalid", "true"); });
  el.cellErr.innerHTML = `<p class="err" role="alert">${icons.alert}<span>${esc(msg)}</span></p>`;
}
function resetCells(focus = true) {
  el.cells.forEach((c) => { c.value = ""; c.classList.remove("is-filled"); });
  clearCellError();
  updatePrimary();
  if (focus) el.cells[0].focus();
}
function fill(digits, start) {
  const d = digits.slice(0, 6 - start);
  [...d].forEach((ch, j) => { el.cells[start + j].value = ch; el.cells[start + j].classList.add("is-filled"); });
  el.cells[Math.min(start + d.length, 5)].focus();
  afterChange();
}
function afterChange() {
  updatePrimary();
  if (code().length === 6 && mode === "entry") submitCode();
}
el.cells.forEach((cell, i) => {
  cell.addEventListener("input", () => {
    clearCellError();
    const v = cell.value.replace(/\D/g, "");
    if (v.length > 1) { cell.value = ""; return fill(v, i); }
    cell.value = v;
    cell.classList.toggle("is-filled", !!v);
    if (v && i < 5) el.cells[i + 1].focus();
    afterChange();
  });
  cell.addEventListener("keydown", (e) => {
    if (e.key === "Backspace" && !cell.value && i > 0) {
      e.preventDefault();
      const p = el.cells[i - 1];
      p.value = ""; p.classList.remove("is-filled"); p.focus();
      updatePrimary();
    } else if (e.key === "ArrowLeft" && i > 0) { e.preventDefault(); el.cells[i - 1].focus(); }
    else if (e.key === "ArrowRight" && i < 5) { e.preventDefault(); el.cells[i + 1].focus(); }
  });
  cell.addEventListener("paste", (e) => {
    e.preventDefault();
    const digits = (e.clipboardData.getData("text") || "").replace(/\D/g, "");
    if (digits) fill(digits, digits.length >= 6 ? 0 : i);
  });
  cell.addEventListener("focus", () => cell.select());
});

/* ---------- actions ---------- */
async function submitCode() {
  if (mode !== "entry" || code().length < 6) return;
  setMode("verifying");
  try {
    const res = await api.verifyResetOtp(email, code());
    resetToken = res.reset_token;
    tokenAt = Date.now();
    clearOtp(ns());
    showPasswordStep();
  } catch (err) {
    if (!(err instanceof ApiError)) throw err;
    const msg = typeof err.detail === "string" ? err.detail : "";
    if (err.status === 400 && /too many attempts/i.test(msg)) return setMode("exhausted", "error", "Too many attempts. Request a new code.");
    if (err.status === 400 || err.status === 422) {
      const st = loadOtp(ns());
      st.attempts = (st.attempts || 0) + 1;
      saveOtp(ns(), st);
      const left = MAX_TRIES - st.attempts;
      if (left <= 0) return setMode("exhausted", "error", "Too many attempts. Request a new code.");
      setMode("entry");
      setCellError(`That code is incorrect or has expired. ${left} ${left === 1 ? "try" : "tries"} left.`);
      el.cells[0].focus();
      el.cells[0].select();
      return;
    }
    setMode("entry");
    showBanner(el.banner, "error", esc(errorMessage(err)));
  }
}

async function sendCode() {
  await api.forgotPassword(email);
  recordSend(ns());
}

async function resend() {
  const st = loadOtp(ns());
  if (cooldownLeft(st) > 0 || limitedFor(st) > 0) return;
  el.resendBtn.disabled = true;
  try {
    await sendCode();
    resetCells(false);
    setMode("entry", "ok", "If your account is eligible, a new code is on its way. Use the newest one.");
    el.cells[0].focus();
  } catch (err) {
    showBanner(el.banner, "error", esc(errorMessage(err)));
  }
  tick();
}
el.resendBtn.addEventListener("click", resend);

el.codeForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (mode === "expired" || mode === "exhausted") {
    const st = loadOtp(ns());
    if (cooldownLeft(st) > 0) return showBanner(el.banner, "warn", `clock:Please wait <span class="num">${mmss(cooldownLeft(st))}</span> before requesting another code.`);
    if (limitedFor(st) > 0) return;
    return resend();
  }
  if (code().length < 6) { setCellError("Enter all six digits."); return el.cells.find((c) => !c.value).focus(); }
  submitCode();
});

el.emailForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (el.emailSubmit.classList.contains("is-loading")) return;
  clearFieldError(el.email);
  const v = el.email.value.trim();
  if (!EMAIL_RE.test(v)) { setFieldError(el.email, "Enter a valid email address."); return el.email.focus(); }
  email = v;
  const st = loadOtp(ns());
  busy(el.emailSubmit, true, "Sending…");
  try {
    if (cooldownLeft(st) === 0 && limitedFor(st) === 0) await sendCode();
    busy(el.emailSubmit, false);
    showCodeStep();
    el.cells[0].focus();
  } catch (err) {
    busy(el.emailSubmit, false);
    if (err instanceof ApiError && err.status === 422) return setFieldError(el.email, "Enter a valid email address.");
    showBanner(el.banner, "error", esc(errorMessage(err)));
  }
});

el.pwForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (el.pwSubmit.classList.contains("is-loading")) return;
  clearFieldError(el.pw);
  if (el.pw.value.length < 8) { setFieldError(el.pw, "Use at least 8 characters."); return el.pw.focus(); }
  busy(el.pwSubmit, true, "Updating…");
  el.pw.disabled = true;
  try {
    await api.resetPassword(resetToken, el.pw.value);
    location.replace(`login.html?reset=1&identifier=${encodeURIComponent(email)}`);
  } catch (err) {
    busy(el.pwSubmit, false);
    el.pw.disabled = false;
    if (!(err instanceof ApiError)) throw err;
    if (err.status === 400) return backToStart("<b>That reset link is no longer valid.</b> Request a new code to continue.");
    if (err.status === 422) return setFieldError(el.pw, err.fields.new_password || "Use 8 to 128 characters.");
    showBanner(el.banner, "error", esc(errorMessage(err)));
    el.pw.focus();
  }
});

const pre = new URLSearchParams(location.search).get("email");
if (pre) el.email.value = pre;
history.replaceState(null, "", "reset.html");
