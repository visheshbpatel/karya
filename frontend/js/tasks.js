import { api, session, endSession, ApiError } from "./api.js";
import {
  $, $$, esc, icons, toast, busy, showBanner, setFieldError, clearFieldError, bindClearOnInput,
  setupMenu, errorMessage,
} from "./ui.js";

const PAGE = 10;
const SORTS = {
  newest: { sort_by: "id", order: "desc", label: "Newest first" },
  oldest: { sort_by: "id", order: "asc", label: "Oldest first" },
  urgent: { sort_by: "priority", order: "asc", label: "Most urgent first" },
  least: { sort_by: "priority", order: "desc", label: "Least urgent first" },
};
const PRIO_LABEL = { urgent: "Urgent", important: "Important", normal: "Normal" };
const PRIO_BARS = { urgent: "b3", important: "b2", normal: "b1" };

const state = { q: "", status: "all", priority: "", sort: "newest", page: 0, rows: [], hasNext: false, error: false };

/* ---------- dates (the API sends YYYY-MM-DD; compare as local-time strings) ---------- */
const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const today = () => iso(new Date());
const inDays = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return iso(d); };
const fmt = (s) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(y, m - 1, d));
};
const clock = (ms) => new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(ms));

/* ---------- row rendering ---------- */
function metaHtml(t) {
  const parts = [];
  if (t.priority !== "normal") {
    parts.push(`<span class="badge badge-${t.priority}"><span class="bars ${PRIO_BARS[t.priority]}" aria-hidden="true"><i></i><i></i><i></i></span>${PRIO_LABEL[t.priority]}</span>`);
  }
  if (t.due_date) {
    const t0 = today();
    const overdue = !t.completed && t.due_date < t0;
    const isToday = t.due_date === t0 && !t.completed;
    const text = overdue ? `Overdue · ${fmt(t.due_date)}` : t.due_date === t0 ? "Today" : fmt(t.due_date);
    parts.push(`<span class="due${overdue ? " is-overdue" : isToday ? " is-today" : ""}">${icons.calendar}<time datetime="${t.due_date}">${text}</time></span>`);
  }
  return parts.join("");
}

function rowHtml(t) {
  return `<li class="row${t.completed ? " is-done" : ""}" data-id="${t.id}">
    <span class="row-check"><span class="check"><input class="check-input" type="checkbox" ${t.completed ? "checked" : ""} aria-label="${t.completed ? "Mark not done" : "Mark done"}: ${esc(t.task)}"><span class="check-box"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" pathLength="16"/></svg></span></span></span>
    <div class="row-body"><div><span class="row-title">${esc(t.task)}</span></div>${t.description ? `<span class="row-desc">${esc(t.description)}</span>` : ""}</div>
    <div class="row-meta">${metaHtml(t)}</div>
    <div class="row-actions">
      <button class="btn btn-ghost btn-icon" type="button" data-act="edit" aria-label="Edit task: ${esc(t.task)}">${icons.edit}</button>
      <button class="btn btn-ghost btn-icon" type="button" data-act="delete" aria-label="Delete task: ${esc(t.task)}">${icons.trash}</button>
    </div></li>`;
}

const skeletonRow = (a, b) => `<div class="row-skel"><span style="display:grid;place-items:center"><span class="skel" style="width:20px;height:20px;border-radius:50%"></span></span><div style="display:grid;gap:8px"><span class="skel" style="width:${a}%"></span></div><span class="skel" style="width:${b}px"></span></div>`;

function filtersActive() { return !!(state.q.trim() || state.status !== "all" || state.priority); }

