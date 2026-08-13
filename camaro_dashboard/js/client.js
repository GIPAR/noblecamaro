/* client.js */

let currentCart = [];

// Initialize Client Dashboard
function initClientDashboard() {
  loadCart();
  renderProducts();
  renderClientUI();
  toggleClientSubview('catalog');

  // Search input event (use onclick/oninput to avoid duplicate listener binding)
  const searchInput = document.getElementById("product-search");
  if (searchInput) {
    searchInput.oninput = (e) => {
      renderProducts(e.target.value);
    };
  }

  // Close cart button listener
  const closeCartBtn = document.getElementById("btn-close-cart");
  if (closeCartBtn) {
    closeCartBtn.onclick = closeCartModal;
  }
}

// Global Chatbot Event Delegation (Bulletproof event binding)
document.addEventListener("click", (e) => {
  if (e.target && (e.target.id === "chat-send-btn" || e.target.closest("#chat-send-btn"))) {
    handleChatSend();
  }
});

document.addEventListener("keypress", (e) => {
  if (e.target && e.target.id === "chat-input" && e.key === "Enter") {
    handleChatSend();
  }
});

function handleChatSend() {
  const chatInput = document.getElementById("chat-input");
  if (!chatInput) return;
  
  const text = chatInput.value.trim();
  if (!text) return;
  
  appendChatMessage(text, "user");
  chatInput.value = "";
  
  // Simulate LLM response delay
  setTimeout(() => {
    const response = generateMockLLMResponse(text);
    appendChatMessage(response, "bot");
  }, 800);
}

// Subview navigation: catalog vs tracking
function toggleClientSubview(viewName) {
  const catalogView = document.getElementById("subview-catalog");
  const trackingView = document.getElementById("subview-tracking");
  const btnTracking = document.getElementById("btn-show-tracking");

  if (!catalogView || !trackingView) return;

  if (viewName === 'tracking') {
    catalogView.style.display = "none";
    trackingView.style.display = "block";
    if (btnTracking) btnTracking.classList.add("active");
  } else {
    catalogView.style.display = "block";
    trackingView.style.display = "none";
    if (btnTracking) btnTracking.classList.remove("active");
  }
  
  renderClientUI();
}

// --- CART STATE ACTIONS ---
function loadCart() {
  const user = getCurrentUser();
  if (!user) return;
  currentCart = JSON.parse(localStorage.getItem(`cart_${user.username}`)) || [];
}

function saveCart() {
  const user = getCurrentUser();
  if (!user) return;
  localStorage.setItem(`cart_${user.username}`, JSON.stringify(currentCart));
  updateBadges();
}

function addToCart(productId, quantity) {
  const products = getProducts();
  const product = products.find(p => p.id === productId);
  if (!product) return;

  if (product.stock < quantity) {
    alert("Quantidade solicitada excede o estoque disponível!");
    return;
  }

  const existingItem = currentCart.find(item => item.productId === productId);
  if (existingItem) {
    if (product.stock < (existingItem.quantity + quantity)) {
      alert("Quantidade total no carrinho excede o estoque disponível!");
      return;
    }
    existingItem.quantity += quantity;
  } else {
    currentCart.push({
      productId: product.id,
      productName: product.name,
      quantity: quantity
    });
  }

  saveCart();
  alert(`${quantity}x ${product.name} adicionado(s) ao carrinho!`);
  renderProducts(); // Refresh list to reset quantity selectors
}

function updateCartQuantity(productId, delta) {
  const products = getProducts();
  const product = products.find(p => p.id === productId);
  const item = currentCart.find(i => i.productId === productId);
  if (!item || !product) return;

  const newQty = item.quantity + delta;
  if (newQty <= 0) {
    removeFromCart(productId);
    return;
  }

  if (newQty > product.stock) {
    alert("Estoque máximo atingido!");
    return;
  }

  item.quantity = newQty;
  saveCart();
  renderCartModalItems();
}

