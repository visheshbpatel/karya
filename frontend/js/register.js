import { api, session, ApiError } from "./api.js";
import { recordSend } from "./otp-store.js";
import { $, icons, busy, showBanner, setFieldError, clearAllErrors, bindClearOnInput, bindPasswordToggle, errorMessage } from "./ui.js";

if (session.valid) location.replace("index.html");

const form = $("#form");
const submit = $("#submit");
const bannerEl = $("#banner");
const fields = ["first_name", "last_name", "username", "email", "password"].map((id) => $("#" + id));

$("#toggle").innerHTML = icons.eye;
bindPasswordToggle($("#password"), $("#toggle"));
bindClearOnInput(form);

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(v) {
  const e = {};
  if (!v.first_name) e.first_name = "Enter your first name.";
  if (!v.last_name) e.last_name = "Enter your last name.";
  if (v.username.length < 3) e.username = "Use at least 3 characters.";
  if (!EMAIL.test(v.email) || v.email.length < 5) e.email = "Enter a valid email address.";
  if (v.password.length < 8) e.password = "Use at least 8 characters.";
  return e;
}

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  if (submit.classList.contains("is-loading")) return;
  clearAllErrors(form);
  showBanner(bannerEl, "info", "");

  const v = Object.fromEntries(fields.map((f) => [f.id, f.value.trim()]));
  v.password = $("#password").value;
  const errs = validate(v);
  for (const [k, msg] of Object.entries(errs)) setFieldError($("#" + k), msg);
  if (Object.keys(errs).length) return form.querySelector("[aria-invalid]").focus();

  busy(submit, true, "Creating account…");
  fields.forEach((f) => (f.disabled = true));
  const goVerify = (notice) => {
    recordSend(v.email); // registration counts as the first send and starts the 60 s cooldown
    location.replace(`verify.html?email=${encodeURIComponent(v.email)}${notice ? `&notice=${notice}` : ""}`);
  };
  try {
    await api.register(v);
    goVerify();
  } catch (err) {
    busy(submit, false);
    fields.forEach((f) => (f.disabled = false));
    if (!(err instanceof ApiError)) throw err;
    if (err.status === 409) {
      showBanner(bannerEl, "error", `Username or email already exists. <a href="login.html">Sign in instead</a>`);
    } else if (err.status === 503) {
      goVerify("mail-failed"); // account exists; only the email failed
    } else if (err.status === 422) {
      for (const [k, msg] of Object.entries(err.fields)) if ($("#" + k)) setFieldError($("#" + k), msg);
      form.querySelector("[aria-invalid]")?.focus();
    } else showBanner(bannerEl, "error", errorMessage(err));
  }
});
