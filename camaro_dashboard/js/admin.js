/* admin.js */

let adminChatHistory = [];

let adminQueuePollingInterval = null;
let adminStatsPollingInterval = null;

function initAdminDashboard() {
  renderAdminUI();
  initAdminChat();
  setupAdminSuggestionChips();
  loadAdminChatHistory();
  refreshAdminAIStats();
  startRobotStatusPolling();
  startAdminQueuePolling();
  startAdminStatsPolling();
}

// Fila + histórico vivos: refresh dedicado a cada 4s (o loop global de 1s
// cuida só de telemetria/HUD; isso evita rebuild da fila a cada segundo)
function startAdminQueuePolling() {
  if (!adminQueuePollingInterval) {
    adminQueuePollingInterval = setInterval(() => {
      if (!document.getElementById("admin-view").classList.contains("active")) return;
      renderOrdersQueue();
      renderHistoryTable();
    }, 4000);
  }
}

// Stats da IA são caras e mudam devagar: a cada 30s basta
function startAdminStatsPolling() {
  if (!adminStatsPollingInterval) {
    adminStatsPollingInterval = setInterval(() => {
      if (!document.getElementById("admin-view").classList.contains("active")) return;
      refreshAdminAIStats();
    }, 30000);
  }
}

function renderAdminUI() {
  renderTelemetry();
  renderOrdersQueue();
  renderHistoryTable();
  renderAdminMap();
}

// Render Telemetry metrics
function renderTelemetry() {
  const telemetry = getTelemetry();
  
  // 1. Battery Gauge & Value
  const batteryLevelEl = document.getElementById("telemetry-battery-level");
  const batteryValueEl = document.getElementById("telemetry-battery-value");
  if (batteryLevelEl && batteryValueEl) {
    const batt = Math.round(telemetry.battery);
    const newText = `${batt}%`;
    if (batteryValueEl.textContent !== newText) {
      batteryValueEl.textContent = newText;
    }
    const newWidth = `${batt}%`;
    if (batteryLevelEl.style.width !== newWidth) {
      batteryLevelEl.style.width = newWidth;
    }
    
    // Color thresholds
    let newClass = "battery-level";
    if (batt <= 20) {
      newClass = "battery-level danger";
    } else if (batt <= 50) {
      newClass = "battery-level warning";
    }
    if (batteryLevelEl.className !== newClass) {
      batteryLevelEl.className = newClass;
    }
  }

  // 2. Status Badge
  const statusBadgeEl = document.getElementById("telemetry-status-badge");
  if (statusBadgeEl) {
    let statusText = "Ocioso";
    let statusColor = "var(--status-idle)";
    
    switch (telemetry.status) {
      case "idle":
        statusText = "Ocioso";
        statusColor = "var(--status-idle)";
        break;
      case "preparing":
        statusText = "Preparando";
        statusColor = "var(--status-preparing)";
        break;
      case "delivering":
        statusText = "Em Entrega";
        statusColor = "var(--status-delivering)";
        break;
      case "returning":
        statusText = "Retornando";
        statusColor = "var(--status-returning)";
        break;
      case "charging":
        statusText = "Recarregando";
        statusColor = "var(--status-preparing)";
        break;
    }
    
    const badgeHTML = `
      <span class="status-dot" style="background-color: ${statusColor}"></span>
      ${statusText}
    `;
    
    if (statusBadgeEl.innerHTML.trim() !== badgeHTML.trim()) {
      statusBadgeEl.innerHTML = badgeHTML;
    }
  }

  // 3. Speed, Distance & ETA
  const speedEl = document.getElementById("telemetry-speed");
  if (speedEl) {
    const newSpeed = `${telemetry.speed.toFixed(1)} km/h`;
    if (speedEl.textContent !== newSpeed) {
      speedEl.textContent = newSpeed;
    }
  }

  const distanceEl = document.getElementById("telemetry-distance");
  if (distanceEl) {
    const newDist = telemetry.status === "idle" || telemetry.status === "charging" ? "0 m" : `${telemetry.distance} m`;
    if (distanceEl.textContent !== newDist) {
      distanceEl.textContent = newDist;
    }
  }

  const etaEl = document.getElementById("telemetry-eta");
  if (etaEl) {
    const newEta = telemetry.status === "idle" || telemetry.status === "charging" ? "--" : `${telemetry.eta} s`;
    if (etaEl.textContent !== newEta) {
      etaEl.textContent = newEta;
    }
  }
}

