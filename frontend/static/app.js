const state = {
  view: "mail",
  emails: [],
  selectedEmail: null,
  todos: [],
  drafts: [],
  attachments: [],
  logs: [],
  activeTab: "mail",
  todoStatusFilter: "all",
  todoPriorityFilter: "all",
};

const $ = (id) => document.getElementById(id);
const ACCOUNT_KEY = "mailAgent.account";
const AUTH_CONSENT_KEY = "mailAgent.authConsent";
const SYNC_COLLAPSED_KEY = "mailAgent.syncCollapsed";

function setStatus(message, kind = "") {
  $("status").textContent = message;
  $("status").className = `status ${kind}`;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json();
  if (!res.ok || data.error) {
    throw new Error(data.error || data.detail || `HTTP ${res.status}`);
  }
  return data;
}

async function refreshAll() {
  const [emails, todos, drafts, attachments, logs] = await Promise.all([
    api("/api/emails"),
    api("/api/todos"),
    api("/api/drafts"),
    api("/api/attachments"),
    api("/api/agent-logs"),
  ]);
  state.emails = emails;
  state.todos = todos;
  state.drafts = drafts;
  state.attachments = attachments;
  state.logs = logs;
  if (state.selectedEmail) {
    const fresh = emails.find((mail) => mail.id === state.selectedEmail.id);
    state.selectedEmail = fresh ? await api(`/api/emails/${fresh.id}`) : null;
  }
  render();
}

function render() {
  renderView();
  renderEmails();
  renderSelectedHeader();
  renderTabs();
  renderPanels();
  renderTodoOverview();
}

function renderView() {
  $("mailView").classList.toggle("active", state.view === "mail");
  $("todoView").classList.toggle("active", state.view === "todo");
  $("mailViewBtn").classList.toggle("active", state.view === "mail");
  $("todoViewBtn").classList.toggle("active", state.view === "todo");
}

function selectedTodos() {
  return state.selectedEmail ? state.todos.filter((todo) => todo.email_id === state.selectedEmail.id) : [];
}

function selectedDrafts() {
  return state.selectedEmail ? state.drafts.filter((draft) => draft.email_id === state.selectedEmail.id) : [];
}

function selectedAttachments() {
  return state.selectedEmail ? state.attachments.filter((att) => att.email_id === state.selectedEmail.id) : [];
}

function selectedLogs() {
  return state.selectedEmail ? state.logs.filter((log) => log.email_id === state.selectedEmail.id) : [];
}

function renderEmails() {
  $("emailCount").textContent = state.emails.length;
  $("emailList").innerHTML =
    state.emails
      .map((mail) => {
        const active = state.selectedEmail?.id === mail.id ? "active" : "";
        const unread = mail.processed_status === "new" ? "unread" : "";
        return `
          <button class="mail-item ${active} ${unread}" onclick="selectEmail(${mail.id})">
            <span class="mail-subject">${escapeHtml(mail.subject)}</span>
            <span class="mail-sender">${escapeHtml(mail.sender || "")}</span>
            <span class="mail-meta">
              <span>${escapeHtml(mail.category || "new")}</span>
              <span>${escapeHtml(mail.priority || "medium")}</span>
              <span>Todo ${mail.todo_count || 0}</span>
              <span>附件 ${mail.attachment_count || 0}</span>
            </span>
          </button>
        `;
      })
      .join("") || `<div class="empty">暂无邮件。请同步邮箱或导入样例。</div>`;
}

async function selectEmail(id) {
  state.selectedEmail = await api(`/api/emails/${id}`);
  state.activeTab = "mail";
  state.view = "mail";
  render();
}