function stateBlock(kind) {
  if (kind === "first") {
    return `<div class="list"><div class="empty">
      <svg class="ring-art" viewBox="0 0 88 88" fill="none" aria-hidden="true"><circle cx="44" cy="44" r="36" stroke="var(--line-strong)" stroke-width="2"/><path d="M44 8a36 36 0 1 1-31 18" stroke="var(--accent)" stroke-width="3" stroke-linecap="round"/></svg>
      <h2 class="t-display">A clear desk</h2><p>Add your first task. It will live here until you close the ring.</p>
      <button class="btn btn-primary" type="button" data-empty="new">${icons.plus}New task</button></div></div>`;
  }
  if (kind === "none") {
    return `<div class="list"><div class="empty"><span class="iconring" style="width:48px;height:48px;border-radius:50%;display:grid;place-items:center;background:var(--sunken);color:var(--text-2)">${icons.search}</span>
      <h2 class="t-h2" style="margin-top:8px">Nothing matches</h2><p>No tasks match your search and filters.</p>
      <button class="btn btn-secondary" type="button" data-empty="clear">Clear search and filters</button></div></div>`;
  }
  return `<div class="list"><div class="empty"><span style="width:48px;height:48px;border-radius:50%;display:grid;place-items:center;background:var(--danger-soft);color:var(--danger)">${icons.alert.replace('class="i "', 'class="i i-lg"')}</span>
    <h2 class="t-h2" style="margin-top:8px">Couldn’t load your tasks</h2><p>Check your connection and try again.</p>
    <button class="btn btn-secondary" type="button" data-empty="retry">${icons.refresh}Try again</button></div></div>`;
}

/* ---------- loading ---------- */
let ctrl;
async function load() {
  ctrl?.abort();
  ctrl = new AbortController();
  const mine = ctrl;
  const area = $("#list-area");
  area.setAttribute("aria-busy", "true");
  const timer = setTimeout(() => {
    area.innerHTML = `<div class="list" aria-hidden="true">${[62, 48, 70, 54, 40].map((a, i) => skeletonRow(a, [90, 70, 100, 80, 60][i])).join("")}</div>`;
  }, 250);
  const s = SORTS[state.sort];
  try {
    const data = await api.listTodos({
      skip: state.page * PAGE, limit: PAGE + 1,
      completed: state.status === "open" ? false : state.status === "done" ? true : undefined,
      priority: state.priority || undefined,
      sort_by: s.sort_by, order: s.order,
      search: state.q.trim() || undefined,
    }, mine.signal);
    clearTimeout(timer);
    if (data.length === 0 && state.page > 0) { state.page -= 1; return load(); }
    state.hasNext = data.length > PAGE;
    state.rows = data.slice(0, PAGE);
    state.error = false;
  } catch (e) {
    clearTimeout(timer);
    if (e.name === "AbortError") return;
    state.error = true;
    state.rows = [];
    state.hasNext = false;
  }
  area.removeAttribute("aria-busy");
  render();
}

function render() {
  const area = $("#list-area");
  const pager = $("#pager");
  if (state.error) area.innerHTML = stateBlock("error");
  else if (!state.rows.length) area.innerHTML = stateBlock(filtersActive() ? "none" : "first");
  else area.innerHTML = `<ul class="list" style="margin:0;padding:0;list-style:none">${state.rows.map(rowHtml).join("")}</ul>`;

  const has = state.rows.length > 0;
  pager.hidden = !has && state.page === 0;
  if (has) {
    $("#range").textContent = `Showing ${state.page * PAGE + 1}–${state.page * PAGE + state.rows.length}`;
  } else $("#range").textContent = "";
  $("#prev").disabled = state.page === 0;
  $("#next").disabled = !state.hasNext;
  $("#srStatus").textContent = state.error ? "Couldn’t load tasks." : has ? `${state.rows.length} task${state.rows.length === 1 ? "" : "s"} shown.` : "No tasks shown.";
}

/* ---------- summary (one extra request: open tasks only) ---------- */
async function loadSummary() {
  try {
    const open = await api.listTodos({ completed: false, limit: 200, sort_by: "id", order: "asc" });
    const t0 = today(), week = inDays(6);
    const overdue = open.filter((t) => t.due_date && t.due_date < t0).length;
    const soon = open.filter((t) => t.due_date && t.due_date >= t0 && t.due_date <= week).length;
    const n = open.length >= 200 ? "200+" : String(open.length);
    $("#summary").innerHTML =
      `<span><span class="num">${n}</span> open</span>` +
      `<span><span class="num">${soon}</span> due this week</span>` +
      (overdue ? `<span class="is-overdue">${icons.clock}<span class="num">${overdue}</span> overdue</span>` : "");
  } catch (e) {
    if (e.name !== "AbortError") $("#summary").textContent = "";
  }
}