// Render Incoming Orders Queue & Mission Queue
async function renderOrdersQueue() {
  const ordersListEl = document.getElementById("admin-orders-list");
  if (!ordersListEl) return;

  const orders = getOrders();
  // Filter active client orders (not archived, not delivered/canceled)
  const activeOrders = orders.filter(o => o.status !== "delivered" && o.status !== "canceled" && !o.customerUsername.endsWith("_archived"));

  // Try to fetch queue from API
  let queueList = [];
  try {
    if (typeof apiFetch === "function") {
      const qData = await apiFetch("/queue");
      if (qData && qData.queue) {
        queueList = qData.queue;
      }
    }
  } catch (e) {
    console.warn("Could not fetch queue from server, falling back to local state:", e.message);
  }

  // Proactive batch suggestion card
  const pendingOrders = activeOrders.filter(o => o.status === "pending");
  const suggestionBox = document.getElementById("admin-batch-suggestion-box");
  if (suggestionBox) {
    if (pendingOrders.length >= 2) {
      const dests = pendingOrders.map(o => o.destination);
      const uniqueDests = [...new Set(dests)];
      
      if (uniqueDests.length >= 2) {
        const orderIdsJson = JSON.stringify(pendingOrders.map(o => o.id));
        suggestionBox.style.display = "block";
        suggestionBox.innerHTML = `
          <div style="border-left: 3px solid var(--accent-color); padding-left: 12px; padding-top: 4px; padding-bottom: 4px;">
            <div style="font-weight: 700; font-size: 13px; color: var(--accent-color); display: flex; align-items: center; gap: 6px;">
              SUGESTÃO DA IA: Rota Otimizada em Lote Detectada
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 6px; line-height: 1.4;">
              Há ${pendingOrders.length} pedidos pendentes para destinos diferentes (${uniqueDests.join(", ")}). 
              Você pode enviar todos de uma vez em uma rota em lote otimizada sem retornar à base entre as paradas.
            </div>
            <div style="margin-top: 10px; display: flex; gap: 8px;">
              <button class="btn btn-primary" style="padding: 4px 10px; font-size: 11px;" onclick='confirmBatchRoute(${orderIdsJson})'>
                Autorizar Rota em Lote
              </button>
              <button class="btn" style="padding: 4px 10px; font-size: 11px; background: none; border-color: var(--border-color);" onclick="hideBatchSuggestion()">
                Manter Individual
              </button>
            </div>
          </div>
        `;
      } else {
        suggestionBox.style.display = "none";
      }
    } else {
      suggestionBox.style.display = "none";
    }
  }

  // Preserva a posição de rolagem entre os refreshes automáticos
  const savedScrollTop = ordersListEl.scrollTop;

  if (activeOrders.length === 0 && queueList.length === 0) {
    const emptyHTML = `
      <div class="empty-state">
        <p>Nenhum pedido na fila de processamento.</p>
      </div>
    `;
    if (ordersListEl.innerHTML.trim() !== emptyHTML.trim()) {
      ordersListEl.innerHTML = emptyHTML;
    }
    return;
  }

  const telemetry = getTelemetry();

  const queueHTML = activeOrders.map(o => {
    let statusLabel = "";
    let statusClass = "";
    
    switch (o.status) {
      case "pending":
        statusLabel = "Aguardando";
        statusClass = "badge";
        break;
      case "preparing":
        statusLabel = "Preparando";
        statusClass = "badge";
        break;
      case "delivering":
        statusLabel = "Em Rota";
        statusClass = "badge";
        break;
    }

    const isRobotBusy = telemetry.currentOrderId !== null;
    const canConfirm = o.status === "pending" && !isRobotBusy;

    // Check if this order is in the batch queue
    const queuedMission = queueList.find(m => m.order_id === o.id);
    let queueBadge = "";
    if (queuedMission) {
      const modeLabel = queuedMission.mode === "batch" ? "Lote" : "Individual";
      queueBadge = `<span class="badge" style="background-color: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--accent-color); font-size: 10px; margin-left: 6px;">Fila [${modeLabel}]</span>`;
    }

    return `
      <div class="order-item" style="border-left: 3px solid ${o.status === 'pending' ? 'var(--text-muted)' : 'var(--accent-color)'};">
        <div class="order-item-header">
          <div class="order-info">
            <span class="order-id">${o.id.toUpperCase()}</span>
            <span class="order-customer">Cliente: ${o.customerName}</span>
            ${queueBadge}
          </div>
          <span class="${statusClass}" style="background-color: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-secondary);">${statusLabel}</span>
        </div>
        
        <div class="order-items-details">
          ${o.summaryText || o.productName}
          <br><span style="font-size: 11px; color: var(--text-muted); font-weight: 500;">Local: ${o.destination}</span>
          ${o.timing ? `<br><span style="font-size: 11px; color: var(--accent-color); font-weight: 600;">Tipo: ${o.timing}</span>` : ""}
          ${o.notes ? `<br><span style="font-size: 11px; color: var(--text-muted); font-style: italic;">Obs: "${o.notes}"</span>` : ""}
        </div>
        
        <div class="order-actions">
          ${canConfirm ? `
            <button class="btn btn-primary" onclick="confirmOrder('${o.id}')">Confirmar Envio</button>
          ` : o.status === "pending" && isRobotBusy ? `
            <span class="text-muted" style="font-size:12px; align-self:center;">Camaro ocupado em outra entrega... (Enfileirado)</span>
          ` : `
            <span class="text-accent" style="font-weight:600; font-size:13px; align-self:center;">Camaro ativo no trajeto</span>
          `}
          
          ${o.status === "pending" ? `
            <button class="btn btn-danger" onclick="cancelOrder('${o.id}')">Recusar</button>
          ` : ""}
        </div>
      </div>
    `;
  }).join("");

  if (ordersListEl.innerHTML !== queueHTML) {
    ordersListEl.innerHTML = queueHTML;
    ordersListEl.scrollTop = savedScrollTop;
  }
}

