/* admin.js */

let adminChatHistory = [];

function initAdminDashboard() {
  renderAdminUI();
  initAdminChat();
  setupAdminSuggestionChips();
  loadAdminChatHistory();
  refreshAdminAIStats();
}

function renderAdminUI() {
  renderTelemetry();
  renderOrdersQueue();
  renderHistoryTable();
  renderAdminMap();
  refreshAdminAIStats();
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
              <span>🤖</span> SUGESTÃO DA IA: Rota Otimizada em Lote Detectada
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

// Render 2D Map for Admin
function renderAdminMap() {
  const mapContainer = document.getElementById("admin-live-map-container");
  if (!mapContainer) return;

  const telemetry = getTelemetry();
  const orders = getOrders();
  const activeOrder = orders.find(o => o.id === telemetry.currentOrderId);

  let targetRoom = "SALA A";
  if (activeOrder) {
    targetRoom = activeOrder.destination || "SALA A";
  }

  // 1. Re-render structural HTML only if targetRoom changes or map is missing
  const mapKey = `target_${targetRoom}_active_${!!telemetry.currentOrderId}`;
  const currentRenderedKey = mapContainer.getAttribute("data-rendered-key") || "";

  if (currentRenderedKey !== mapKey || !mapContainer.querySelector(".map-robot")) {
    mapContainer.innerHTML = `
      <div class="map-container" style="height: 180px; margin-top: 0;">
        <div class="map-corridor">
          <div class="map-corridor-label">Corredor Principal</div>
        </div>
        <div class="map-room sala-a ${targetRoom === 'SALA A' && telemetry.currentOrderId ? 'active-target' : ''}">
          <div class="map-room-name">Sala A</div>
        </div>
        <div class="map-room sala-b ${targetRoom === 'SALA B' && telemetry.currentOrderId ? 'active-target' : ''}">
          <div class="map-room-name">Sala B</div>
        </div>
        <div class="map-room sala-c ${targetRoom === 'SALA C' && telemetry.currentOrderId ? 'active-target' : ''}">
          <div class="map-room-name">Sala C</div>
        </div>
        <div class="map-room sala-d ${targetRoom === 'SALA D' && telemetry.currentOrderId ? 'active-target' : ''}">
          <div class="map-room-name">Sala D</div>
        </div>
        <div class="map-dock">Doca Base</div>
        <div class="map-robot" style="left: 50%; top: 90%;" title="Camaro"></div>
      </div>
    `;
    mapContainer.setAttribute("data-rendered-key", mapKey);
  }

  // 2. Direct style updates to avoid flickering
  let robotX = 50;
  let robotY = 90;

  const roomCoordinates = {
    "SALA A": { x: 24, y: 28 },
    "SALA B": { x: 24, y: 72 },
    "SALA C": { x: 76, y: 28 },
    "SALA D": { x: 76, y: 72 }
  };

  const coords = roomCoordinates[targetRoom] || roomCoordinates["SALA A"];

  if (telemetry.currentOrderId) {
    const now = Date.now();
    if (telemetry.status === "preparing") {
      robotX = 50;
      robotY = 90;
    } else if (telemetry.status === "delivering") {
      const prepTime = telemetry.startTime + 3000;
      const duration = telemetry.deliveryEndTime - prepTime;
      const elapsed = now - prepTime;
      const progress = Math.max(0, Math.min(1, elapsed / duration));

      if (progress < 0.7) {
        const t = progress / 0.7;
        robotX = 50;
        robotY = 90 + t * (coords.y - 90);
      } else {
        const t = (progress - 0.7) / 0.3;
        robotX = 50 + t * (coords.x - 50);
        robotY = coords.y;
      }
    } else if (telemetry.status === "returning") {
      const duration = telemetry.returnEndTime - telemetry.deliveryEndTime;
      const elapsed = now - telemetry.deliveryEndTime;
      const progress = Math.max(0, Math.min(1, elapsed / duration));

      if (progress < 0.3) {
        const t = progress / 0.3;
        robotX = coords.x + t * (50 - coords.x);
        robotY = coords.y;
      } else {
        const t = (progress - 0.3) / 0.7;
        robotX = 50;
        robotY = coords.y + t * (90 - coords.y);
      }
    }
  }

  const robotEl = mapContainer.querySelector(".map-robot");
  if (robotEl) {
    robotEl.style.left = `${robotX}%`;
    robotEl.style.top = `${robotY}%`;
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
                const stars = "★".repeat(f.rating) + "☆".repeat(5 - f.rating);
                const ratingColor = f.rating <= 2 ? "var(--status-error)" : "var(--accent-color)";
                const formattedDate = f.created_at ? f.created_at.substring(11, 16) : "--:--";
                return `
                  <tr>
                    <td style="font-family: monospace;">${f.order_id.replace("ord_", "")}</td>
                    <td style="color: ${ratingColor}; letter-spacing: 2px;">${stars}</td>
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
      alert("Erro ao confirmar envio: " + e.message);
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
  if (!confirm("Tem certeza que deseja recusar este pedido?")) return;

  if (typeof apiUpdateOrderStatus === "function") {
    try {
      await apiUpdateOrderStatus(orderId, "canceled");
      renderAdminUI();
    } catch (e) {
      alert("Erro ao recusar pedido: " + e.message);
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
      alert("Erro ao confirmar todos os pedidos: " + e.message);
    }
  } else {
    alert("Operação indisponível em modo offline.");
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
        alert("Rota em lote confirmada! Camaro a caminho das paradas: " + resp.route);
        renderAdminUI();
      }
    } catch (e) {
      alert("Erro ao autorizar rota em lote: " + e.message);
    }
  } else {
    alert("Rota em lote indisponível em modo offline.");
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
      message: "Olá, Operador! 🤖\nEstou pronto para auxiliar na administração das entregas. Pergunte-me pelo status, peça estatísticas, confirme pedidos ou verifique a rota otimizada em lote.",
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
    badgeDiv.innerHTML = `<span>⚡</span> <span>${actionBadge}</span>`;
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

function clearAdminChatHistory() {
  if (confirm("Tem certeza que deseja limpar o histórico do chat?")) {
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
