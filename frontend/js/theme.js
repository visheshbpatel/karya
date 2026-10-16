// Theme: "system" (follow the OS), "light" or "dark". The choice is saved in localStorage.
const KEY = "karya.theme";
const root = document.documentElement;

export function getTheme() {
  try { const t = localStorage.getItem(KEY); return t === "light" || t === "dark" ? t : "system"; }
  catch { return "system"; }
}

export function setTheme(t) {
  if (t === "light" || t === "dark") root.setAttribute("data-theme", t);
  else root.removeAttribute("data-theme");
  try { t === "system" ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, t); } catch { /* storage unavailable */ }
  document.dispatchEvent(new CustomEvent("karya:theme", { detail: t }));
}

const ICON = {
  system: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  light: '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>',
  dark: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>',
};
export const themeIcon = (t) => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICON[t]}</svg>`;
export const THEMES = [["system", "System"], ["light", "Light"], ["dark", "Dark"]];

/** Three-way segmented control for pages without the account menu (sign in, register, ...). */
export function mountThemeSwitch(host) {
  host.innerHTML = `<div class="theme-switch" role="radiogroup" aria-label="Theme">${THEMES.map(
    ([v, label]) => `<button type="button" role="radio" data-theme-value="${v}" aria-label="${label}" title="${label}">${themeIcon(v)}</button>`
  ).join("")}</div>`;
  const btns = [...host.querySelectorAll("button")];
  const sync = () => btns.forEach((b) => b.setAttribute("aria-checked", String(b.dataset.themeValue === getTheme())));
  btns.forEach((b, i) => {
    b.addEventListener("click", () => setTheme(b.dataset.themeValue));
    b.addEventListener("keydown", (e) => {
      const d = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      const n = btns[(i + d + btns.length) % btns.length];
      n.focus(); setTheme(n.dataset.themeValue);
    });
  });
  document.addEventListener("karya:theme", sync);
  sync();
  // roving tabindex
  const upd = () => btns.forEach((b) => (b.tabIndex = b.getAttribute("aria-checked") === "true" ? 0 : -1));
  document.addEventListener("karya:theme", upd); upd();
}