// Render Past Deliveries History Table
function renderHistoryTable() {
  const tableBodyEl = document.getElementById("admin-history-body");
  if (!tableBodyEl) return;

  const telemetry = getTelemetry();
  const history = telemetry.history || [];

  if (history.length === 0) {
    const emptyHTML = `
      <tr>
        <td colspan="5" class="text-center" style="color: var(--text-muted); padding: 24px;">Nenhuma entrega no histórico recente.</td>
      </tr>
    `;
    if (tableBodyEl.innerHTML.trim() !== emptyHTML.trim()) {
      tableBodyEl.innerHTML = emptyHTML;
    }
    return;
  }

  const historyHTML = history.map(h => `
    <tr>
      <td>${h.customer}</td>
      <td>${h.product}</td>
      <td>${h.date}</td>
      <td><span class="badge" style="background-color: rgba(16, 185, 129, 0.1); color: var(--status-delivered); border: 1px solid rgba(16, 185, 129, 0.2);">Sucesso</span></td>
      <td>${h.distance} m</td>
    </tr>
  `).join("");

  if (tableBodyEl.innerHTML !== historyHTML) {
    tableBodyEl.innerHTML = historyHTML;
  }
}

// ─── GAZEBO REAL 2D MAP & ROBOT ODOMETRY STATUS ───────────────────────────

let latestRobotStatus = {
  x: 2.0,
  y: 0.0,
  conectado: false,
  sala_mais_proxima: "SALA A"
};
let robotPollingInterval = null;

// Poll GET /api/robot/status every 1-2 seconds
async function fetchAndUpdateRobotStatus() {
  try {
    let data = null;
    if (typeof apiGetRobotStatus === "function") {
      data = await apiGetRobotStatus();
    } else if (typeof apiFetch === "function") {
      data = await apiFetch("/robot/status");
    } else {
      const resp = await fetch("/api/robot/status");
      if (resp.ok) data = await resp.json();
    }

    if (data && typeof data.x === "number") {
      latestRobotStatus = {
        x: data.x,
        y: data.y,
        conectado: !!data.conectado,
        sala_mais_proxima: data.sala_mais_proxima || "SALA A"
      };
      updateAdminMapElements(latestRobotStatus);
    }
  } catch (err) {
    // Graceful offline display
    const dot = document.getElementById("ros-status-dot");
    const text = document.getElementById("ros-status-text");
    if (dot) dot.style.backgroundColor = "var(--status-error)";
    if (text) {
      text.textContent = "ROS2 Bridge: Backend Offline";
      text.style.color = "var(--status-error)";
    }
  }
}

function startRobotStatusPolling() {
  if (!robotPollingInterval) {
    fetchAndUpdateRobotStatus();
    robotPollingInterval = setInterval(fetchAndUpdateRobotStatus, 1000);
  }
}

