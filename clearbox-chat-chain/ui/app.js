const state = { conversation: null, branch: null, models: [], busy: false };
const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.message || `Request failed: ${response.status}`);
  return value;
}

function key() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[char]);
}

function localDay() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function selectedRoute() {
  const option = $("#model").selectedOptions[0];
  return { provider: option?.dataset.provider || "echo", model: option?.dataset.model || "echo" };
}

function renderFeed(messages) {
  const feed = $("#feed");
  if (!messages.length) {
    feed.innerHTML = '<div class="empty">This calendar day has no messages yet.</div>';
    return;
  }
  feed.innerHTML = messages.map((message) => {
    const identity = message.identity_display_name || (message.role === "user" ? "Operator" : "Unidentified system");
    const route = message.identity_provider && message.identity_model
      ? `${message.identity_provider} · ${message.identity_model}` : "";
    const continuation = message.model_output_id
      ? `<button class="continue" type="button" data-output="${escapeHtml(message.model_output_id)}">Continue</button>` : "";
    return `<article class="message ${escapeHtml(message.role)}">
      <div class="message-head"><span>${escapeHtml(identity)}${route ? ` · ${escapeHtml(route)}` : ""}</span><time>${escapeHtml(message.created_at)}</time></div>
      <div class="message-body">${escapeHtml(message.content)}</div>${continuation}
    </article>`;
  }).join("");
  feed.scrollTop = feed.scrollHeight;
}

async function loadDays() {
  const conversations = await api("/api/v1/conversations");
  const days = conversations.filter((item) => item.calendar_day);
  $("#day-list").innerHTML = days.map((item) =>
    `<button class="day-link ${state.conversation?.id === item.id ? "active" : ""}" type="button" data-day="${escapeHtml(item.calendar_day)}">${escapeHtml(item.calendar_day)}</button>`
  ).join("");
}

async function openDay(day) {
  const projection = await api(`/api/v1/days/${encodeURIComponent(day)}`, { method: "POST", body: "{}" });
  state.conversation = projection.conversation;
  state.branch = projection.selected_branch;
  $("#day").value = day;
  $("#chat-title").textContent = day;
  renderFeed(state.branch.messages || []);
  await loadDays();
}

async function refresh() {
  if (!state.conversation) return openDay($("#day").value || localDay());
  const projection = await api(`/api/v1/branches/${state.branch.branch.id}`);
  state.branch = projection;
  renderFeed(projection.messages || []);
  $("#connection").textContent = "Connected · Chat-Chain owns the record";
}

async function waitForTurn(turnId) {
  for (let attempt = 0; attempt < 240; attempt += 1) {
    const result = await api(`/api/v1/turns/${turnId}`);
    if (["completed", "failed", "cancelled"].includes(result.turn.status)) return result;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Response is still running");
}

async function send(event) {
  event.preventDefault();
  if (state.busy || !state.conversation) return;
  const content = $("#message").value;
  if (!content.trim()) return;
  state.busy = true;
  $("#send").disabled = true;
  try {
    const route = selectedRoute();
    const accepted = await api(`/api/v1/conversations/${state.conversation.id}/turns`, {
      method: "POST",
      body: JSON.stringify({
        branch_id: state.branch.branch.id,
        content,
        plan: { mode: "single", seats: [route] },
        expected_branch_revision: state.branch.revision,
        idempotency_key: key(),
      }),
    });
    $("#message").value = "";
    await waitForTurn(accepted.turn_id);
    await refresh();
  } catch (error) {
    $("#connection").textContent = error.message;
    $("#connection").classList.add("error");
  } finally {
    state.busy = false;
    $("#send").disabled = false;
  }
}

async function continueFrom(outputId) {
  if (state.busy) return;
  const instruction = $("#message").value.trim() || "Continue from this output without repeating completed material.";
  const route = selectedRoute();
  state.busy = true;
  $("#send").disabled = true;
  try {
    const accepted = await api(`/api/v1/outputs/${encodeURIComponent(outputId)}/continue`, {
      method: "POST",
      body: JSON.stringify({
        additional_instruction: instruction,
        plan: { mode: "single", seats: [route] },
        idempotency_key: key(),
      }),
    });
    state.branch = await api(`/api/v1/branches/${accepted.branch_id}`);
    $("#message").value = "";
    await waitForTurn(accepted.turn_id);
    await refresh();
  } finally {
    state.busy = false;
    $("#send").disabled = false;
  }
}

async function start() {
  $("#day").value = localDay();
  state.models = await api("/api/v1/models");
  $("#model").innerHTML = state.models.map((item) =>
    `<option data-provider="${escapeHtml(item.provider)}" data-model="${escapeHtml(item.model)}">${escapeHtml(item.provider)} · ${escapeHtml(item.model)}</option>`
  ).join("");
  await openDay(localDay());
  $("#connection").textContent = "Connected · Chat-Chain owns the record";
}

$("#composer").addEventListener("submit", send);
$("#open-day").addEventListener("click", () => openDay($("#day").value));
$("#refresh").addEventListener("click", refresh);
$("#day-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-day]");
  if (button) openDay(button.dataset.day);
});
$("#feed").addEventListener("click", (event) => {
  const button = event.target.closest("[data-output]");
  if (button) continueFrom(button.dataset.output);
});

start().catch((error) => {
  $("#connection").textContent = error.message;
  $("#connection").classList.add("error");
});
