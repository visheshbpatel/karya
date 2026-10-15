import { api, session, ApiError } from "./api.js";
import { $, icons, busy, showBanner, toast, setFieldError, clearAllErrors, bindClearOnInput, bindPasswordToggle, errorMessage } from "./ui.js";

if (session.valid) location.replace("index.html");

const form = $("#form");
const idEl = $("#identifier");
const pwEl = $("#password");
const submit = $("#submit");
const bannerEl = $("#banner");

$("#toggle").innerHTML = icons.eye;
bindPasswordToggle(pwEl, $("#toggle"));
bindClearOnInput(form);

const params = new URLSearchParams(location.search);
if (params.get("reason") === "expired") {
  showBanner(bannerEl, "info", "clock:<b>Your session ended.</b> Sign in again to pick up where you left off.");
}
if (params.get("verified")) toast("Email verified. Sign in to continue.");
if (params.get("identifier")) idEl.value = params.get("identifier");
history.replaceState(null, "", "login.html");

function setDisabled(on) {
  [idEl, pwEl].forEach((i) => (i.disabled = on));
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (submit.classList.contains("is-loading")) return;
  clearAllErrors(form);
  showBanner(bannerEl, "info", "");

  const identifier = idEl.value.trim();
  const password = pwEl.value;
  if (!identifier) setFieldError(idEl, "Enter your email or username.");
  if (password.length < 8) setFieldError(pwEl, "Use at least 8 characters.");
  const bad = form.querySelector("[aria-invalid]");
  if (bad) return bad.focus();

  busy(submit, true, "Signing in…");
  setDisabled(true);
  try {
    const { access_token } = await api.login({ identifier, password });
    session.start(access_token, identifier);
    location.replace("index.html");
  } catch (err) {
    busy(submit, false);
    setDisabled(false);
    if (!(err instanceof ApiError)) throw err;
    if (err.status === 401) showBanner(bannerEl, "error", "Invalid username/email or password.");
    else if (err.status === 403) {
      const email = identifier.includes("@") ? `?email=${encodeURIComponent(identifier)}` : "";
      showBanner(bannerEl, "warn", `<b>Please verify your email before logging in.</b><br><a href="verify.html${email}">Enter your code</a>`);
    } else if (err.status === 422) {
      const f = err.fields;
      if (f.identifier) setFieldError(idEl, f.identifier);
      if (f.password) setFieldError(pwEl, f.password);
      form.querySelector("[aria-invalid]")?.focus();
    } else showBanner(bannerEl, "error", errorMessage(err));
  }
});