function renderSelectedHeader() {
  const mail = state.selectedEmail;
  $("processBtn").disabled = !mail;
  $("forceTodoBtn").disabled = !mail;
  $("forceDraftBtn").disabled = !mail;
  if (!mail) {
    $("selectedHeader").className = "selected-header empty";
    $("selectedHeader").innerHTML = "请选择左侧邮件。";
    return;
  }
  $("selectedHeader").className = "selected-header";
  $("selectedHeader").innerHTML = `
    <div>
      <h2>${escapeHtml(mail.subject)}</h2>
      <p>发件人：${escapeHtml(mail.sender || "")}</p>
      <p>时间：${escapeHtml(mail.received_at || "")}</p>
    </div>
    <div class="header-tags">
      <span class="tag">${escapeHtml(mail.category || "unprocessed")}</span>
      <span class="tag ${mail.priority || "medium"}">${escapeHtml(mail.priority || "medium")}</span>
      <span class="tag">Todo ${selectedTodos().length}</span>
      <span class="tag">草稿 ${selectedDrafts().length}</span>
    </div>
  `;
}

function renderTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.activeTab);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${state.activeTab}`);
  });
}

function renderPanels() {
  renderMailPanel();
  renderAgentPanel();
  renderDraftPanel();
  renderAttachmentPanel();
  renderLogPanel();
}

function renderMailPanel() {
  const mail = state.selectedEmail;
  if (!mail) {
    $("tab-mail").innerHTML = `<div class="empty">请选择邮件。</div>`;
    return;
  }
  $("tab-mail").innerHTML = `
    <article class="mail-content">
      <div class="source-line">来源邮件 ID：${escapeHtml(mail.message_id || String(mail.id))}</div>
      <div class="mail-body">${escapeHtml(mail.body || "无正文")}</div>
    </article>
  `;
}

function renderAgentPanel() {
  const logs = selectedLogs();
  const triage = logs.find((log) => log.agent_name === "Triage Agent");
  const action = logs.find((log) => log.agent_name === "Action Agent");
  const critic = logs.find((log) => log.agent_name === "Critic Agent");
  const guard = logs.find((log) => log.agent_name === "Persistence Guard");
  $("tab-agent").innerHTML = `
    <div class="agent-steps">
      ${agentStep("0", "Persistence Guard 持久化保护", guard, "重跑 Agent 时只清理待确认的临时结果，保留已确认、已完成和已拒绝的 Todo。")}
      ${agentStep("1", "Triage Agent 分类", triage, "判断邮件类别、优先级、是否需要生成 Todo、回复草稿或附件分析。")}
      ${agentStep("2", "Action Agent 执行", action, "生成结构化 Todo、回复草稿，并结合附件分析结果。")}
      ${agentStep("3", "Critic Agent 审查", critic, "检查模糊时间、缺失字段、置信度和自动化风险。")}
    </div>
  `;
}

function agentStep(index, title, log, emptyText) {
  const output = log ? tryFormatJson(log.output_json) : emptyText;
  const risk = log ? log.risk_level || "low" : "pending";
  return `
    <section class="agent-step">
      <div class="step-index">${index}</div>
      <div>
        <h3>${title}</h3>
        <span class="tag risk-${risk}">${escapeHtml(risk)}</span>
        <pre>${escapeHtml(output)}</pre>
      </div>
    </section>
  `;
}

function renderDraftPanel() {
  const drafts = selectedDrafts();
  const triage = selectedLogs().find((log) => log.agent_name === "Triage Agent");
  $("tab-drafts").innerHTML =
    drafts
      .map(
        (draft) => `
        <article class="draft-card">
          <h3>${escapeHtml(draft.subject)}</h3>
          <div class="source-line">来源：${escapeHtml(draft.email_subject || state.selectedEmail?.subject || "")}</div>
          <textarea id="draft-${draft.id}">${escapeHtml(draft.body)}</textarea>
          ${draft.critic_notes ? `<div class="critic-note">审查：${escapeHtml(draft.critic_notes)}</div>` : ""}
          <div class="task-meta">
            <span>状态：${escapeHtml(draft.status || "draft")}</span>
          </div>
          <div class="actions">
            <button onclick="saveDraft(${draft.id})">保存草稿</button>
            <button class="ghost" onclick="copyDraft(${draft.id})">复制草稿</button>
          </div>
        </article>
      `
      )
      .join("") || emptyDecision(
        "当前邮件没有生成回复草稿。",
        triage,
        "Agent 可能判断它不需要回复。你可以点击右上角“生成草稿”强制创建。"
      );
}

function renderAttachmentPanel() {
  const attachments = selectedAttachments();
  $("tab-attachments").innerHTML =
    attachments
      .map(
        (att) => `
        <article class="attachment-card">
          <h3>${escapeHtml(att.filename)}</h3>
          <div class="source-line">来源：${escapeHtml(att.email_subject || state.selectedEmail?.subject || "")}</div>
          <div class="mail-body">${escapeHtml(att.analysis_summary || "等待运行 Agent 后生成附件分析。")}</div>
        </article>
      `
      )
      .join("") || `<div class="empty">当前邮件没有附件，或尚未运行附件分析。</div>`;
}

function renderLogPanel() {
  const logs = selectedLogs();
  $("tab-logs").innerHTML =
    logs
      .map(
        (log) => `
        <article class="log-card">
          <div class="task-head">
            <h3>${escapeHtml(log.agent_name)}</h3>
            <span class="tag risk-${log.risk_level || "low"}">${escapeHtml(log.risk_level || "low")}</span>
          </div>
          <div class="source-line">${escapeHtml(log.created_at || "")}</div>
          <pre>${escapeHtml(tryFormatJson(log.output_json || ""))}</pre>
        </article>
      `
      )
      .join("") || `<div class="empty">当前邮件还没有 Agent 日志。</div>`;
}

function renderTodoOverview() {
  const filtered = filteredTodos();
  const counts = {
    total: state.todos.length,
    pending: state.todos.filter((todo) => todo.status === "pending").length,
    confirmed: state.todos.filter((todo) => todo.status === "confirmed").length,
    done: state.todos.filter((todo) => todo.status === "done").length,
  };
  $("todoTotal").textContent = counts.total;
  $("todoPending").textContent = counts.pending;
  $("todoConfirmed").textContent = counts.confirmed;
  $("todoDone").textContent = counts.done;
  document.querySelectorAll(".summary-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.status === state.todoStatusFilter);
  });
  $("todoBoard").innerHTML =
    filtered
      .map((todo) => todoCard(todo))
      .join("") || `<div class="empty-decision"><h3>没有符合筛选条件的 Todo。</h3><p>可以点击上方统计卡切换状态，或调整优先级筛选。</p></div>`;
}

function filteredTodos() {
  const priorityRank = { high: 0, medium: 1, low: 2 };
  return [...state.todos]
    .filter((todo) => state.todoStatusFilter === "all" || todo.status === state.todoStatusFilter)
    .filter((todo) => state.todoPriorityFilter === "all" || todo.priority === state.todoPriorityFilter)
    .sort((a, b) => {
      const pa = priorityRank[a.priority] ?? 1;
      const pb = priorityRank[b.priority] ?? 1;
      if (pa !== pb) return pa - pb;
      const da = a.deadline || "9999-99-99";
      const db = b.deadline || "9999-99-99";
      if (da !== db) return da.localeCompare(db);
      return b.id - a.id;
    });
}

function todoCard(todo) {
  return `
    <article class="task-card ${state.selectedEmail?.id === todo.email_id ? "current-source" : ""}">
      <div class="task-head">
        <h3>${escapeHtml(todo.title)}</h3>
        <span class="tag ${todo.priority || "medium"}">${priorityLabel(todo.priority)}</span>
      </div>
      <div class="source-box">
        <strong>来源</strong>
        <p>邮件：${escapeHtml(todo.email_subject || "")}</p>
        <p>发件人：${escapeHtml(todo.email_sender || "")}</p>
        <p>证据：${escapeHtml(todo.evidence || "无证据，建议人工确认")}</p>
      </div>
      <p class="task-desc">${escapeHtml(todo.description || "")}</p>
      <div class="task-meta">
        <span>截止：${escapeHtml(todo.deadline || "待确认")}</span>
        <span>状态：${statusLabel(todo.status)}</span>
        <span>置信度：${Number(todo.confidence || 0).toFixed(2)}</span>
      </div>
      ${todo.critic_notes ? `<div class="critic-note">审查：${escapeHtml(todo.critic_notes)}</div>` : ""}
      <div class="actions">
        <button onclick="patchTodoStatus(${todo.id}, 'confirmed')">确认</button>
        <button class="ghost" onclick="patchTodoStatus(${todo.id}, 'done')">完成</button>
        <button class="ghost" onclick="openTodoEditor(${todo.id})">编辑</button>
        <button class="ghost danger" onclick="patchTodoStatus(${todo.id}, 'rejected')">拒绝</button>
        <button class="ghost danger" onclick="deleteTodo(${todo.id})">删除</button>
      </div>
    </article>
  `;
}

async function importSamples() {
  setStatus("正在导入样例邮件...");
  const data = await api("/api/emails/import-samples", { method: "POST", body: "{}" });
  setStatus(`已导入 ${data.imported} 封样例邮件。`);
  await refreshAll();
}

async function syncMailbox() {
  setStatus("正在连接邮箱，请稍等...");
  rememberAccountIfNeeded();
  const syncDates = selectedSyncDates();
  const body = {
    host: currentImapHost(),
    username: $("imapUser").value.trim(),
    password: $("imapPassword").value,
    limit: Number($("imapLimit").value || 50),
    since_date: syncDates.sinceDate,
    until_date: syncDates.untilDate,
    replace_snapshot: true,
  };
  const data = await api("/api/emails/sync", { method: "POST", body: JSON.stringify(body) });
  const rangeText = formatSyncRange(syncDates);
  const maxRead = data.limit ?? body.limit;
  const serverMatched = data.server_matched ?? data.matched ?? data.imported;
  const capHint = data.imported >= maxRead ? "，已达到最多封数上限" : "";
  if (data.imported === 0) {
    setStatus(`已按${rangeText}刷新邮件列表：本范围内没有邮件。服务器初筛 ${serverMatched} 封，最多读取 ${maxRead} 封。可以改选最近 7 天或最近 30 天再同步。`);
    await refreshAll();
    return;
  } else {
    setStatus(`已按${rangeText}刷新邮件列表：当前显示 ${data.imported} 封，服务器初筛 ${serverMatched} 封，最多读取 ${maxRead} 封${capHint}。Agent 正在自动生成 Todo、草稿和附件分析...`);
  }
  const processResult = await autoProcessSyncedEmails(data.imported);
  await refreshAll();
  setSyncCollapsed(true);
  state.view = "todo";
  setStatus(`同步并自动处理完成：邮件 ${data.imported} 封，Agent 成功处理 ${processResult.processed} 封，失败 ${processResult.failed} 封。Todo 与草稿已汇总到右侧页面。`);
  render();
}

async function autoProcessSyncedEmails(importedCount) {
  const limit = Math.min(Math.max(Number(importedCount || 1), 1), 200);
  return api("/api/emails/process-all", {
    method: "POST",
    body: JSON.stringify({
      only_unprocessed: true,
      limit,
      force_todo: false,
      force_reply: false,
    }),
  });
}

async function processAllEmails() {
  const limit = Number($("processLimit").value || 50);
  const onlyUnprocessed = $("processScope").value !== "all";
  const forceTodo = $("batchForceTodo").checked;
  const scopeText = onlyUnprocessed ? "未处理邮件" : "全部邮件";
  setStatus(`Agent 正在批量处理${scopeText}，最多 ${limit} 封。会逐封分类、生成 Todo/草稿、分析附件并审查风险...`);
  const data = await api("/api/emails/process-all", {
    method: "POST",
    body: JSON.stringify({
      only_unprocessed: onlyUnprocessed,
      limit,
      force_todo: forceTodo,
      force_reply: false,
    }),
  });
  await refreshAll();
  state.view = "todo";
  setStatus(`批量处理完成：请求 ${data.requested} 封，成功 ${data.processed} 封，失败 ${data.failed} 封。Todo 已按优先级排序。`);
  render();
}

async function processSelected() {
  return processSelectedWithOptions({});
}

async function forceTodo() {
  return processSelectedWithOptions({ force_todo: true });
}

async function forceDraft() {
  return processSelectedWithOptions({ force_reply: true });
}

async function processSelectedWithOptions(options) {
  if (!state.selectedEmail) return;
  setStatus("Agent 正在处理：Triage 分类 -> Action 执行 -> Critic 审查...");
  const data = await api(`/api/emails/${state.selectedEmail.id}/process`, {
    method: "POST",
    body: JSON.stringify(options),
  });
  state.selectedEmail = data.email;
  await refreshAll();
  state.selectedEmail = await api(`/api/emails/${data.email_id}`);
  state.activeTab = options.force_reply ? "drafts" : "agent";
  setStatus(`处理完成：分类 ${data.triage.category}，Todo ${data.email.todos.length} 个，草稿 ${data.email.drafts.length} 个，风险 ${data.critic.risk_level}。`);
  render();
}

async function patchTodoStatus(id, status) {
  await api(`/api/todos/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
  await refreshAll();
  setStatus(`Todo 已更新为 ${statusLabel(status)}。`);
}