// Render dual ZED cameras (RGB + depth) for Admin
function renderAdminMap() {
  const mapContainer = document.getElementById("admin-live-map-container");
  if (!mapContainer) return;

  // Mount structure if not yet present
  if (!document.getElementById("gazebo-map-main-wrapper")) {
    mapContainer.innerHTML = `
      <div id="gazebo-map-main-wrapper" class="gazebo-map-wrapper">
        <!-- Telemetry & Status HUD Header -->
        <div class="map-hud-bar">
          <div class="map-hud-group">
            <div class="map-hud-item">
              <span id="ros-status-dot" class="status-dot" style="background-color: var(--status-idle);"></span>
              <span id="ros-status-text" style="font-weight: 600; color: var(--text-secondary);">ROS2 Bridge: Aguardando</span>
            </div>
            <div class="map-hud-divider"></div>
            <div class="map-hud-item">
              <span style="color: var(--text-muted);">Odometria Real:</span>
              <span id="map-odom-coords" class="map-coord-val">X: 2.00m | Y: 0.00m</span>
            </div>
          </div>
          <div class="map-hud-group">
            <div class="map-hud-item">
              <span style="color: var(--text-muted);">Sala Mais Próxima:</span>
              <span id="map-nearest-room" class="map-nearest-badge">SALA A</span>
            </div>
          </div>
        </div>

        <!-- DUAL CAMERAS (ZED RGB + traseira, lado a lado) -->
        <div class="zed-duo-grid">
          <!-- ZED RGB -->
          <div class="zed-camera-panel">
            <div class="zed-camera-header">
              <div class="flex-align" style="gap: 8px;">
                <span id="zed-rgb-dot" class="status-dot" style="background-color: var(--status-delivering);"></span>
                <span style="font-weight: 700; font-size: 13px;">ZED 2i — RGB</span>
                <span id="zed-rgb-text" style="font-size: 11px; color: var(--text-muted);">verificando…</span>
              </div>
              <div class="flex-align" style="gap: 6px;">
                <button type="button" class="cam-preset-btn" onclick="reloadZedPanel('rgb')" title="Recarregar stream">↻</button>
                <button type="button" class="cam-preset-btn" onclick="snapshotZedPanel('rgb')" title="Tirar foto (salva JPEG)">📷</button>
                <button type="button" class="cam-preset-btn" onclick="openZedPanelNewTab('rgb')" title="Abrir em nova aba">⧉</button>
              </div>
            </div>
            <div class="zed-camera-body">
              <img id="zed-rgb-stream" class="zed-camera-img" alt="Visão RGB da câmera ZED do Camaro" style="display: none;" />
              <div id="zed-rgb-offline" class="zed-camera-offline">
                <div style="font-size: 28px;">📷</div>
                <div style="font-weight: 700; margin-top: 8px;">Câmera RGB offline</div>
                <div id="zed-rgb-hint" style="font-size: 11px; margin-top: 6px; opacity: 0.8;">
                  Suba a simulação: ros2 launch camaro_description gazebo.launch.py
                </div>
              </div>
              <div class="zed-camera-topic-badge">/zed/zed_node/rgb/image_raw</div>
            </div>
          </div>

          <!-- ZED PROFUNDIDADE (colorida via depth_viz_node.py) -->
          <div class="zed-camera-panel">
            <div class="zed-camera-header">
              <div class="flex-align" style="gap: 8px;">
                <span id="zed-depth-dot" class="status-dot" style="background-color: var(--status-delivering);"></span>
                <span style="font-weight: 700; font-size: 13px;">ZED 2i — Profundidade</span>
                <span id="zed-depth-text" style="font-size: 11px; color: var(--text-muted);">verificando…</span>
              </div>
              <div class="flex-align" style="gap: 6px;">
                <button type="button" class="cam-preset-btn" onclick="reloadZedPanel('depth')" title="Recarregar stream">↻</button>
                <button type="button" class="cam-preset-btn" onclick="snapshotZedPanel('depth')" title="Tirar foto (salva JPEG)">📷</button>
                <button type="button" class="cam-preset-btn" onclick="openZedPanelNewTab('depth')" title="Abrir em nova aba">⧉</button>
              </div>
            </div>
            <div class="zed-camera-body">
              <img id="zed-depth-stream" class="zed-camera-img" alt="Mapa de profundidade colorido da ZED do Camaro" style="display: none;" />
              <div id="zed-depth-offline" class="zed-camera-offline">
                <div style="font-size: 28px;">📷</div>
                <div style="font-weight: 700; margin-top: 8px;">Profundidade offline</div>
                <div id="zed-depth-hint" style="font-size: 11px; margin-top: 6px; opacity: 0.8;">
                  Suba a simulação: ros2 launch camaro_description gazebo.launch.py
                </div>
              </div>
              <div class="zed-camera-topic-badge">/zed/zed_node/rgb/depth_image_viz</div>
            </div>
          </div>
        </div>

      </div>
    `;

  }

  // Update HUD + ensure pollings are active
  updateAdminMapElements(latestRobotStatus);
  startRobotStatusPolling();
  initZedDuoPanels();
  startZedDuoPolling();
}

