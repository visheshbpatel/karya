import { api, ApiError } from "./api.js";
import {
  COOLDOWN_S, MAX_TRIES, loadOtp, saveOtp, clearOtp, recordSend, cooldownLeft, limitedFor, isExpired, mmss,
} from "./otp-store.js";
import { $, $$, esc, icons, busy, showBanner, setFieldError, clearFieldError, errorMessage } from "./ui.js";

const params = new URLSearchParams(location.search);
let email = (params.get("email") || "").trim();
let mode = "entry"; // entry | expired | exhausted | verifying | success

const el = {
  title: $("#title"), lede: $("#lede"), banner: $("#banner"),
  emailForm: $("#emailForm"), email: $("#email"), emailSubmit: $("#emailSubmit"),
  codeForm: $("#codeForm"), cells: $$("#otp .otp-cell"), cellErr: $("#cellErr"), primary: $("#primary"),
  foot: $("#foot"), limit: $("#limitNote"), resendBtn: $("#resendBtn"), wait: $("#resendWait"), time: $("#resendTime"),
  sr: $("#timerSr"), success: $("#success"), successMsg: $("#successMsg"), toLogin: $("#toLogin"),
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const code = () => el.cells.map((c) => c.value).join("");

/* ---------- screen assembly ---------- */
function showEmailStep() {
  el.title.textContent = "Verify your email";
  el.lede.textContent = "Enter the email you signed up with and we’ll send a code.";
  el.emailForm.hidden = false;
  el.codeForm.hidden = true;
  el.foot.hidden = true;
  el.email.focus();
}

function showCodeStep() {
  el.title.textContent = "Check your email";
  el.lede.innerHTML = `We sent a six-digit code to <b style="color: var(--text); font-weight: 500">${esc(email)}</b>. It expires in 10 minutes.`;
  el.emailForm.hidden = true;
  el.codeForm.hidden = false;
  el.foot.hidden = false;
  setMode("entry");
  tick();
}

function setMode(next, bannerType, bannerHtml) {
  mode = next;
  showBanner(el.banner, bannerType || "info", bannerHtml || "");
  const locked = next !== "entry";
  el.cells.forEach((c) => (c.disabled = locked));
  if (next === "entry") {
    el.primary.textContent = "Verify email";
    el.primary.classList.remove("is-loading");
    updatePrimary();
  } else if (next === "verifying") {
    busy(el.primary, true, "Verifying…");
  } else {
    busy(el.primary, false);
    el.primary.textContent = "Send a new code";
    el.primary.removeAttribute("aria-disabled");
  }
}

function updatePrimary() {
  if (mode !== "entry") return;
  el.primary.setAttribute("aria-disabled", String(code().length < 6));
}

/* ---------- timers ---------- */
function tick() {
  if (el.foot.hidden) return;
  const st = loadOtp(email);
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
  if (mode === "entry" && isExpired(st)) {
    setMode("expired", "warn", "clock:<b>This code has expired.</b> Codes last 10 minutes.");
  }
}
setInterval(tick, 1000);

/* ---------- OTP cells ---------- */
function clearCellError() {
  el.cells.forEach((c) => c.classList.remove("is-error"));
  el.cells.forEach((c) => c.removeAttribute("aria-invalid"));
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
  const otp = code();
  setMode("verifying");
  try {
    await api.verifyEmail({ email, otp });
    return succeed("Your account is ready. Sign in to start.");
  } catch (err) {
    if (!(err instanceof ApiError)) throw err;
    const msg = typeof err.detail === "string" ? err.detail : "";
    if (err.status === 400 && /already verified/i.test(msg)) return succeed("This email is already verified. Sign in to continue.");
    if (err.status === 400 && /too many attempts/i.test(msg)) {
      return setMode("exhausted", "error", "Too many attempts. Request a new code.");
    }
    if (err.status === 400 || err.status === 422) {
      const st = loadOtp(email);
      st.attempts = (st.attempts || 0) + 1;
      saveOtp(email, st);
      const left = MAX_TRIES - st.attempts;
      if (left <= 0) return setMode("exhausted", "error", "Too many attempts. Request a new code.");
      setMode("entry");
      el.cells.forEach((c) => (c.disabled = false));
      setCellError(`That code is incorrect or has expired. ${left} ${left === 1 ? "try" : "tries"} left.`);
      el.cells[0].focus();
      el.cells[0].select();
      return;
    }
    setMode("entry");
    showBanner(el.banner, "error", esc(errorMessage(err)));
  }
}

function succeed(message) {
  mode = "success";
  clearOtp(email);
  el.title.textContent = "Email verified";
  el.lede.textContent = "";
  showBanner(el.banner, "info", "");
  el.codeForm.hidden = true;
  el.emailForm.hidden = true;
  el.foot.hidden = true;
  el.successMsg.textContent = message;
  el.toLogin.href = `login.html?verified=1&identifier=${encodeURIComponent(email)}`;
  el.success.hidden = false;
  el.toLogin.focus();
}

async function resend() {
  const st = loadOtp(email);
  if (cooldownLeft(st) > 0 || limitedFor(st) > 0) return;
  el.resendBtn.disabled = true;
  try {
    await api.resendOtp(email);
    recordSend(email);
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
    if (cooldownLeft(loadOtp(email)) > 0) {
      showBanner(el.banner, "warn", `clock:Please wait <span class="num">${mmss(cooldownLeft(loadOtp(email)))}</span> before requesting another code.`);
      return;
    }
    if (limitedFor(loadOtp(email)) > 0) return;
    return resend();
  }
  if (code().length < 6) {
    setCellError("Enter all six digits.");
    return el.cells.find((c) => !c.value).focus();
  }
  submitCode();
});

el.emailForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (el.emailSubmit.classList.contains("is-loading")) return;
  clearFieldError(el.email);
  const v = el.email.value.trim();
  if (!EMAIL_RE.test(v)) { setFieldError(el.email, "Enter a valid email address."); return el.email.focus(); }
  email = v;
  const st = loadOtp(email);
  busy(el.emailSubmit, true, "Sending…");
  try {
    if (cooldownLeft(st) === 0 && limitedFor(st) === 0) {
      await api.resendOtp(email);
      recordSend(email);
    }
    busy(el.emailSubmit, false);
    showCodeStep();
    showBanner(el.banner, "ok", "If your account is eligible, a code is on its way.");
    el.cells[0].focus();
  } catch (err) {
    busy(el.emailSubmit, false);
    showBanner(el.banner, "error", esc(errorMessage(err)));
  }
});

/* ---------- boot ---------- */
if (!email) showEmailStep();
else {
  showCodeStep();
  if (params.get("notice") === "mail-failed") {
    showBanner(el.banner, "warn", "<b>Account created.</b> The verification email could not be sent. Request a new code in a minute.");
  }
  el.cells[0].focus();
}
history.replaceState(null, "", "verify.html" + (email ? `?email=${encodeURIComponent(email)}` : ""));
