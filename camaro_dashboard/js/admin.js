/* admin.js */

function initAdminDashboard() {
  renderAdminUI();
}

function renderAdminUI() {
  renderTelemetry();
  renderOrdersQueue();
  renderHistoryTable();
}

// Render Telemetry metrics
function renderTelemetry() {
  const telemetry = getTelemetry();
  
  // 1. Battery Gauge & Value
  const batteryLevelEl = document.getElementById("telemetry-battery-level");
  const batteryValueEl = document.getElementById("telemetry-battery-value");
  if (batteryLevelEl && batteryValueEl) {
    const batt = Math.round(telemetry.battery);
    batteryValueEl.textContent = `${batt}%`;
    batteryLevelEl.style.width = `${batt}%`;
    
    // Color thresholds
    batteryLevelEl.className = "battery-level";
    if (batt <= 20) {
      batteryLevelEl.classList.add("danger");
    } else if (batt <= 50) {
      batteryLevelEl.classList.add("warning");
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
    speedEl.textContent = `${telemetry.speed.toFixed(1)} km/h`;
  }

  const distanceEl = document.getElementById("telemetry-distance");
  if (distanceEl) {
    distanceEl.textContent = telemetry.status === "idle" || telemetry.status === "charging" ? "0 m" : `${telemetry.distance} m`;
  }

  const etaEl = document.getElementById("telemetry-eta");
  if (etaEl) {
    etaEl.textContent = telemetry.status === "idle" || telemetry.status === "charging" ? "--" : `${telemetry.eta} s`;
  }
}

// Render Incoming Orders Queue
function renderOrdersQueue() {
  const ordersListEl = document.getElementById("admin-orders-list");
  if (!ordersListEl) return;

  const orders = getOrders();
  // Filter active client orders (not archived, not delivered/canceled)
  const activeOrders = orders.filter(o => o.status !== "delivered" && o.status !== "canceled" && !o.customerUsername.endsWith("_archived"));

  if (activeOrders.length === 0) {
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
        statusLabel = "Aguardando confirmação";
        statusClass = "badge";
        break;
      case "preparing":
        statusLabel = "Preparando envio";
        statusClass = "badge";
        break;
      case "delivering":
        statusLabel = "Em rota de entrega";
        statusClass = "badge";
        break;
    }

    const isRobotBusy = telemetry.currentOrderId !== null;
    const canConfirm = o.status === "pending" && !isRobotBusy;

    return `
      <div class="order-item">
        <div class="order-item-header">
          <div class="order-info">
            <span class="order-id">${o.id.toUpperCase()}</span>
            <span class="order-customer">Cliente: ${o.customerName}</span>
          </div>
          <span class="${statusClass}" style="background-color: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-secondary);">${statusLabel}</span>
        </div>
        
        <div class="order-items-details">
          ${o.summaryText || o.productName}
          ${o.timing ? `<br><span style="font-size: 11px; color: var(--accent-color); font-weight: 600;">Tipo: ${o.timing}</span>` : ""}
          ${o.notes ? `<br><span style="font-size: 11px; color: var(--text-muted); font-style: italic;">Obs: "${o.notes}"</span>` : ""}
        </div>
        
        <div class="order-actions">
          ${canConfirm ? `
            <button class="btn btn-primary" onclick="confirmOrder('${o.id}')">Confirmar Envio</button>
          ` : o.status === "pending" && isRobotBusy ? `
            <span class="text-muted" style="font-size:12px; align-self:center;">Camaro ocupado em outra entrega...</span>
          ` : `
            <span class="text-accent" style="font-weight:600; font-size:13px; align-self:center;">Camaro a caminho</span>
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

// Admin Action: Confirm Order
function confirmOrder(orderId) {
  const telemetry = getTelemetry();
  
  if (telemetry.currentOrderId) {
    alert("O Camaro já está executando uma missão ativa!");
    return;
  }

  const orders = getOrders();
  const order = orders.find(o => o.id === orderId);
  if (!order) return;

  // Update order status in state
  order.status = "preparing";
  saveOrders(orders);

  // Configure telemetry and trigger simulation
  const now = Date.now();
  
  telemetry.status = "preparing";
  telemetry.currentOrderId = order.id;
  telemetry.startTime = now;
  telemetry.deliveryEndTime = now + 15000; // 15 seconds to deliver (3s prep + 12s travel)
  telemetry.returnEndTime = now + 25000;   // 10 seconds to return to dock
  telemetry.speed = 0;
  telemetry.distance = 450;
  telemetry.eta = 15;

  saveTelemetry(telemetry);
  renderAdminUI();
}

// Admin Action: Cancel/Reject Order
function cancelOrder(orderId) {
  if (!confirm("Tem certeza que deseja recusar este pedido?")) return;

  const orders = getOrders();
  const order = orders.find(o => o.id === orderId);
  if (order) {
    order.status = "canceled";
    saveOrders(orders);
  }
  renderAdminUI();
}