// HUD fino (odometria + sala mais próxima) — sem mapa
function updateAdminMapElements(status) {
  const odomCoords = document.getElementById("map-odom-coords");
  const rosDot = document.getElementById("ros-status-dot");
  const rosText = document.getElementById("ros-status-text");
  const nearestRoomBadge = document.getElementById("map-nearest-room");

  const x = typeof status.x === "number" ? status.x : 2.0;
  const y = typeof status.y === "number" ? status.y : 0.0;
  const isConnected = !!status.conectado;
  const nearestRoom = status.sala_mais_proxima || "SALA A";

  if (odomCoords) {
    odomCoords.textContent = `X: ${x.toFixed(2)}m | Y: ${y.toFixed(2)}m`;
  }

  if (rosDot && rosText) {
    if (isConnected) {
      rosDot.style.backgroundColor = "var(--status-delivered)";
      rosText.textContent = "ROS2 Bridge: Conectado (Odometria Real)";
      rosText.style.color = "var(--status-delivered)";
    } else {
      rosDot.style.backgroundColor = "var(--status-delivering)";
      rosText.textContent = "ROS2 Bridge: Aguardando Conexão";
      rosText.style.color = "var(--text-secondary)";
    }
  }

  if (nearestRoomBadge) {
    nearestRoomBadge.textContent = nearestRoom;
  }
}

// ─── DUAL CAMERAS (ZED RGB + traseira, via Flask proxy) ──────────────────────
// Streams MJPEG em <img>: /api/camera/stream?topic=<topico>
// Status: GET /api/camera/status → { online, ... }

const ZED_PANELS = [
  { key: "rgb", topic: "/zed/zed_node/rgb/image_raw" },
  { key: "depth", topic: "/zed/zed_node/rgb/depth_image_viz" },
];
let zedDuoInitialized = false;
let zedDuoPollingInterval = null;

function zedPanelStreamUrl(topic) {
  if (typeof zedStreamUrl === "function") return zedStreamUrl(topic);
  return `/api/camera/stream?topic=${encodeURIComponent(topic)}`;
}

function initZedDuoPanels() {
  if (zedDuoInitialized) return;
  // Só marca como inicializado se o DOM do grid existir
  if (!document.getElementById("zed-rgb-stream")) return;
  zedDuoInitialized = true;

  ZED_PANELS.forEach(({ key }) => {
    const img = document.getElementById(`zed-${key}-stream`);
    if (!img) return;
    img.onload = () => {
      img.style.display = "block";
      const off = document.getElementById(`zed-${key}-offline`);
      if (off) off.style.display = "none";
    };
    img.onerror = () => {
      // Mantém o último frame visível por 3s antes de mostrar o placeholder,
      // evitando flicker a cada reconexão do MJPEG.
      setTimeout(() => {
        if (img.naturalWidth === 0) {
          img.style.display = "none";
          const off = document.getElementById(`zed-${key}-offline`);
          if (off) off.style.display = "flex";
        }
      }, 3000);
    };
  });

  refreshZedDuoStatus();
}

function startZedDuoPolling() {
  if (!zedDuoPollingInterval) {
    zedDuoPollingInterval = setInterval(refreshZedDuoStatus, 5000);
  }
}