function openTodoEditor(id) {
  const todo = state.todos.find((item) => item.id === id);
  if (!todo) return;
  $("editTodoId").value = todo.id;
  $("editTodoTitle").value = todo.title || "";
  $("editTodoDescription").value = todo.description || "";
  $("editTodoDeadline").value = todo.deadline || "";
  $("editTodoPriority").value = todo.priority || "medium";
  $("editTodoStatus").value = todo.status || "pending";
  $("editTodoEvidence").value = todo.evidence || "";
  $("todoModal").classList.remove("hidden");
}

function closeTodoEditor() {
  $("todoModal").classList.add("hidden");
}

async function saveTodoEdit(event) {
  event.preventDefault();
  const id = $("editTodoId").value;
  await api(`/api/todos/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      title: $("editTodoTitle").value.trim(),
      description: $("editTodoDescription").value.trim(),
      deadline: $("editTodoDeadline").value.trim(),
      priority: $("editTodoPriority").value,
      status: $("editTodoStatus").value,
      evidence: $("editTodoEvidence").value.trim(),
    }),
  });
  closeTodoEditor();
  await refreshAll();
  setStatus("Todo 已保存。");
}

async function deleteTodo(id) {
  if (!window.confirm("确定要删除这条 Todo 吗？删除后不会在总览中显示。")) return;
  await api(`/api/todos/${id}`, { method: "DELETE" });
  await refreshAll();
  setStatus("Todo 已删除。");
}

async function saveDraft(id) {
  const body = $("draft-" + id).value;
  await api(`/api/drafts/${id}`, { method: "PATCH", body: JSON.stringify({ body, status: "edited" }) });
  await refreshAll();
  setStatus("草稿已保存。");
}

async function copyDraft(id) {
  const body = $("draft-" + id).value;
  await navigator.clipboard.writeText(body);
  setStatus("草稿已复制到剪贴板。");
}

function currentImapHost() {
  const preset = $("imapPreset").value;
  return preset === "custom" ? $("imapHost").value.trim() : preset;
}

function toggleCustomHost() {
  $("customHostLabel").classList.toggle("hidden", $("imapPreset").value !== "custom");
}

function toggleCustomDateRange() {
  $("customDateRange").classList.toggle("hidden", $("syncRange").value !== "custom");
}

function setSyncCollapsed(collapsed) {
  $("syncBox").classList.toggle("collapsed", collapsed);
  $("syncToggleBtn").textContent = collapsed ? "展开" : "收起";
  localStorage.setItem(SYNC_COLLAPSED_KEY, collapsed ? "true" : "false");
}

function toggleSyncBox() {
  setSyncCollapsed(!$("syncBox").classList.contains("collapsed"));
}

function loadSyncCollapsedState() {
  setSyncCollapsed(localStorage.getItem(SYNC_COLLAPSED_KEY) === "true");
}

function toDateInputValue(date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function selectedSyncDates() {
  const range = $("syncRange").value;
  const today = new Date();
  const untilDate = toDateInputValue(today);
  if (range === "custom") {
    return {
      sinceDate: $("syncSinceDate").value || null,
      untilDate: $("syncUntilDate").value || untilDate,
    };
  }
  const days = Number(range || 7);
  const since = new Date(today);
  since.setDate(today.getDate() - Math.max(days - 1, 0));
  return {
    sinceDate: toDateInputValue(since),
    untilDate,
  };
}

function formatSyncRange(dates) {
  if (dates.sinceDate && dates.untilDate) return ` ${dates.sinceDate} 至 ${dates.untilDate} `;
  if (dates.sinceDate) return ` ${dates.sinceDate} 之后 `;
  if (dates.untilDate) return ` ${dates.untilDate} 之前 `;
  return "全部时间";
}

function rememberAccountIfNeeded() {
  if (!$("rememberAccount").checked && !$("rememberAuth").checked) {
    localStorage.removeItem(ACCOUNT_KEY);
    return;
  }
  let password = "";
  if ($("rememberAuth").checked) {
    const hasConsent = localStorage.getItem(AUTH_CONSENT_KEY) === "true";
    if (hasConsent || window.confirm("授权码将明文保存在当前浏览器 localStorage。仅建议在个人电脑演示时保存，是否继续？")) {
      localStorage.setItem(AUTH_CONSENT_KEY, "true");
      password = $("imapPassword").value;
    } else {
      $("rememberAuth").checked = false;
    }
  }
  const payload = {
    preset: $("imapPreset").value,
    customHost: $("imapHost").value.trim(),
    username: $("rememberAccount").checked || $("rememberAuth").checked ? $("imapUser").value.trim() : "",
    password,
    limit: $("imapLimit").value,
    syncRange: $("syncRange").value,
    syncSinceDate: $("syncSinceDate").value,
    syncUntilDate: $("syncUntilDate").value,
    rememberAccount: $("rememberAccount").checked,
    rememberAuth: $("rememberAuth").checked && Boolean(password),
  };
  localStorage.setItem(ACCOUNT_KEY, JSON.stringify(payload));
}

function loadRememberedAccount() {
  const raw = localStorage.getItem(ACCOUNT_KEY);
  if (!raw) return;
  try {
    const payload = JSON.parse(raw);
    $("imapPreset").value = payload.preset || "imap.qq.com";
    $("imapHost").value = payload.customHost || "";
    $("imapUser").value = payload.username || "";
    $("imapPassword").value = payload.password || "";
    $("imapLimit").value = payload.limit || "50";
    $("syncRange").value = payload.syncRange || "7";
    $("syncSinceDate").value = payload.syncSinceDate || "";
    $("syncUntilDate").value = payload.syncUntilDate || "";
    $("rememberAccount").checked = Boolean(payload.rememberAccount);
    $("rememberAuth").checked = Boolean(payload.rememberAuth && payload.password);
    toggleCustomHost();
    toggleCustomDateRange();
  } catch {
    localStorage.removeItem(ACCOUNT_KEY);
  }
}

function clearRememberedAccount() {
  localStorage.removeItem(ACCOUNT_KEY);
  localStorage.removeItem(AUTH_CONSENT_KEY);
  $("imapUser").value = "";
  $("imapPassword").value = "";
  $("rememberAccount").checked = false;
  $("rememberAuth").checked = false;
  setStatus("已清除本机记忆的邮箱账号和授权信息。");
}

function switchView(view) {
  state.view = view;
  render();
}

function priorityLabel(priority) {
  return { high: "高优先级", medium: "中优先级", low: "低优先级" }[priority] || "中优先级";
}

function statusLabel(status) {
  return { pending: "待确认", confirmed: "已确认", done: "已完成", rejected: "已拒绝" }[status] || status || "待确认";
}

function tryFormatJson(value) {
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return String(value ?? "");
  }
}

function emptyDecision(title, triageLog, fallback) {
  let detail = fallback;
  if (triageLog?.output_json) {
    try {
      const triage = JSON.parse(triageLog.output_json);
      detail = `Triage 判断：category=${triage.category || "unknown"}，needs_todo=${Boolean(triage.needs_todo)}，needs_reply=${Boolean(triage.needs_reply)}。${triage.evidence ? "依据：" + triage.evidence : ""}`;
    } catch {
      detail = fallback;
    }
  }
  return `
    <div class="empty-decision">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(detail)}</p>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    state.activeTab = button.dataset.tab;
    renderTabs();
  });
});