/* ---------- init ---------- */
function init() {
  const dayFmt = new Intl.DateTimeFormat("en", { weekday: "long" }).format(new Date());
  const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long" }).format(new Date());
  $("#today").innerHTML = `${dayFmt}, <time datetime="${today()}">${dateFmt}</time>`;
  $("#acctName").textContent = session.identifier;
  $("#acId").textContent = session.identifier || "—";

  const exp = session.expiresAt;
  if (exp) setTimeout(() => endSession("expired"), Math.max(0, exp - Date.now()));

  bindToolbar();
  bindList();
  bindDialogs();
  bindAccount();
  bindShortcuts();
  load();
  loadSummary();
}

/* ---------- toolbar: search, sort, filters, pager ---------- */
function bindToolbar() {
  const q = $("#q"), clear = $("#clearQ");
  let t;
  q.addEventListener("input", () => {
    clear.hidden = !q.value;
    clearTimeout(t);
    t = setTimeout(() => { state.q = q.value; state.page = 0; load(); }, 300);
  });
  q.addEventListener("keydown", (e) => { if (e.key === "Escape" && q.value) { e.preventDefault(); clearSearch(); } });
  clear.addEventListener("click", () => { clearSearch(); q.focus(); });
  function clearSearch() { q.value = ""; clear.hidden = true; state.q = ""; state.page = 0; load(); }

  const sortMenu = setupMenu($("#sortBtn"), $("#sortPop"));
  $("#sortPop").addEventListener("click", (e) => {
    const b = e.target.closest("[data-sort]");
    if (!b) return;
    state.sort = b.dataset.sort;
    state.page = 0;
    $$("#sortPop .menu-item").forEach((i) => i.setAttribute("aria-checked", String(i === b)));
    $("#sortLabel").textContent = SORTS[state.sort].label;
    sortMenu.close();
    load();
  });

  $("#statusSeg").addEventListener("change", (e) => { state.status = e.target.value; state.page = 0; load(); });
  $("#prioChips").addEventListener("click", (e) => {
    const b = e.target.closest("[data-prio]");
    if (!b) return;
    state.priority = b.dataset.prio;
    $$("#prioChips .chip").forEach((c) => c.setAttribute("aria-pressed", String(c === b)));
    state.page = 0;
    load();
  });
  $("#prev").addEventListener("click", () => { if (state.page > 0) { state.page -= 1; load(); scrollTop(); } });
  $("#next").addEventListener("click", () => { if (state.hasNext) { state.page += 1; load(); scrollTop(); } });
}
const scrollTop = () => window.scrollTo({ top: 0, behavior: "smooth" });

function resetFilters() {
  state.q = ""; state.status = "all"; state.priority = ""; state.page = 0;
  $("#q").value = ""; $("#clearQ").hidden = true;
  $("input[name=status][value=all]").checked = true;
  $$("#prioChips .chip").forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.prio === "")));
  load();
}

/* ---------- list interactions ---------- */
const byId = (id) => state.rows.find((t) => t.id === Number(id));

function bindList() {
  const area = $("#list-area");
  area.addEventListener("change", (e) => {
    if (!e.target.matches(".check-input")) return;
    const li = e.target.closest(".row");
    toggle(li, e.target.checked);
  });
  area.addEventListener("click", (e) => {
    const empty = e.target.closest("[data-empty]");
    if (empty) {
      if (empty.dataset.empty === "new") openTask();
      if (empty.dataset.empty === "clear") resetFilters();
      if (empty.dataset.empty === "retry") load();
      return;
    }
    const li = e.target.closest(".row");
    if (!li) return;
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "delete") return openDelete(byId(li.dataset.id), e.target.closest("button"));
    if (act === "edit" || e.target.closest(".row-body")) openTask(byId(li.dataset.id), e.target.closest("button") || li.querySelector("[data-act=edit]"));
  });
}