async function refreshZedDuoStatus() {
  const probe = document.getElementById("zed-rgb-dot");
  if (!probe) return;

  let data = null;
  try {
    if (typeof apiGetCameraStatus === "function") {
      data = await apiGetCameraStatus();
    } else if (typeof apiFetch === "function") {
      data = await apiFetch("/camera/status");
    } else {
      const resp = await fetch("/api/camera/status");
      if (resp.ok) data = await resp.json();
    }
    if (!data) throw new Error("sem resposta");
  } catch (err) {
    ZED_PANELS.forEach(({ key }) => {
      const dot = document.getElementById(`zed-${key}-dot`);
      const text = document.getElementById(`zed-${key}-text`);
      if (dot) dot.style.backgroundColor = "var(--status-error)";
      if (text) {
        text.textContent = "Backend offline";
        text.style.color = "var(--status-error)";
      }
    });
    return;
  }

  ZED_PANELS.forEach(({ key, topic }) => {
    const dot = document.getElementById(`zed-${key}-dot`);
    const text = document.getElementById(`zed-${key}-text`);
    const img = document.getElementById(`zed-${key}-stream`);
    const hint = document.getElementById(`zed-${key}-hint`);
    if (!dot || !img) return;

    if (data.online) {
      dot.style.backgroundColor = "var(--status-delivered)";
      if (text) {
        text.textContent = "AO VIVO";
        text.style.color = "var(--status-delivered)";
      }
      const expected = zedPanelStreamUrl(topic);
      // Só troca o src se o tópico mudou (evita restart do MJPEG a cada poll)
      if (!img.getAttribute("src") || !img.getAttribute("src").includes(encodeURIComponent(topic))) {
        img.setAttribute("src", expected + "&t=" + Date.now());
      }
      if (hint && data.hint_offline) hint.textContent = "";
    } else {
      dot.style.backgroundColor = "var(--status-error)";
      if (text) {
        text.textContent = "OFFLINE — simulação parada";
        text.style.color = "var(--status-error)";
      }
      if (hint) hint.textContent = data.hint_offline || "Suba a simulação: ros2 launch camaro_description gazebo.launch.py";
      if (!img.getAttribute("src")) {
        img.style.display = "none";
        const off = document.getElementById(`zed-${key}-offline`);
        if (off) off.style.display = "flex";
      }
    }
  });
}

function reloadZedPanel(key) {
  const panel = ZED_PANELS.find(p => p.key === key);
  if (!panel) return;
  const img = document.getElementById(`zed-${key}-stream`);
  if (img) {
    img.setAttribute("src", zedPanelStreamUrl(panel.topic) + "&t=" + Date.now());
    img.style.display = "block";
    const off = document.getElementById(`zed-${key}-offline`);
    if (off) off.style.display = "none";
  }
}

function openZedPanelNewTab(key) {
  const panel = ZED_PANELS.find(p => p.key === key);
  if (!panel) return;
  window.open(zedPanelStreamUrl(panel.topic), "_blank");
}

// Baixa o frame atual da câmera como JPEG (via /api/camera/snapshot)
async function snapshotZedPanel(key) {
  const panel = ZED_PANELS.find(p => p.key === key);
  if (!panel) return;
  try {
    const url = (typeof zedSnapshotUrl === "function"
      ? zedSnapshotUrl(panel.topic)
      : `/api/camera/snapshot?topic=${encodeURIComponent(panel.topic)}`);
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `camaro-${key}-${new Date().toISOString().replace(/[:.]/g, "-")}.jpg`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  } catch (e) {
    showToast("Não foi possível capturar a foto: " + e.message, "error");
  }
}

// Refresh continuous learning stats from Flask API
async function refreshAdminAIStats() {
  const totalMsgsEl = document.getElementById("ai-stats-messages");
  const ratingEl = document.getElementById("ai-stats-rating");
  const totalFeedbackEl = document.getElementById("ai-stats-total-feedback");
  const aiStatsModeEl = document.getElementById("ai-stats-mode");
  const patternsTbody = document.getElementById("ai-patterns-tbody");
  const feedbackTbody = document.getElementById("ai-feedback-tbody");

  if (!totalMsgsEl) return;

  try {
    if (typeof apiGetTrainingStats === "function" && typeof apiGetLLMStatus === "function") {
      const stats = await apiGetTrainingStats();
      const status = await apiGetLLMStatus();

      if (stats) {
        totalMsgsEl.textContent = stats.total_messages || 0;
        
        // Populate feedback stats
        if (stats.feedback) {
          if (ratingEl) {
            const avg = stats.feedback.avg_rating || 0;
            ratingEl.textContent = `${avg.toFixed(1)} / 5`;
          }
          if (totalFeedbackEl) {
            totalFeedbackEl.textContent = stats.feedback.total || 0;
          }
          
          if (feedbackTbody && stats.feedback.recent) {
            if (stats.feedback.recent.length === 0) {
              feedbackTbody.innerHTML = `<tr><td colspan="4" class="text-center" style="color: var(--text-muted);">Nenhuma avaliação recebida ainda.</td></tr>`;
            } else {
              feedbackTbody.innerHTML = stats.feedback.recent.map(f => {
                const stars = `${f.rating} / 5`;
                const ratingColor = f.rating <= 2 ? "var(--status-error)" : "var(--accent-color)";
                const formattedDate = f.created_at ? f.created_at.substring(11, 16) : "--:--";
                return `
                  <tr>
                    <td style="font-family: monospace;">${f.order_id.replace("ord_", "")}</td>
                    <td style="color: ${ratingColor}; font-weight: 700;">${stars}</td>
                    <td style="max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${f.comment || ''}">${f.comment || '<span class="text-muted">Sem comentário</span>'}</td>
                    <td>${formattedDate}</td>
                  </tr>
                `;
              }).join("");
            }
          }
        }
        
        if (stats.top_patterns && Array.isArray(stats.top_patterns)) {
          if (stats.top_patterns.length === 0) {
            patternsTbody.innerHTML = `<tr><td colspan="3" class="text-center" style="color: var(--text-muted);">Nenhum comando aprendido ainda.</td></tr>`;
          } else {
            patternsTbody.innerHTML = stats.top_patterns.map(p => `
              <tr>
                <td style="font-family: monospace; color: var(--accent-color);">${p.query_norm}</td>
                <td>${p.action_type}${p.product_id ? ' (' + p.product_id + ')' : ''}</td>
                <td style="font-weight: 700; text-align: center;">${p.frequency}x</td>
              </tr>
            `).join("");
          }
        }
      }

      if (status) {
        aiStatsModeEl.textContent = status.mode === "gemini" ? "Gemini AI" : "Fallback Rules";
        aiStatsModeEl.style.color = status.mode === "gemini" ? "var(--accent-color)" : "var(--text-secondary)";
      }
    }
  } catch (e) {
    console.warn("Failed to refresh AI stats:", e.message);
  }
}