$("mailViewBtn").addEventListener("click", () => switchView("mail"));
$("todoViewBtn").addEventListener("click", () => switchView("todo"));
$("imapPreset").addEventListener("change", toggleCustomHost);
$("syncRange").addEventListener("change", toggleCustomDateRange);
$("syncToggleBtn").addEventListener("click", toggleSyncBox);
$("clearAccountBtn").addEventListener("click", clearRememberedAccount);
document.querySelectorAll(".summary-card").forEach((card) => {
  card.addEventListener("click", () => {
    state.todoStatusFilter = card.dataset.status;
    renderTodoOverview();
  });
});
$("todoPriorityFilter").addEventListener("change", (event) => {
  state.todoPriorityFilter = event.target.value;
  renderTodoOverview();
});
$("todoRefreshBtn").addEventListener("click", () => refreshAll().catch((e) => setStatus(e.message, "error")));
$("importBtn").addEventListener("click", () => importSamples().catch((e) => setStatus(e.message, "error")));
$("syncBtn").addEventListener("click", () => syncMailbox().catch((e) => setStatus(e.message, "error")));
$("processAllBtn").addEventListener("click", () => processAllEmails().catch((e) => setStatus(e.message, "error")));
$("refreshBtn").addEventListener("click", () => refreshAll().catch((e) => setStatus(e.message, "error")));
$("processBtn").addEventListener("click", () => processSelected().catch((e) => setStatus(e.message, "error")));
$("forceTodoBtn").addEventListener("click", () => forceTodo().catch((e) => setStatus(e.message, "error")));
$("forceDraftBtn").addEventListener("click", () => forceDraft().catch((e) => setStatus(e.message, "error")));
$("todoEditForm").addEventListener("submit", saveTodoEdit);
$("todoModalClose").addEventListener("click", closeTodoEditor);
$("todoModalCancel").addEventListener("click", closeTodoEditor);
$("todoModal").addEventListener("click", (event) => {
  if (event.target === $("todoModal")) closeTodoEditor();
});

loadRememberedAccount();
loadSyncCollapsedState();
toggleCustomHost();
toggleCustomDateRange();
refreshAll().catch((e) => setStatus(e.message, "error"));

window.selectEmail = selectEmail;
window.patchTodoStatus = patchTodoStatus;
window.openTodoEditor = openTodoEditor;
window.deleteTodo = deleteTodo;
window.saveDraft = saveDraft;
window.copyDraft = copyDraft;