async function toggle(li, checked) {
  const t = byId(li.dataset.id);
  if (!t) return;
  const before = t.completed;
  t.completed = checked;
  li.classList.toggle("is-done", checked);
  li.querySelector(".row-meta").innerHTML = metaHtml(t);
  li.querySelector(".check-input").setAttribute("aria-label", `${checked ? "Mark not done" : "Mark done"}: ${t.task}`);
  try {
    await api.patchTodo(t.id, { completed: checked });
    loadSummary();
    const hidden = (state.status === "open" && checked) || (state.status === "done" && !checked);
    if (hidden) {
      setTimeout(() => {
        li.classList.add("is-collapsing");
        setTimeout(load, 200);
      }, 1200);
    }
  } catch (err) {
    t.completed = before;
    li.classList.toggle("is-done", before);
    li.querySelector(".check-input").checked = before;
    li.querySelector(".row-meta").innerHTML = metaHtml(t);
    toast("Couldn’t update the task", { type: "error", action: "Retry", onAction: () => { li.querySelector(".check-input").checked = checked; toggle(li, checked); } });
  }
}

/* ---------- create / edit dialog ---------- */
let editing = null;       // task being edited, or null for create
let returnFocus = null;

function bindDialogs() {
  const dlg = $("#taskDialog"), form = $("#taskForm");
  bindClearOnInput(form);
  $("#newBtn").addEventListener("click", (e) => openTask(null, e.currentTarget));
  $("#fab").addEventListener("click", (e) => openTask(null, e.currentTarget));
  $("#taskClose").addEventListener("click", () => dlg.close());
  $("#tCancel").addEventListener("click", () => dlg.close());
  dlg.addEventListener("close", () => {
    $$(".row.is-editing").forEach((r) => r.classList.remove("is-editing"));
    (returnFocus && document.contains(returnFocus) ? returnFocus : $("#newBtn")).focus?.();
  });
  dlg.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); form.requestSubmit(); }
  });
  $("#tDelete").addEventListener("click", () => { const t = editing; dlg.close(); returnFocus = null; openDelete(t, $("#newBtn")); });
  form.addEventListener("submit", onSaveTask);

  $("#delCancel").addEventListener("click", () => $("#delDialog").close());
  $("#delConfirm").addEventListener("click", onDelete);
}

function openTask(task = null, trigger = null) {
  editing = task;
  returnFocus = trigger;
  const dlg = $("#taskDialog");
  $("#taskTitle").textContent = task ? "Edit task" : "New task";
  $("#tSave").textContent = task ? "Save changes" : "Create task";
  $("#tDelete").hidden = !task;
  $("#tDoneWrap").hidden = !task;
  showBanner($("#taskBanner"), "info", "");
  [$("#tTitle")].forEach(clearFieldError);
  $("#tTitle").value = task ? task.task : "";
  $("#tDesc").value = task?.description || "";
  $("#tDue").value = task?.due_date || "";
  $("#tDone").checked = !!task?.completed;
  $(`input[name=priority][value=${task ? task.priority : "normal"}]`).checked = true;
  if (task) $(`.row[data-id="${task.id}"]`)?.classList.add("is-editing");
  dlg.showModal();
  $("#tTitle").focus();
  $("#tTitle").select();
}

async function onSaveTask(e) {
  e.preventDefault();
  const save = $("#tSave");
  if (save.classList.contains("is-loading")) return;
  const title = $("#tTitle");
  clearFieldError(title);
  showBanner($("#taskBanner"), "info", "");
  const task = title.value.trim();
  if (!task) { setFieldError(title, "Give the task a title."); return title.focus(); }

  const desc = $("#tDesc").value.trim() || null;
  const due = $("#tDue").value || null;
  const priority = $("input[name=priority]:checked").value;

  busy(save, true, "Saving…");
  try {
    if (!editing) {
      await api.createTodo({ task, priority, description: desc, due_date: due });
      $("#taskDialog").close();
      toast("Task created");
      state.page = 0;
      load();
    } else {
      const patch = {};
      if (task !== editing.task) patch.task = task;
      if (desc !== (editing.description || null)) patch.description = desc;
      if (priority !== editing.priority) patch.priority = priority;
      if (due !== (editing.due_date || null)) patch.due_date = due;
      if ($("#tDone").checked !== editing.completed) patch.completed = $("#tDone").checked;
      if (Object.keys(patch).length) {
        await api.patchTodo(editing.id, patch);
        toast("Task updated");
        load();
      }
      $("#taskDialog").close();
    }
    loadSummary();
  } catch (err) {
    if (!(err instanceof ApiError)) throw err;
    if (err.status === 422 && err.fields.task) { setFieldError(title, err.fields.task); title.focus(); }
    else showBanner($("#taskBanner"), "error", esc(errorMessage(err)));
  } finally {
    busy(save, false);
  }
}