function removeFromCart(productId) {
  currentCart = currentCart.filter(item => item.productId !== productId);
  saveCart();
  renderCartModalItems();
}

function clearCart() {
  currentCart = [];
  saveCart();
  closeCartModal();
}

function checkoutCart() {
  if (currentCart.length === 0) {
    alert("Seu carrinho está vazio!");
    return;
  }

  // Get checkout details
  const destinationEl = document.getElementById("checkout-destination");
  const timingEl = document.querySelector('input[name="checkout-timing"]:checked');
  const notesEl = document.getElementById("checkout-notes");

  const destination = destinationEl ? destinationEl.value : "SALA A";
  const timing = timingEl ? timingEl.value : "now";
  const notes = notesEl ? notesEl.value.trim() : "";

  const user = getCurrentUser();
  const products = getProducts();
  const orders = getOrders();

  // Double check stock levels
  for (const item of currentCart) {
    const prod = products.find(p => p.id === item.productId);
    if (!prod || prod.stock < item.quantity) {
      alert(`Erro: Estoque insuficiente para o item: ${item.productName}`);
      return;
    }
  }

  // Deduct stock
  for (const item of currentCart) {
    const prod = products.find(p => p.id === item.productId);
    prod.stock -= item.quantity;
  }
  saveProducts(products);

  // Generate summary text
  const summaryText = currentCart.map(item => `${item.quantity}x ${item.productName}`).join(", ") + ` [Destino: ${destination}]`;

  // Create order
  const newOrder = {
    id: "ord_" + Date.now(),
    customerUsername: user.username,
    customerName: user.name || user.username,
    status: "pending", // pending, preparing, delivering, delivered, canceled
    timestamp: Date.now(),
    items: [...currentCart],
    summaryText: summaryText,
    productName: currentCart[0].productName, // Fallback compatibility
    destination: destination,
    timing: timing === "now" ? "Imediata" : "Agendada",
    notes: notes
  };

  orders.push(newOrder);
  saveOrders(orders);

  // Reset cart form fields
  if (notesEl) notesEl.value = "";
  if (destinationEl) destinationEl.selectedIndex = 0;
  const timingDefault = document.querySelector('input[name="checkout-timing"][value="now"]');
  if (timingDefault) timingDefault.checked = true;

  // Reset cart list
  currentCart = [];
  saveCart();
  closeCartModal();
  
  // Switch to tracking view
  toggleClientSubview('tracking');
  
  appendChatMessage(`Solicitei um pedido para a ${destination} (${newOrder.timing}). Qual é o status atual?`, "user");
  setTimeout(() => {
    appendChatMessage(`Seu pedido foi recebido e aguarda aprovação do operador para iniciar o envio à ${destination}.`, "bot");
  }, 800);
}

// --- MODAL VIEWS ---
function openCartModal() {
  const modal = document.getElementById("cart-modal");
  if (!modal) return;
  modal.style.display = "flex";
  renderCartModalItems();
}

function closeCartModal() {
  const modal = document.getElementById("cart-modal");
  if (modal) modal.style.display = "none";
}

