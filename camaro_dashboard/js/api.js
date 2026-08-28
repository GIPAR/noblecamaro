/**
 * api.js — REST client for Camaro Dashboard backend.
 * All communication with http://localhost:5000/api/...
 */

const API_BASE = "http://localhost:5000/api";

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
