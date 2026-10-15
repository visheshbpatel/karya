// Small DOM helpers shared by every page.
const svg = (d, extra = "") =>
  `<svg class="i ${extra}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;

export const icons = {
  check: svg('<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
  okCircle: svg('<circle cx="12" cy="12" r="9"/><path d="M8.5 12.3l2.5 2.5 4.5-5"/>'),
  alert: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5v.5"/>'),
  info: svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>'),
  clock: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  x: svg('<path d="M6 6l12 12M18 6L6 18"/>'),
  edit: svg('<path d="M4 20h4L19 9l-4-4L4 16v4z"/>'),
  trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
  calendar: svg('<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
  refresh: svg('<path d="M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6"/>'),
  search: svg('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>', "i-lg"),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  eye: svg('<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
  eyeOff: svg('<path d="M3 3l18 18M10.6 6.2A9.9 9.9 0 0 1 12 6c6 0 10 6 10 6a17 17 0 0 1-3 3.6M6.5 7.6A17 17 0 0 0 2 12s4 7 10 7c1.5 0 2.9-.4 4.1-1M9.9 9.9a3 3 0 0 0 4.2 4.2"/>'),
};

export const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/* ---------- banners ---------- */
const BANNER_ICON = { error: icons.alert, warn: icons.alert, ok: icons.okCircle, info: icons.info };
export function showBanner(el, type, html) {
  el.innerHTML = html
    ? `<div class="banner banner-${type}" role="${type === "error" ? "alert" : "status"}">${
        type === "warn" && html.includes("clock:") ? icons.clock : BANNER_ICON[type]
      }<div>${html.replace("clock:", "")}</div></div>`
    : "";
}

/* ---------- toasts ---------- */
function region() {
  let r = document.getElementById("toasts");
  if (!r) {
    r = document.createElement("div");
    r.id = "toasts";
    r.className = "toasts";
    document.body.append(r);
  }
  return r;
}
export function toast(message, { type = "ok", action, onAction, duration } = {}) {
  const r = region();
  while (r.children.length >= 3) r.firstElementChild.remove();
  const el = document.createElement("div");
  const err = type === "error";
  el.className = `toast${err ? " toast-err" : ""}`;
  el.setAttribute("role", err ? "alert" : "status");
  el.innerHTML = `${err ? icons.alert : icons.okCircle}<span></span>${
    action ? '<button class="toast-action" type="button"></button>' : ""
  }<button class="toast-x" type="button" aria-label="Dismiss">${icons.x}</button>`;
  el.querySelector("span").textContent = message;
  if (action) {
    const b = el.querySelector(".toast-action");
    b.textContent = action;
    b.addEventListener("click", () => { remove(); onAction && onAction(); });
  }
  const remove = () => { clearTimeout(timer); el.remove(); };
  el.querySelector(".toast-x").addEventListener("click", remove);
  const ms = duration ?? (err ? 8000 : 4000);
  let timer = setTimeout(remove, ms);
  const pause = () => clearTimeout(timer);
  const resume = () => { timer = setTimeout(remove, ms); };
  el.addEventListener("mouseenter", pause);
  el.addEventListener("mouseleave", resume);
  el.addEventListener("focusin", pause);
  el.addEventListener("focusout", resume);
  r.append(el);
  return remove;
}

/* ---------- buttons ---------- */
export function busy(btn, on, label) {
  if (on) {
    btn.dataset.html = btn.innerHTML;
    btn.style.minWidth = `${btn.offsetWidth}px`;
    btn.classList.add("is-loading");
    btn.setAttribute("aria-disabled", "true");
    btn.innerHTML = `<span class="spin"></span>${esc(label)}`;
  } else {
    if (btn.dataset.html !== undefined) btn.innerHTML = btn.dataset.html;
    btn.classList.remove("is-loading");
    btn.removeAttribute("aria-disabled");
    btn.style.minWidth = "";
  }
}

/* ---------- field errors ---------- */
export function setFieldError(input, message) {
  clearFieldError(input);
  input.classList.add("is-error");
  input.setAttribute("aria-invalid", "true");
  const host = input.closest(".field") || input.parentElement;
  const p = document.createElement("p");
  p.className = "err";
  p.id = `${input.id || "f"}-err`;
  p.innerHTML = `${icons.alert}<span></span>`;
  p.querySelector("span").textContent = message;
  host.append(p);
  const prev = input.getAttribute("aria-describedby");
  input.dataset.prevDesc = prev || "";
  input.setAttribute("aria-describedby", [prev, p.id].filter(Boolean).join(" "));
}
export function clearFieldError(input) {
  input.classList.remove("is-error");
  input.removeAttribute("aria-invalid");
  const host = input.closest(".field") || input.parentElement;
  host.querySelector(`#${CSS.escape((input.id || "f") + "-err")}`)?.remove();
  if (input.dataset.prevDesc !== undefined) {
    if (input.dataset.prevDesc) input.setAttribute("aria-describedby", input.dataset.prevDesc);
    else input.removeAttribute("aria-describedby");
    delete input.dataset.prevDesc;
  }
}
export function clearAllErrors(form) {
  $$("[aria-invalid]", form).forEach(clearFieldError);
}
export function bindClearOnInput(form) {
  form.addEventListener("input", (e) => {
    if (e.target.matches("[aria-invalid]")) clearFieldError(e.target);
  });
}

export function bindPasswordToggle(input, btn) {
  btn.addEventListener("click", () => {
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    btn.innerHTML = show ? icons.eyeOff : icons.eye;
  });
}

/* ---------- popover menus ---------- */
export function setupMenu(trigger, pop, { onOpen } = {}) {
  const items = () => $$(".menu-item", pop);
  const open = () => {
    pop.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    onOpen && onOpen();
    (items().find((i) => i.getAttribute("aria-checked") === "true") || items()[0])?.focus();
  };
  const close = (refocus = true) => {
    if (pop.hidden) return;
    pop.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    if (refocus) trigger.focus();
  };
  trigger.addEventListener("click", () => (pop.hidden ? open() : close()));
  trigger.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && pop.hidden) { e.preventDefault(); open(); }
  });
  pop.addEventListener("keydown", (e) => {
    const list = items();
    const i = list.indexOf(document.activeElement);
    if (e.key === "ArrowDown") { e.preventDefault(); list[(i + 1) % list.length].focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); list[(i - 1 + list.length) % list.length].focus(); }
    else if (e.key === "Home") { e.preventDefault(); list[0].focus(); }
    else if (e.key === "End") { e.preventDefault(); list[list.length - 1].focus(); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Tab") close(false);
  });
  document.addEventListener("click", (e) => {
    if (!pop.hidden && !pop.contains(e.target) && !trigger.contains(e.target)) close(false);
  });
  return { open, close };
}

/* ---------- misc ---------- */
export function errorMessage(e) {
  if (e && e.offline) return "Can’t reach Karya. Check your connection and try again.";
  if (e && typeof e.detail === "string") return e.detail;
  return "Something went wrong. Please try again.";
}

export const BRAND_MARK =
  '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-opacity=".18" stroke-width="2"/><path d="M12 3a9 9 0 1 1-8.2 5.3" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"/><path d="M8.5 12.3l2.5 2.5 4.5-5" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