// Confirm single order
async function confirmOrder(orderId) {
  if (typeof apiUpdateOrderStatus === "function") {
    try {
      await apiUpdateOrderStatus(orderId, "preparing");
      renderAdminUI();
    } catch (e) {
      showToast("Erro ao confirmar envio: " + e.message, "error");
    }
  } else {
    // Pure local fallback
    const orders = getOrders();
    const order = orders.find(o => o.id === orderId);
    if (!order) return;
    order.status = "preparing";
    saveOrders(orders);
    
    const telemetry = getTelemetry();
    const now = Date.now();
    telemetry.status = "preparing";
    telemetry.currentOrderId = order.id;
    telemetry.startTime = now;
    telemetry.deliveryEndTime = now + 15000;
    telemetry.returnEndTime = now + 25000;
    telemetry.speed = 0;
    telemetry.distance = 450;
    telemetry.eta = 15;
    saveTelemetry(telemetry);
    renderAdminUI();
  }
}

// Reject order
async function cancelOrder(orderId) {
  if (!(await confirmDialog("Tem certeza que deseja recusar este pedido?", "Recusar"))) return;

  if (typeof apiUpdateOrderStatus === "function") {
    try {
      await apiUpdateOrderStatus(orderId, "canceled");
      renderAdminUI();
    } catch (e) {
      showToast("Erro ao recusar pedido: " + e.message, "error");
    }
  } else {
    const orders = getOrders();
    const order = orders.find(o => o.id === orderId);
    if (order) {
      order.status = "canceled";
      saveOrders(orders);
    }
    renderAdminUI();
  }
}

// Confirm All Orders in individual mode
async function confirmAllOrders() {
  if (typeof apiFetch === "function") {
    try {
      const resp = await apiFetch("/queue/confirm-all", { method: "POST" });
      if (resp) {
        renderAdminUI();
      }
    } catch (e) {
      showToast("Erro ao confirmar todos os pedidos: " + e.message, "error");
    }
  } else {
    showToast("Operação indisponível em modo offline.", "error");
  }
}

// Confirm Batch Route (Lote)
async function confirmBatchRoute(orderIds) {
  if (typeof apiFetch === "function") {
    try {
      const resp = await apiFetch("/queue/batch-confirm", {
        method: "POST",
        body: { order_ids: orderIds }
      });
      if (resp) {
        showToast("Rota em lote confirmada! Camaro a caminho das paradas: " + resp.route, "success");
        renderAdminUI();
      }
    } catch (e) {
      showToast("Erro ao autorizar rota em lote: " + e.message, "error");
    }
  } else {
    showToast("Rota em lote indisponível em modo offline.", "error");
  }
}

function hideBatchSuggestion() {
  const suggestionBox = document.getElementById("admin-batch-suggestion-box");
  if (suggestionBox) {
    suggestionBox.style.display = "none";
  }
}

// ─── ADMIN CHATBOT ─────────────────────────────────────────────────────────