/* ---------- delete ---------- */
let deleting = null;
function openDelete(task, trigger) {
  if (!task) return;
  deleting = task;
  returnFocus = trigger;
  $("#delMsg").innerHTML = `<b style="color:var(--text);font-weight:500">${esc(task.task)}</b> will be removed for good. This can’t be undone.`;
  showBanner($("#delBanner"), "info", "");
  $("#delConfirm").textContent = "Delete task";
  $(`.row[data-id="${task.id}"]`)?.classList.add("is-editing");
  const dlg = $("#delDialog");
  dlg.addEventListener("close", () => $$(".row.is-editing").forEach((r) => r.classList.remove("is-editing")), { once: true });
  dlg.showModal();
  $("#delCancel").focus();
}

async function onDelete() {
  const btn = $("#delConfirm");
  if (btn.classList.contains("is-loading") || !deleting) return;
  const id = deleting.id;
  const li = $(`.row[data-id="${id}"]`);
  busy(btn, true, "Deleting…");
  $("#delCancel").disabled = true;
  try {
    await api.deleteTodo(id);
    $("#delDialog").close();
    li?.classList.add("is-collapsing");
    toast("Task deleted");
    setTimeout(() => { load(); loadSummary(); }, 200);
    returnFocus = $("#newBtn");
    $("#newBtn").focus();
  } catch (err) {
    showBanner($("#delBanner"), "error", err.status === 404 ? "That task no longer exists." : "Couldn’t delete the task. Check your connection and try again.");
    busy(btn, false);
    btn.textContent = "Try again";
    if (err.status === 404) setTimeout(() => { $("#delDialog").close(); load(); loadSummary(); }, 900);
  } finally {
    $("#delCancel").disabled = false;
  }
}

/* ---------- account ---------- */
function bindAccount() {
  const menu = setupMenu($("#acctBtn"), $("#acctPop"));
  const drawer = $("#acctDrawer");
  let t;
  const refresh = () => {
    const exp = session.expiresAt;
    $("#acStart").textContent = session.startedAt ? clock(session.startedAt) : "—";
    if (exp) {
      const min = Math.max(0, Math.round((exp - Date.now()) / 60e3));
      $("#acEnd").textContent = `${clock(exp)} · in ${min} min`;
    } else $("#acEnd").textContent = "—";
  };
  $("#openAccount").addEventListener("click", () => {
    menu.close(false);
    refresh();
    drawer.showModal();
    t = setInterval(refresh, 30000);
  });
  drawer.addEventListener("close", () => { clearInterval(t); $("#acctBtn").focus(); });
  $("#acClose").addEventListener("click", () => drawer.close());
  drawer.addEventListener("click", (e) => { if (e.target === drawer) drawer.close(); });
  const out = () => endSession("signedout");
  $("#signOut").addEventListener("click", out);
  $("#acSignOut").addEventListener("click", out);
}

/* ---------- shortcuts: "/" search, "n" new task (only when not typing) ---------- */
function bindShortcuts() {
  document.addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (document.querySelector("dialog[open]")) return;
    const el = document.activeElement;
    if (el && (el.matches("input, textarea, select") || el.isContentEditable)) return;
    if (e.key === "/") { e.preventDefault(); $("#q").focus(); }
    else if (e.key === "n" || e.key === "N") { e.preventDefault(); openTask(null, $("#newBtn")); }
  });
}

/* ---------- boot ---------- */
if (!session.valid) endSession("expired");
else init();
