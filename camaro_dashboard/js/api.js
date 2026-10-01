/**
 * api.js — REST client for Camaro Dashboard backend.
 * All communication goes through the relative path /api/... so the site
 * works from any host (localhost, LAN IP, hostname) that serves it.
 */

const API_BASE = "/api";

// ─── Session ───────────────────────────────────────────────────────────────
function getToken() {
  return localStorage.getItem("camaro_token") || "";
}

function setToken(token) {
  localStorage.setItem("camaro_token", token);
}

function clearToken() {
  localStorage.removeItem("camaro_token");
  localStorage.removeItem("camaro_session");
  localStorage.removeItem("camaro_user");
}

function getApiUser() {
  try {
    return JSON.parse(localStorage.getItem("camaro_user") || "null");
  } catch {
    return null;
  }
}

function setApiUser(user) {
  localStorage.setItem("camaro_user", JSON.stringify(user));
}

// ─── Core fetch wrapper ────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const token = getToken();
  if (token) {
    headers["X-Session-Token"] = token;
  }

  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  try {
    const resp = await fetch(url, {
      ...options,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (resp.status === 401) {
      clearToken();
      // Also clear sessionStorage so the polling loop stops trying
      sessionStorage.removeItem("camaro_current_user");
      // Redirect to login page without hard reload (just re-check auth)
      if (typeof checkAuth === "function") {
        setTimeout(checkAuth, 0);
      }
      return null;
    }

    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
  } catch (err) {
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      throw new Error("Backend offline. Inicie o servidor: cd backend && python3 server.py");
    }
    throw err;
  }
}

// ─── Auth API ──────────────────────────────────────────────────────────────
async function apiLogin(username, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: { username, password },
  });
  if (data) {
    setToken(data.token);
    setApiUser({ username: data.username, name: data.name, role: data.role });
  }
  return data;
}

async function apiLogout() {
  await apiFetch("/auth/logout", { method: "POST" }).catch(() => {});
  clearToken();
}

// ─── Products API ──────────────────────────────────────────────────────────
async function apiGetProducts() {
  return await apiFetch("/products");
}

// ─── Orders API ────────────────────────────────────────────────────────────
async function apiGetOrders(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return await apiFetch(`/orders${qs ? "?" + qs : ""}`);
}

async function apiCreateOrder(items, destination, timing, notes) {
  return await apiFetch("/orders", {
    method: "POST",
    body: { items, destination, timing, notes },
  });
}

async function apiUpdateOrderStatus(orderId, status) {
  return await apiFetch(`/orders/${orderId}/status`, {
    method: "PATCH",
    body: { status },
  });
}

// ─── Telemetry API ─────────────────────────────────────────────────────────
async function apiGetTelemetry() {
  return await apiFetch("/telemetry");
}

async function apiUpdateTelemetry(data) {
  return await apiFetch("/telemetry", {
    method: "PATCH",
    body: data,
  });
}

// ─── Chat API ──────────────────────────────────────────────────────────────
async function apiSendChat(message, sessionId, cart = []) {
  return await apiFetch("/chat", {
    method: "POST",
    body: { message, session_id: sessionId, cart },
  });
}

async function apiGetChatHistory(sessionId, limit = 30) {
  return await apiFetch(`/chat/history?session_id=${sessionId}&limit=${limit}`);
}

// ─── LLM Status ────────────────────────────────────────────────────────────
async function apiGetLLMStatus() {
  return await apiFetch("/llm/status");
}

async function apiGetTrainingStats() {
  return await apiFetch("/llm/training-stats");
}

// ─── Feedback API ──────────────────────────────────────────────────────────
async function apiSubmitFeedback(orderId, rating, comment = "") {
  return await apiFetch(`/orders/${orderId}/feedback`, {
    method: "POST",
    body: { rating, comment },
  });
}

// ─── Robot Status API (ROS2 / Gazebo) ───────────────────────────────────────
async function apiGetRobotStatus() {
  return await apiFetch("/robot/status");
}

// ─── Toasts & confirmações (substitui alert/confirm nativos) ────────────────
function ensureToastContainer() {
  let box = document.getElementById("camaro-toasts");
  if (!box) {
    box = document.createElement("div");
    box.id = "camaro-toasts";
    box.className = "toast-container";
    document.body.appendChild(box);
  }
  return box;
}

function showToast(message, type = "info", ms = 4000) {
  const box = ensureToastContainer();
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  el.onclick = () => el.remove();
  box.appendChild(el);
  setTimeout(() => {
    el.classList.add("toast-out");
    setTimeout(() => el.remove(), 300);
  }, ms);
}

// Diálogo de confirmação não-bloqueante (estilo do site). Resolve true/false.
function confirmDialog(message, okLabel = "Confirmar") {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal-card animate-fade-in" style="max-width: 380px;">
        <div class="modal-body" style="font-size: 14px; line-height: 1.6;">${message}</div>
        <div class="modal-footer flex-between" style="border-top: 1px solid var(--border-color); padding: 12px 20px; background-color: var(--bg-tertiary);">
          <button class="btn" data-act="no" style="padding: 8px 16px;">Cancelar</button>
          <button class="btn btn-primary" data-act="yes" style="padding: 8px 16px;">${okLabel}</button>
        </div>
      </div>`;
    const done = (val) => {
      overlay.remove();
      resolve(val);
    };
    overlay.querySelector('[data-act="yes"]').onclick = () => done(true);
    overlay.querySelector('[data-act="no"]').onclick = () => done(false);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) done(false);
    });
    document.body.appendChild(overlay);
  });
}

// ─── ZED Camera API (via Flask proxy → web_video_server) ────────────────────
async function apiGetCameraStatus() {
  return await apiFetch("/camera/status");
}

function zedStreamUrl(topic) {
  return `/api/camera/stream?topic=${encodeURIComponent(topic)}`;
}

function zedSnapshotUrl(topic) {
  return `/api/camera/snapshot?topic=${encodeURIComponent(topic)}`;
}