function getAdminChatStorageKey() {
  return "camaro_admin_chat_history";
}

function loadAdminChatHistory() {
  const chatMessages = document.getElementById("admin-chat-messages");
  if (!chatMessages) return;

  chatMessages.innerHTML = "";
  const key = getAdminChatStorageKey();
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem(key)) || [];
  } catch (e) {
    history = [];
  }

  if (history.length === 0) {
    const defaultMsg = {
      message: "Olá, Operador!\nEstou pronto para auxiliar na administração das entregas. Pergunte-me pelo status, peça estatísticas, confirme pedidos ou verifique a rota otimizada em lote.",
      sender: "bot",
      actionBadge: null
    };
    renderAdminChatMessageElement(defaultMsg.message, defaultMsg.sender, defaultMsg.actionBadge);
    localStorage.setItem(key, JSON.stringify([defaultMsg]));
  } else {
    history.forEach(item => {
      renderAdminChatMessageElement(item.message, item.sender, item.actionBadge);
    });
  }
}

function renderAdminChatMessageElement(message, sender = "bot", actionBadge = null) {
  const chatMessages = document.getElementById("admin-chat-messages");
  if (!chatMessages) return;

  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg ${sender} animate-fade-in`;
  msgDiv.style.whiteSpace = "pre-line";

  if (actionBadge) {
    const badgeDiv = document.createElement("div");
    badgeDiv.style.cssText = "font-size: 11px; font-weight: 700; color: var(--accent-color); margin-bottom: 6px; display: flex; align-items: center; gap: 4px; text-transform: uppercase; letter-spacing: 0.05em;";
    badgeDiv.innerHTML = `<span>[${actionBadge}]</span>`;
    msgDiv.appendChild(badgeDiv);
  }

  const textNode = document.createElement("div");
  textNode.textContent = message;
  msgDiv.appendChild(textNode);

  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendAdminChatMessage(message, sender = "bot", actionBadge = null) {
  const key = getAdminChatStorageKey();
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem(key)) || [];
  } catch (e) {
    history = [];
  }

  const newMsg = { message, sender, actionBadge };
  history.push(newMsg);
  localStorage.setItem(key, JSON.stringify(history));

  renderAdminChatMessageElement(message, sender, actionBadge);
}

async function clearAdminChatHistory() {
  if (await confirmDialog("Tem certeza que deseja limpar o histórico do chat?", "Limpar")) {
    const key = getAdminChatStorageKey();
    localStorage.removeItem(key);
    loadAdminChatHistory();
  }
}

function initAdminChat() {
  const sendBtn = document.getElementById("admin-chat-send-btn");
  const chatInput = document.getElementById("admin-chat-input");
  const clearBtn = document.getElementById("btn-clear-admin-chat");

  if (sendBtn && chatInput) {
    const handleSend = async () => {
      const messageText = chatInput.value.trim();
      if (!messageText) return;

      chatInput.value = "";
      appendAdminChatMessage(messageText, "user");

      try {
        if (typeof apiSendChat === "function") {
          const res = await apiSendChat(messageText, "admin_session", []);
          if (res) {
            let actionBadge = null;
            if (res.actions && res.actions.length > 0) {
              actionBadge = res.actions.map(a => a.type).join(", ");
            }
            appendAdminChatMessage(res.text, "bot", actionBadge);
            
            if (res.actions) {
              res.actions.forEach(executeAdminChatAction);
            }
          }
        }
      } catch (e) {
        appendAdminChatMessage("Erro ao conectar ao servidor do Camaro. Verifique se o backend está ativo.", "bot");
      }
    };

    sendBtn.onclick = handleSend;
    chatInput.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSend();
      }
    };
  }

  if (clearBtn) {
    clearBtn.onclick = clearAdminChatHistory;
  }
}

function executeAdminChatAction(action) {
  console.log("Admin AI executed action:", action);
  
  if (action.type === "confirm_all") {
    renderAdminUI();
  } else if (action.type === "batch_route") {
    renderAdminUI();
  }
}

function setupAdminSuggestionChips() {
  const container = document.getElementById("admin-chat-suggestions");
  if (!container) return;

  const chips = container.querySelectorAll(".chat-chip");
  chips.forEach(chip => {
    chip.onclick = () => {
      const cmd = chip.dataset.cmd;
      const input = document.getElementById("admin-chat-input");
      if (input) {
        input.value = cmd;
        const sendBtn = document.getElementById("admin-chat-send-btn");
        if (sendBtn) sendBtn.click();
      }
    };
  });
}