function renderCartModalItems() {
  const listEl = document.getElementById("cart-items-list");
  if (!listEl) return;

  if (currentCart.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <p>Seu carrinho está vazio.</p>
      </div>
    `;
    return;
  }

  const products = getProducts();

  listEl.innerHTML = currentCart.map(item => {
    const prod = products.find(p => p.id === item.productId) || {};
    return `
      <div class="cart-item-row">
        <div class="cart-item-info">
          <div class="cart-item-name">${item.productName}</div>
          <div class="cart-item-stock">Disponível: ${prod.stock || 0} un</div>
        </div>
        <div class="cart-item-actions">
          <div class="qty-selector">
            <button class="qty-btn" onclick="updateCartQuantity('${item.productId}', -1)">-</button>
            <input type="text" class="qty-input" value="${item.quantity}" readonly>
            <button class="qty-btn" onclick="updateCartQuantity('${item.productId}', 1)">+</button>
          </div>
          <span class="btn-remove-cart" onclick="removeFromCart('${item.productId}')">Excluir</span>
        </div>
      </div>
    `;
  }).join("");
}

// --- RENDER VITRINE ---
function renderProducts(filterText = "") {
  const catalogGrid = document.getElementById("catalog-grid");
  if (!catalogGrid) return;

  const products = getProducts();
  const query = filterText.toLowerCase().trim();
  const filtered = products.filter(p => p.name.toLowerCase().includes(query) || p.description.toLowerCase().includes(query));

  if (filtered.length === 0) {
    catalogGrid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <p>Nenhum componente encontrado.</p>
      </div>
    `;
    return;
  }

  catalogGrid.innerHTML = filtered.map(p => {
    const outOfStock = p.stock <= 0;
    
    return `
      <div class="product-card animate-fade-in">
        <div class="product-image-wrapper">
          <img class="product-image" src="${p.image}" alt="${p.name}">
        </div>
        <div class="product-details">
          <div>
            <span class="stock-tag" style="color: ${outOfStock ? 'var(--status-error)' : 'var(--text-muted)'}">
              ${outOfStock ? 'Esgotado' : `Estoque: ${p.stock} unidades`}
            </span>
            <h3 class="product-title">${p.name}</h3>
            <p class="product-desc">${p.description}</p>
          </div>
          <div class="product-action" style="gap: 12px; justify-content: flex-start;">
            ${outOfStock ? `
              <button class="btn" style="flex: 1;" disabled>Sem estoque</button>
            ` : `
              <div class="qty-selector">
                <button class="qty-btn" onclick="adjustProductQtySelector('${p.id}', -1)">-</button>
                <input type="text" id="qty-selector-${p.id}" class="qty-input" value="1" readonly>
                <button class="qty-btn" onclick="adjustProductQtySelector('${p.id}', 1, ${p.stock})">+</button>
              </div>
              <button class="btn btn-primary" style="flex: 1;" onclick="addSelectedToCart('${p.id}')">Adicionar</button>
            `}
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// Adjust quantity selector inside catalog cards
function adjustProductQtySelector(productId, delta, maxStock = 99) {
  const el = document.getElementById(`qty-selector-${productId}`);
  if (!el) return;
  let val = parseInt(el.value) + delta;
  if (val < 1) val = 1;
  if (val > maxStock) val = maxStock;
  el.value = val;
}

function addSelectedToCart(productId) {
  const el = document.getElementById(`qty-selector-${productId}`);
  if (!el) return;
  const qty = parseInt(el.value);
  addToCart(productId, qty);
}

// --- RENDER CLIENT UI ---
function updateBadges() {
  const cartBadge = document.getElementById("cart-badge");
  const trackingBadge = document.getElementById("tracking-badge");

  if (cartBadge) {
    const totalItems = currentCart.reduce((sum, item) => sum + item.quantity, 0);
    if (totalItems > 0) {
      cartBadge.textContent = totalItems;
      cartBadge.style.display = "flex";
    } else {
      cartBadge.style.display = "none";
    }
  }

  if (trackingBadge) {
    const user = getCurrentUser();
    if (user) {
      const orders = getOrders();
      const activeOrdersCount = orders.filter(o => o.customerUsername === user.username && o.status !== "canceled" && !o.customerUsername.endsWith("_archived")).length;
      if (activeOrdersCount > 0) {
        trackingBadge.textContent = activeOrdersCount;
        trackingBadge.style.display = "flex";
      } else {
        trackingBadge.style.display = "none";
      }
    }
  }
}

function renderClientUI() {
  updateBadges();

  const user = getCurrentUser();
  if (!user) return;

  const orders = getOrders();
  // Filter active checkout orders for this client (not archived)
  const clientActiveOrders = orders.filter(o => o.customerUsername === user.username && !o.customerUsername.endsWith("_archived"));
  
  const trackingContainer = document.getElementById("client-tracking-container");
  if (!trackingContainer) return;

  if (clientActiveOrders.length === 0) {
    const emptyHTML = `
      <div class="empty-state" style="border: 1px solid var(--border-color); border-radius: var(--card-radius); background: var(--bg-secondary);">
        <p>Você não possui entregas ativas ou em andamento no momento.</p>
        <button class="btn btn-primary" onclick="toggleClientSubview('catalog')">Ir para o Catálogo</button>
      </div>
    `;
    if (trackingContainer.innerHTML.trim() !== emptyHTML.trim()) {
      trackingContainer.innerHTML = emptyHTML;
    }
    return;
  }

  const telemetry = getTelemetry();

  const stages = [
    { key: "pending", label: "Aguardando" },
    { key: "preparing", label: "Preparando" },
    { key: "delivering", label: "A caminho" },
    { key: "delivered", label: "Entregue" }
  ];

  const newHTML = clientActiveOrders.slice().reverse().map(order => {
    let activeIndex = stages.findIndex(s => s.key === order.status);
    if (activeIndex === -1 && order.status === "returning") {
      activeIndex = 2; // Treat returning as almost delivered / on the way
    }

    // --- CALCULATE ROBOT POSITION ON MAP ---
    let robotX = 50; // default (Doca)
    let robotY = 90; // default (Doca)
    
    // Coordinates for the rooms
    const roomCoordinates = {
      "SALA A": { x: 24, y: 28 }, // Left Top
      "SALA B": { x: 24, y: 72 }, // Left Bottom
      "SALA C": { x: 76, y: 28 }, // Right Top
      "SALA D": { x: 76, y: 72 }  // Right Bottom
    };
    
    const targetRoom = order.destination || "SALA A";
    const coords = roomCoordinates[targetRoom] || roomCoordinates["SALA A"];
    
    if (order.id === telemetry.currentOrderId) {
      const now = Date.now();
      if (telemetry.status === "preparing") {
        robotX = 50;
        robotY = 90;
      } else if (telemetry.status === "delivering") {
        const prepTime = telemetry.startTime + 3000;
        const duration = telemetry.deliveryEndTime - prepTime;
        const elapsed = now - prepTime;
        const progress = Math.max(0, Math.min(1, elapsed / duration));
        
        // 0% to 70% along the vertical corridor (50, 90) -> (50, targetY)
        // 70% to 100% turn horizontally (50, targetY) -> (targetX, targetY)
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
        
        // 0% to 30% horizontal from room back to corridor
        // 30% to 100% vertical down the corridor to base dock
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
    } else if (order.status === "delivered") {
      robotX = 50;
      robotY = 90;
    }

    // Details box content (NO battery percentage)
    let detailsHTML = "";
    if (order.status === "pending") {
      detailsHTML = `
        <div class="detail-item">
          <div class="detail-label">Status</div>
          <div class="detail-value">Aguardando confirmação do operador</div>
        </div>
      `;
    } else if (order.status === "preparing") {
      detailsHTML = `
        <div class="detail-item">
          <div class="detail-label">Veículo</div>
          <div class="detail-value">Camaro Autônomo</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Preparação</div>
          <div class="detail-value">Robô atracado na estação, carregando itens</div>
        </div>
      `;
    } else if (order.status === "delivering" || (order.id === telemetry.currentOrderId && telemetry.status === "returning")) {
      const speedKmh = telemetry.speed.toFixed(1);
      const distText = telemetry.distance > 0 ? `${telemetry.distance}m` : "Chegando...";
      const etaText = telemetry.eta > 0 ? `${telemetry.eta}s` : "Entregando...";
      
      detailsHTML = `
        <div class="detail-item">
          <div class="detail-label">Módulo</div>
          <div class="detail-value">Camaro Autônomo</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Distância Restante</div>
          <div class="detail-value">${distText}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Tempo Estimado (ETA)</div>
          <div class="detail-value">${etaText}</div>
        </div>
      `;
    } else if (order.status === "delivered") {
      detailsHTML = `
        <div class="detail-item">
          <div class="detail-label">Entregue</div>
          <div class="detail-value">Itens entregues no destino com sucesso!</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Ações</div>
          <div class="detail-value">
            <button class="btn btn-primary" style="padding: 6px 14px; font-size:12px;" onclick="clearClientOrder('${order.id}')">Confirmar Recebimento</button>
          </div>
        </div>
      `;
    } else if (order.status === "canceled") {
      detailsHTML = `
        <div class="detail-item">
          <div class="detail-label">Cancelado</div>
          <div class="detail-value" style="color: var(--status-error);">Solicitação recusada pelo operador</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Ações</div>
          <div class="detail-value">
            <button class="btn" style="padding: 6px 14px; font-size:12px;" onclick="clearClientOrder('${order.id}')">Remover da Lista</button>
          </div>
        </div>
      `;
    }

    const percent = activeIndex === -1 ? 0 : (activeIndex / (stages.length - 1)) * 100;

    return `
      <div class="tracking-card" style="margin-top: 0; margin-bottom: 24px;">
        <h3 class="tracking-title" style="border-bottom: 1px solid var(--border-color); padding-bottom: 12px; font-size: 14px;">
          Pedido: <span class="text-accent">${order.id.toUpperCase()}</span>
          <br>
          <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-top: 4px; display: inline-block;">
            ${order.summaryText}
          </span>
          ${order.notes ? `<br><span style="font-size:11px; font-weight:normal; color:var(--text-muted);">Obs: "${order.notes}"</span>` : ""}
        </h3>
        
        ${order.status !== "canceled" ? `
          <div class="tracking-steps" style="margin-top: 16px;">
            <div class="tracking-progress-bar" style="width: ${percent}%"></div>
            ${stages.map((stage, idx) => {
              let stateClass = "";
              if (idx < activeIndex) stateClass = "completed";
              else if (idx === activeIndex) stateClass = "active";
              
              return `
                <div class="tracking-step ${stateClass}">
                  <div class="step-dot">${idx + 1}</div>
                  <div class="step-label" style="font-size: 10px;">${stage.label}</div>
                </div>
              `;
            }).join("")}
          </div>
        ` : ""}

        <!-- Live 2D Corridor & Room Map -->
        <div class="map-container">
          <div class="map-corridor">
            <div class="map-corridor-label">Corredor</div>
          </div>
          <div class="map-room sala-a ${targetRoom === 'SALA A' && order.status !== 'delivered' ? 'active-target' : ''}">
            <div class="map-room-name">Sala A</div>
          </div>
          <div class="map-room sala-b ${targetRoom === 'SALA B' && order.status !== 'delivered' ? 'active-target' : ''}">
            <div class="map-room-name">Sala B</div>
          </div>
          <div class="map-room sala-c ${targetRoom === 'SALA C' && order.status !== 'delivered' ? 'active-target' : ''}">
            <div class="map-room-name">Sala C</div>
          </div>
          <div class="map-room sala-d ${targetRoom === 'SALA D' && order.status !== 'delivered' ? 'active-target' : ''}">
            <div class="map-room-name">Sala D</div>
          </div>
          <div class="map-dock">Doca Base</div>
          <div class="map-robot" style="left: ${robotX}%; top: ${robotY}%;" title="Camaro"></div>
        </div>

        <div class="tracking-details" style="margin-top: 16px;">
          ${detailsHTML}
        </div>
      </div>
    `;
  }).join("");

  // Only assign if HTML has changed to prevent flickers
  if (trackingContainer.innerHTML !== newHTML) {
    trackingContainer.innerHTML = newHTML;
  }
}

// Archive/Dismiss completed tracking cards
function clearClientOrder(orderId) {
  const orders = getOrders();
  const order = orders.find(o => o.id === orderId);
  if (order) {
    order.customerUsername = order.customerUsername + "_archived";
    saveOrders(orders);
  }
  renderClientUI();
}

// Rule-based Mock LLM Chatbot response processor for electronics
function generateMockLLMResponse(userInput) {
  const query = userInput.toLowerCase();
  const telemetry = getTelemetry();
  const orders = getOrders();
  const user = getCurrentUser();
  
  // Find current user's active orders
  const clientActiveOrders = orders.filter(o => o.customerUsername === user.username && !o.customerUsername.endsWith("_archived"));

  if (query.includes("pedido") || query.includes("status") || query.includes("entrega") || query.includes("onde está") || query.includes("onde esta")) {
    if (clientActiveOrders.length === 0) {
      return "Você não possui nenhuma solicitação de entrega ativa no momento. Adicione componentes ao carrinho na vitrine ao lado e finalize a solicitação para despachar o Camaro.";
    }
    
    const latest = clientActiveOrders[clientActiveOrders.length - 1];
    let statusDesc = "";
    switch (latest.status) {
      case "pending":
        statusDesc = "está na fila aguardando a confirmação do operador.";
        break;
      case "preparing":
        statusDesc = "está na fase de preparação física. O robô está sendo carregado na base.";
        break;
      case "delivering":
        statusDesc = `está em trânsito! O robô Camaro está navegando em direção ao destino (${latest.destination}) a ${telemetry.speed.toFixed(1)} km/h. Distância restante: ${telemetry.distance}m.`;
        break;
      case "delivered":
        statusDesc = `já foi entregue na ${latest.destination}! Por favor, retire os componentes e confirme o recebimento na tela de acompanhamento.`;
        break;
      case "canceled":
        statusDesc = "foi recusado.";
        break;
      default:
        statusDesc = `está com status: ${latest.status}.`;
    }
    
    return `Seu pedido mais recente (${latest.id.toUpperCase()}) contendo [${latest.summaryText}] ${statusDesc}`;
  }

  if (query.includes("camaro") || query.includes("robo") || query.includes("robô") || query.includes("simulador") || query.includes("gazebo")) {
    let roboStatus = "";
    switch (telemetry.status) {
      case "idle": roboStatus = "ocioso na estação base de recarga."; break;
      case "preparing": roboStatus = "ancorado, acondicionando itens de entrega."; break;
      case "delivering": roboStatus = `conduzindo missão de waypoint. Velocidade: ${telemetry.speed.toFixed(1)} km/h. Distância: ${telemetry.distance}m.`; break;
      case "returning": roboStatus = "retornando à base."; break;
      case "charging": roboStatus = `atracado na doca, carregando bateria em ${telemetry.battery.toFixed(0)}%.`; break;
    }
    return `O Camaro Autônomo de Delivery de Componentes é um robô simulado no Gazebo Harmonic que executa missões de waypoints gerenciadas por um orquestrador baseado em LLM. Atualmente ele está no estado "${telemetry.status}" (${roboStatus}).`;
  }

  if (query.includes("estoque") || query.includes("componentes") || query.includes("produtos") || query.includes("placa") || query.includes("sensor") || query.includes("relé") || query.includes("rele")) {
    const products = getProducts();
    const list = products.map(p => `- ${p.name} (Disponível: ${p.stock} un)`).join("\n");
    return `Estoque de componentes disponíveis na estação base:\n${list}\n\nPara solicitar, use os botões de ajuste de quantidade e clique em 'Adicionar' na vitrine do site.`;
  }

  if (query.includes("carrinho") || query.includes("como pedir") || query.includes("comprar")) {
    return "Para fazer pedidos:\n1. Ajuste a quantidade desejada do componente usando os botões '+' e '-' na vitrine.\n2. Clique em 'Adicionar' para colocá-lo no carrinho.\n3. Clique no ícone de carrinho no canto superior direito para revisar seus itens.\n4. Selecione sua localização (Sala A, B, C ou D) e clique em 'Confirmar Pedido' para enviar a solicitação ao operador.";
  }

  return "Olá! Eu sou o assistente do robô Camaro. Posso te informar sobre o estoque de componentes eletrônicos, o status da simulação no Gazebo Harmonic, e auxiliar no passo a passo de solicitações. Como posso ajudar?";
}
