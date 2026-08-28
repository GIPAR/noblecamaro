/* client.js */

let currentCart = [];

// Initialize Client Dashboard
function initClientDashboard() {
  loadCart();
  renderProducts();
  renderClientUI();
  loadChatHistory();
  toggleClientSubview('catalog');

  // Search input event
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

// ─── CHAT PERSISTENCE & RENDERING ──────────────────────────────────────────

function getChatStorageKey() {
  const user = getCurrentUser();
  return user ? `camaro_chat_${user.username}` : "camaro_chat_guest";
}

function loadChatHistory() {
  const chatMessages = document.getElementById("chat-messages");
  if (!chatMessages) return;

  chatMessages.innerHTML = "";
  const key = getChatStorageKey();
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem(key)) || [];
  } catch (e) {
    history = [];
  }

  if (history.length === 0) {
    const defaultMsg = {
      message: "Olá! Eu sou o assistente do robô Camaro 🤖\nComo posso ajudar você no seu pedido ou telemetria hoje?",
      sender: "bot",
      actionBadge: null
    };
    renderChatMessageElement(defaultMsg.message, defaultMsg.sender, defaultMsg.actionBadge);
    localStorage.setItem(key, JSON.stringify([defaultMsg]));
  } else {
    history.forEach(item => {
      renderChatMessageElement(item.message, item.sender, item.actionBadge);
    });
  }
}

function renderChatMessageElement(message, sender = "bot", actionBadge = null) {
  const chatMessages = document.getElementById("chat-messages");
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

function appendChatMessage(message, sender = "bot", actionBadge = null) {
  renderChatMessageElement(message, sender, actionBadge);

  const key = getChatStorageKey();
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem(key)) || [];
  } catch (e) {
    history = [];
  }

  history.push({ message, sender, actionBadge, timestamp: Date.now() });
  if (history.length > 100) history.shift();
  localStorage.setItem(key, JSON.stringify(history));
}

function clearChatHistory() {
  const key = getChatStorageKey();
  localStorage.removeItem(key);
  loadChatHistory();
}

// Global Chatbot Event Listeners
document.addEventListener("click", (e) => {
  // Send button
  if (e.target && (e.target.id === "chat-send-btn" || e.target.closest("#chat-send-btn"))) {
    e.preventDefault();
    e.stopPropagation();
    handleChatSend(e);
    return;
  }

  // Clear chat button
  if (e.target && (e.target.id === "btn-clear-chat" || e.target.closest("#btn-clear-chat"))) {
    e.preventDefault();
    e.stopPropagation();
    if (confirm("Deseja limpar as mensagens deste chat?")) {
      clearChatHistory();
    }
    return;
  }

  // Quick Action Suggestion Chips for Client
  const chip = e.target.closest("#chat-suggestions .chat-chip");
  if (chip) {
    e.preventDefault();
    e.stopPropagation();
    const cmd = chip.dataset.cmd || chip.textContent.replace(/^[^a-zA-Z0-9]+/, "").trim();
    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
      chatInput.value = cmd;
      handleChatSend(e);
    }
    return;
  }
});

document.addEventListener("keydown", (e) => {
  if (e.target && e.target.id === "chat-input" && e.key === "Enter") {
    e.preventDefault();
    e.stopPropagation();
    handleChatSend(e);
  }
});

// ─── PRODUCT FINDER & CART ACTIONS ─────────────────────────────────────────

function findProduct(productIdOrQuery) {
  const products = getProducts();
  if (!productIdOrQuery) return null;
  const q = productIdOrQuery.toString().toLowerCase().trim();

  // 1. Exact ID match
  let p = products.find(prod => prod.id.toLowerCase() === q);
  if (p) return p;

  // 2. Alias / keyword matches
  if (q.includes("esp32") || q.includes("esp 32") || q.includes("microcontrolador") || q.includes("devkit") || q === "p1") {
    return products.find(prod => prod.id === "esp32" || prod.id === "p1" || prod.name.includes("ESP32"));
  }
  if (q.includes("sensor") || q.includes("ultrasson") || q.includes("hc-sr04") || q.includes("distancia") || q === "p2") {
    return products.find(prod => prod.id === "sensor_us" || prod.id === "p2" || prod.name.includes("Ultrassônico") || prod.name.includes("Sensor"));
  }
  if (q.includes("rele") || q.includes("relé") || q.includes("relay") || q === "p3") {
    return products.find(prod => prod.id === "relay" || prod.id === "p3" || prod.name.includes("Relé"));
  }

  // 3. Substring match
  return products.find(prod => prod.name.toLowerCase().includes(q) || prod.id.toLowerCase().includes(q));
}

function addToCartSilently(productIdOrQuery, quantity = 1) {
  const product = findProduct(productIdOrQuery);
  if (!product || product.stock < quantity) return false;

  const existingItem = currentCart.find(item => item.productId === product.id);
  if (existingItem) {
    if (product.stock < (existingItem.quantity + quantity)) return false;
    existingItem.quantity += quantity;
  } else {
    currentCart.push({
      productId: product.id,
      productName: product.name,
      quantity: quantity
    });
  }

  saveCart();
  renderProducts();
  return true;
}

// Execute actions dispatched by AI
function executeChatAction(action) {
  if (!action) return null;
  const actionType = action.type || action.action;

  if (actionType === "add_to_cart") {
    const success = addToCartSilently(action.product_id, action.quantity || 1);
    if (success) {
      const prod = findProduct(action.product_id);
      return `Adicionado ao carrinho: ${action.quantity || 1}x ${prod ? prod.name : (action.product_name || 'Componente')}`;
    }
  } else if (actionType === "set_destination") {
    const destSelect = document.getElementById("checkout-destination");
    if (destSelect && action.destination) {
      destSelect.value = action.destination;
    }
    return `Destino definido: ${action.destination}`;
  } else if (actionType === "submit_order") {
    if (action.product_id) {
      addToCartSilently(action.product_id, action.quantity || 1);
    }
    const destSelect = document.getElementById("checkout-destination");
    if (destSelect && action.destination) {
      destSelect.value = action.destination;
    }
    const notesInput = document.getElementById("checkout-notes");
    if (notesInput && action.notes) {
      notesInput.value = action.notes;
    }
    setTimeout(() => {
      checkoutCart();
    }, 400);
    const prod = action.product_id ? findProduct(action.product_id) : null;
    return `Pedido Enviado: ${prod ? (action.quantity || 1) + 'x ' + prod.name + ' → ' : ''}${action.destination || 'Destino'}`;
  } else if (actionType === "open_cart") {
    openCartModal();
    return "Carrinho aberto";
  } else if (actionType === "clear_cart") {
    clearCart();
    return "Carrinho esvaziado";
  } else if (actionType === "show_tracking") {
    toggleClientSubview('tracking');
    return "Visualizando mapa em tempo real";
  } else if (actionType === "show_catalog") {
    toggleClientSubview('catalog');
    return "Visualizando catálogo de produtos";
  }
  return null;
}

// Handle sending a chat message
async function handleChatSend(e) {
  if (e && e.preventDefault) {
    e.preventDefault();
    e.stopPropagation();
  }
  const chatInput = document.getElementById("chat-input");
  if (!chatInput) return;

  const text = chatInput.value.trim();
  if (!text) return;

  appendChatMessage(text, "user");
  chatInput.value = "";

  const user = getCurrentUser();
  const sessionId = user ? user.username : "demo_session";

  // Try sending to backend API first
  let backendHandled = false;
  if (typeof apiSendChat === "function") {
    try {
      const data = await apiSendChat(text, sessionId, currentCart);
      if (data && data.text) {
        backendHandled = true;
        let lastBadge = null;

        if (data.actions && data.actions.length > 0) {
          for (const action of data.actions) {
            const badge = executeChatAction(action);
            if (badge) lastBadge = badge;
          }
        }

        appendChatMessage(data.text, "bot", lastBadge);
      }
    } catch (e) {
      backendHandled = false;
    }
  }

  if (!backendHandled) {
    // Process via local AI orchestrator
    setTimeout(() => {
      const { reply, actions } = processLocalLLMOrchestrator(text);
      let lastBadge = null;

      if (actions && actions.length > 0) {
        for (const action of actions) {
          const badge = executeChatAction(action);
          if (badge) lastBadge = badge;
        }
      }

      appendChatMessage(reply, "bot", lastBadge);
    }, 400);
  }
}

// Local Conversational AI Orchestrator
function processLocalLLMOrchestrator(userInput) {
  const q = userInput.toLowerCase().trim();
  const telemetry = getTelemetry();
  const orders = getOrders();
  const user = getCurrentUser();
  const products = getProducts();

  const clientActiveOrders = orders.filter(o => 
    user && o.customerUsername === user.username && !o.customerUsername.endsWith("_archived")
  );

  let reply = "";
  let actions = [];

  // 1. UI Navigation Commands
  if (q.includes("limpar carrinho") || q.includes("esvaziar carrinho") || q.includes("zerar carrinho") || q.includes("limpar tudo")) {
    actions.push({ type: "clear_cart" });
    return { reply: "Seu carrinho foi limpo com sucesso!", actions };
  }

  if ((q.includes("abrir carrinho") || q.includes("ver carrinho") || q.includes("mostrar carrinho") || q.includes("meu carrinho")) && !q.includes("adiciona") && !q.includes("quero")) {
    actions.push({ type: "open_cart" });
    return { reply: "Abrindo o carrinho para você revisar os itens e confirmar o destino.", actions };
  }

  if (q.includes("mostrar mapa") || q.includes("ver mapa") || q.includes("abrir mapa") || q.includes("tela de acompanhamento") || q.includes("acompanhar entrega") || q.includes("acompanhar pedido") || q.includes("rastrear")) {
    actions.push({ type: "show_tracking" });
    return { reply: "Alternando para a tela de acompanhamento com o mapa 2D em tempo real!", actions };
  }

  if (q.includes("ver catalogo") || q.includes("ver catálogo") || q.includes("vitrine") || q.includes("loja")) {
    actions.push({ type: "show_catalog" });
    return { reply: "Aqui está o catálogo completo de componentes eletrônicos.", actions };
  }

  // 2. Room Selection Only
  let targetRoomOnly = null;
  if (q.includes("sala a") || q.includes("sala 1")) targetRoomOnly = "SALA A";
  else if (q.includes("sala b") || q.includes("sala 2")) targetRoomOnly = "SALA B";
  else if (q.includes("sala c") || q.includes("sala 3")) targetRoomOnly = "SALA C";
  else if (q.includes("sala d") || q.includes("sala 4")) targetRoomOnly = "SALA D";

  if (targetRoomOnly && (q.includes("escolher") || q.includes("selecionar") || q.includes("mudar") || q.includes("definir") || q.includes("trocar") || q.includes("estou na") || q.startsWith("sala "))) {
    if (!findProduct(q) && !q.includes("faz o pedido") && !q.includes("confirmar pedido")) {
      actions.push({ type: "set_destination", destination: targetRoomOnly });
      return { reply: `📍 Local de entrega definido para a **${targetRoomOnly}**! Você pode adicionar mais componentes ou dizer 'confirmar pedido'.`, actions };
    }
  }

  // 3. Real-time Location & Telemetry Query
  if (
    q.includes("onde") || q.includes("cadê") || q.includes("cade") || 
    q.includes("local") || q.includes("localização") || q.includes("localizacao") || 
    q.includes("rota") || q.includes("caminho") || q.includes("posição") || 
    q.includes("posicao") || (q.includes("status") && (q.includes("carro") || q.includes("camaro") || q.includes("robô") || q.includes("robo")))
  ) {
    const activeOrder = clientActiveOrders.find(o => o.id === telemetry.currentOrderId) || clientActiveOrders[clientActiveOrders.length - 1];
    const destination = activeOrder ? (activeOrder.destination || "Sala de destino") : "Sala designada";

    if (telemetry.status === "delivering") {
      actions.push({ type: "show_tracking" });
      reply = `📍 O Camaro está em movimento no corredor navegando em direção à ${destination}!\n\n• Velocidade: ${telemetry.speed.toFixed(1)} km/h\n• Distância restante: ${telemetry.distance}m\n• Tempo estimado de chegada (ETA): ${telemetry.eta}s\n\nVocê pode ver a posição dele em tempo real no mapa da tela de acompanhamento.`;
      return { reply, actions };
    } else if (telemetry.status === "returning") {
      actions.push({ type: "show_tracking" });
      reply = `🔄 A entrega na ${destination} foi realizada com sucesso! O Camaro está agora no caminho de volta pelo corredor em direção à Doca Base.\n\n• Velocidade de retorno: ${telemetry.speed.toFixed(1)} km/h\n• Distância até a base: ${telemetry.distance}m`;
      return { reply, actions };
    } else if (telemetry.status === "preparing") {
      actions.push({ type: "show_tracking" });
      reply = `📦 O Camaro está ancorado na Doca Base sendo preparado e carregado com os componentes. A partida pelo corredor iniciará em poucos segundos.`;
      return { reply, actions };
    } else if (telemetry.status === "charging" || telemetry.status === "idle") {
      reply = `⚡ O Camaro está atualmente acoplado na Doca Base aguardando novas missões de entrega. Bateria em ${telemetry.battery.toFixed(0)}%. Posso adicionar componentes e enviar para sua sala quando quiser!`;
      return { reply, actions };
    }
  }

  // 4. Component Request & Ordering via Chat
  const matchedProduct = findProduct(q);
  if (matchedProduct) {
    let quantity = 1;
    const numMatch = q.match(/(\d+)\s*(?:x|unidades?|peças?|pecas?|pcs?)?/);
    if (numMatch && parseInt(numMatch[1]) > 0) {
      quantity = parseInt(numMatch[1]);
    } else if (q.includes("dois") || q.includes("duas")) {
      quantity = 2;
    } else if (q.includes("tres") || q.includes("três")) {
      quantity = 3;
    } else if (q.includes("quatro")) {
      quantity = 4;
    } else if (q.includes("cinco")) {
      quantity = 5;
    }

    let targetRoom = null;
    if (q.includes("sala a") || q.includes("sala 1")) targetRoom = "SALA A";
    else if (q.includes("sala b") || q.includes("sala 2")) targetRoom = "SALA B";
    else if (q.includes("sala c") || q.includes("sala 3")) targetRoom = "SALA C";
    else if (q.includes("sala d") || q.includes("sala 4")) targetRoom = "SALA D";

    const isAutoSubmit = targetRoom !== null || q.includes("faz o pedido") || q.includes("fazer pedido") || 
                         q.includes("pede pra mim") || q.includes("manda pra") || 
                         q.includes("envia pra") || q.includes("entrega na") || 
                         q.includes("finaliza") || q.includes("confirmar pedido");

    if (isAutoSubmit) {
      const room = targetRoom || "SALA A";
      actions.push({
        type: "submit_order",
        product_id: matchedProduct.id,
        product_name: matchedProduct.name,
        quantity: quantity,
        destination: room,
        timing: "now",
        notes: "Pedido via Chat AI"
      });
      reply = `✅ Pedido confirmado com sucesso! Adicionei ${quantity}x ${matchedProduct.name} e enviei a solicitação para a ${room}.\n\nO Camaro iniciará o trajeto pelo corredor assim que o operador confirmar o envio.`;
      return { reply, actions };
    } else {
      actions.push({
        type: "add_to_cart",
        product_id: matchedProduct.id,
        product_name: matchedProduct.name,
        quantity: quantity
      });
      reply = `🛒 Adicionei ${quantity}x ${matchedProduct.name} ao seu carrinho!\n\nVocê pode me dizer 'escolher Sala B' ou 'confirmar pedido'.`;
      return { reply, actions };
    }
  }

  // 5. Confirmation of existing cart
  if (q.includes("confirmar pedido") || q.includes("finalizar pedido") || q.includes("enviar pedido") || q.includes("pode enviar") || q.includes("manda o pedido") || q.includes("fazer pedido") || q.includes("concluir pedido")) {
    if (currentCart.length === 0) {
      return { reply: "Seu carrinho está vazio! Primeiro me diga quais componentes você precisa (ex: 'adicione 2 ESP32').", actions: [] };
    }
    let room = "SALA A";
    if (q.includes("sala b")) room = "SALA B";
    else if (q.includes("sala c")) room = "SALA C";
    else if (q.includes("sala d")) room = "SALA D";

    actions.push({
      type: "submit_order",
      destination: room,
      timing: "now",
      notes: "Confirmado via Chat AI"
    });
    return { reply: `✅ Confirmando o envio do seu carrinho para a ${room}! Alternando para a tela de acompanhamento.`, actions };
  }

  // 6. Order Status Query
  if (q.includes("pedido") || q.includes("meus pedidos") || q.includes("acompanhar") || q.includes("entrega")) {
    if (clientActiveOrders.length === 0) {
      reply = "Você não possui nenhuma solicitação de entrega ativa no momento. Você pode me pedir componentes por aqui (ex: 'adicione 2 ESP32') ou escolher na vitrine ao lado.";
      return { reply, actions: [] };
    }

    const latest = clientActiveOrders[clientActiveOrders.length - 1];
    let statusDesc = "";
    switch (latest.status) {
      case "pending":
        statusDesc = "está na fila aguardando a confirmação de despacho do operador.";
        break;
      case "preparing":
        statusDesc = "está em fase de preparação na Doca Base.";
        break;
      case "delivering":
        statusDesc = `está a caminho da ${latest.destination}! Velocidade: ${telemetry.speed.toFixed(1)} km/h, distância restante: ${telemetry.distance}m.`;
        break;
      case "delivered":
        statusDesc = `já foi entregue na ${latest.destination}! Você pode retirar os componentes e confirmar o recebimento.`;
        break;
      case "canceled":
        statusDesc = "foi cancelado pelo operador.";
        break;
      default:
        statusDesc = `está com status: ${latest.status}.`;
    }

    actions.push({ type: "show_tracking" });
    reply = `Seu pedido (${latest.id.toUpperCase()}) com [${latest.summaryText}] ${statusDesc}`;
    return { reply, actions };
  }

  // 7. Stock Query
  if (q.includes("estoque") || q.includes("componentes") || q.includes("produtos") || q.includes("o que tem") || q.includes("catalogo")) {
    const list = products.map(p => `• ${p.name}: ${p.stock > 0 ? p.stock + " un disponíveis" : "Esgotado"}`).join("\n");
    reply = `📦 Componentes em estoque na estação base:\n\n${list}\n\nPara solicitar, você pode me dizer: 'adicione 2 ESP32' e depois 'escolher Sala B'.`;
    return { reply, actions: [] };
  }

  // 8. Greetings
  if (q.includes("olá") || q.includes("oi") || q.includes("bom dia") || q.includes("boa tarde") || q.includes("boa noite") || q.includes("ola") || q.includes("help") || q.includes("ajuda")) {
    reply = "Olá! Eu sou o assistente e orquestrador autônomo do robô Camaro 🤖\n\nVocê pode clicar nos atalhos acima ou me pedir comandos como:\n• *'Adicione 2 ESP32'*\n• *'Abrir carrinho'*\n• *'Escolher Sala B'*\n• *'Confirmar pedido'*\n• *'Acompanhar pedido'*\n\nComo posso te ajudar?";
    return { reply, actions: [] };
  }

  // Default intelligent fallback
  reply = "Posso te ajudar a solicitar componentes, escolher a sala de destino, confirmar pedidos ou verificar a telemetria do robô Camaro em tempo real. O que você gostaria de fazer?";
  return { reply, actions: [] };
}

// ─── SUBVIEW NAVIGATION ───────────────────────────────────────────────────

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

// ─── CART STATE ACTIONS ───────────────────────────────────────────────────

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
  const product = findProduct(productId);
  if (!product) return;

  if (product.stock < quantity) {
    alert("Quantidade solicitada excede o estoque disponível!");
    return;
  }

  const success = addToCartSilently(product.id, quantity);
  if (success) {
    alert(`${quantity}x ${product.name} adicionado(s) ao carrinho!`);
  }
}

function updateCartQuantity(productId, delta) {
  const product = findProduct(productId);
  const item = currentCart.find(i => i.productId === (product ? product.id : productId));
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
  const product = findProduct(productId);
  const targetId = product ? product.id : productId;
  currentCart = currentCart.filter(item => item.productId !== targetId);
  saveCart();
  renderCartModalItems();
}

function clearCart() {
  currentCart = [];
  saveCart();
  closeCartModal();
  renderProducts();
}

function checkoutCart() {
  if (currentCart.length === 0) {
    alert("Seu carrinho está vazio!");
    return;
  }

  const destinationEl = document.getElementById("checkout-destination");
  const timingEl = document.querySelector('input[name="checkout-timing"]:checked');
  const notesEl = document.getElementById("checkout-notes");

  const destination = destinationEl ? destinationEl.value : "SALA A";
  const timing = timingEl ? timingEl.value : "now";
  const notes = notesEl ? notesEl.value.trim() : "";

  const user = getCurrentUser();
  const products = getProducts();
  const orders = getOrders();

  // Deduct stock
  for (const item of currentCart) {
    const prod = findProduct(item.productId);
    if (prod) {
      prod.stock = Math.max(0, prod.stock - item.quantity);
    }
  }
  saveProducts(products);

  const summaryText = currentCart.map(item => `${item.quantity}x ${item.productName}`).join(", ") + ` [Destino: ${destination}]`;

  const newOrder = {
    id: "ord_" + Date.now(),
    customerUsername: user ? user.username : "cliente",
    customerName: user ? (user.name || user.username) : "Cliente",
    status: "pending",
    timestamp: Date.now(),
    items: [...currentCart],
    summaryText: summaryText,
    productName: currentCart[0].productName,
    destination: destination,
    timing: timing === "now" ? "Imediata" : "Agendada",
    notes: notes
  };

  orders.push(newOrder);
  saveOrders(orders);

  if (typeof apiCreateOrder === "function") {
    apiCreateOrder(currentCart, destination, newOrder.timing, notes)
      .then(async (createdOrder) => {
        if (createdOrder && createdOrder.id) {
          try {
            const qData = await apiFetch("/queue");
            if (qData && qData.queue) {
              const pos = qData.queue.findIndex(m => m.order_id === createdOrder.id) + 1;
              if (pos > 0) {
                const telemetry = getTelemetry();
                if (telemetry.currentOrderId && telemetry.currentOrderId !== createdOrder.id) {
                  alert(`Seu pedido foi recebido e enfileirado na posição ${pos} do Camaro!`);
                }
              }
            }
          } catch (e) {}
        }
      })
      .catch((err) => {
        console.error("apiCreateOrder failed:", err);
      });
  }

  if (notesEl) notesEl.value = "";
  if (destinationEl) destinationEl.selectedIndex = 0;
  const timingDefault = document.querySelector('input[name="checkout-timing"][value="now"]');
  if (timingDefault) timingDefault.checked = true;

  currentCart = [];
  saveCart();
  closeCartModal();

  toggleClientSubview('tracking');
}

// ─── MODAL VIEWS ──────────────────────────────────────────────────────────

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
    const prod = findProduct(item.productId) || {};
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

// ─── RENDER VITRINE ───────────────────────────────────────────────────────

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

// ─── RENDER CLIENT UI ─────────────────────────────────────────────────────

function updateBadges() {
  const cartBadge = document.getElementById("cart-badge");
  const trackingBadge = document.getElementById("tracking-badge");

  if (cartBadge) {
    const totalItems = currentCart.reduce((sum, item) => sum + item.quantity, 0);
    if (totalItems > 0) {
      if (cartBadge.textContent !== String(totalItems)) {
        cartBadge.textContent = totalItems;
      }
      if (cartBadge.style.display !== "flex") {
        cartBadge.style.display = "flex";
      }
    } else {
      if (cartBadge.style.display !== "none") {
        cartBadge.style.display = "none";
      }
    }
  }

  if (trackingBadge) {
    const user = getCurrentUser();
    if (user) {
      const orders = getOrders();
      const activeOrdersCount = orders.filter(o => o.customerUsername === user.username && o.status !== "canceled" && !o.customerUsername.endsWith("_archived")).length;
      if (activeOrdersCount > 0) {
        if (trackingBadge.textContent !== String(activeOrdersCount)) {
          trackingBadge.textContent = activeOrdersCount;
        }
        if (trackingBadge.style.display !== "flex") {
          trackingBadge.style.display = "flex";
        }
      } else {
        if (trackingBadge.style.display !== "none") {
          trackingBadge.style.display = "none";
        }
      }
    }
  }
}

function renderClientUI() {
  updateBadges();

  const user = getCurrentUser();
  if (!user) return;

  const orders = getOrders();
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
    trackingContainer.removeAttribute("data-rendered-ids");
    return;
  }

  const telemetry = getTelemetry();

  const stages = [
    { key: "pending", label: "Aguardando" },
    { key: "preparing", label: "Preparando" },
    { key: "delivering", label: "A caminho" },
    { key: "delivered", label: "Entregue" }
  ];

  const activeIdsStr = clientActiveOrders.map(o => o.id + "_" + o.status).join("|");
  const currentRenderedIds = trackingContainer.getAttribute("data-rendered-ids") || "";

  if (activeIdsStr !== currentRenderedIds) {
    const newHTML = clientActiveOrders.slice().reverse().map(order => {
      let activeIndex = stages.findIndex(s => s.key === order.status);
      if (activeIndex === -1 && order.status === "returning") {
        activeIndex = 2;
      }
      const percent = activeIndex === -1 ? 0 : (activeIndex / (stages.length - 1)) * 100;
      const targetRoom = order.destination || "SALA A";

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
        detailsHTML = `
          <div class="detail-item">
            <div class="detail-label">Módulo</div>
            <div class="detail-value">Camaro Autônomo</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Distância Restante</div>
            <div class="detail-value" id="dist-val-${order.id}">--</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Tempo Estimado (ETA)</div>
            <div class="detail-value" id="eta-val-${order.id}">--</div>
          </div>
        `;
      } else if (order.status === "delivered") {
        detailsHTML = `
          <div class="detail-item">
            <div class="detail-label">Entregue ✅</div>
            <div class="detail-value">Itens entregues no destino com sucesso!</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Avaliação da Entrega</div>
            <div class="detail-value">
              <div id="feedback-section-${order.id}">
                <div style="margin-bottom: 8px; font-size: 12px; color: var(--text-secondary);">Como foi a sua experiência? (1 a 5 estrelas)</div>
                <div class="star-rating-row" style="display: flex; gap: 4px; margin-bottom: 10px;">
                  ${[1,2,3,4,5].map(n => `
                    <button
                      class="star-btn"
                      data-order="${order.id}"
                      data-star="${n}"
                      onclick="handleStarClick('${order.id}', ${n})"
                      title="${n} estrela${n>1?'s':''}"
                      style="font-size: 22px; background: none; border: none; cursor: pointer; color: var(--text-muted); transition: color 0.15s; padding: 2px;"
                    >☆</button>
                  `).join("")}
                </div>
                <div id="feedback-comment-${order.id}" style="display: none;">
                  <textarea
                    id="feedback-text-${order.id}"
                    placeholder="Comentário opcional (ex: entregou rápido, veio correto...)"
                    style="width: 100%; min-height: 56px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 12px; padding: 8px; font-family: var(--font-family); resize: vertical; margin-bottom: 8px;"
                  ></textarea>
                  <div style="display: flex; gap: 8px;">
                    <button class="btn btn-primary" style="padding: 6px 14px; font-size: 12px;" onclick="submitFeedback('${order.id}')">
                      Confirmar Recebimento
                    </button>
                    <button class="btn" style="padding: 6px 10px; font-size: 12px;" onclick="clearClientOrder('${order.id}')">
                      Pular Avaliação
                    </button>
                  </div>
                </div>
              </div>
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

      return `
        <div class="tracking-card" id="card-${order.id}" style="margin-top: 0; margin-bottom: 24px;">
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
            <div class="map-robot" style="left: 50%; top: 90%;" title="Camaro"></div>
          </div>

          <div class="tracking-details" style="margin-top: 16px;">
            ${detailsHTML}
          </div>
        </div>
      `;
    }).join("");

    trackingContainer.innerHTML = newHTML;
    trackingContainer.setAttribute("data-rendered-ids", activeIdsStr);
  }

  clientActiveOrders.forEach(order => {
    let robotX = 50;
    let robotY = 90;

    const roomCoordinates = {
      "SALA A": { x: 24, y: 28 },
      "SALA B": { x: 24, y: 72 },
      "SALA C": { x: 76, y: 28 },
      "SALA D": { x: 76, y: 72 }
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
    } else if (order.status === "delivered") {
      robotX = 50;
      robotY = 90;
    }

    const cardEl = document.getElementById(`card-${order.id}`);
    if (cardEl) {
      const robotEl = cardEl.querySelector(".map-robot");
      if (robotEl) {
        robotEl.style.left = `${robotX}%`;
        robotEl.style.top = `${robotY}%`;
      }

      const distValEl = document.getElementById(`dist-val-${order.id}`);
      if (distValEl) {
        const txt = telemetry.distance > 0 ? `${telemetry.distance}m` : "Chegando...";
        if (distValEl.textContent !== txt) {
          distValEl.textContent = txt;
        }
      }

      const etaValEl = document.getElementById(`eta-val-${order.id}`);
      if (etaValEl) {
        const txt = telemetry.eta > 0 ? `${telemetry.eta}s` : "Entregando...";
        if (etaValEl.textContent !== txt) {
          etaValEl.textContent = txt;
        }
      }
    }
  });
}

function clearClientOrder(orderId) {
  const orders = getOrders();
  const order = orders.find(o => o.id === orderId);
  if (order) {
    order.customerUsername = order.customerUsername + "_archived";
    saveOrders(orders);
  }
  renderClientUI();
}

let selectedRatings = {};

function handleStarClick(orderId, rating) {
  selectedRatings[orderId] = rating;
  
  const section = document.getElementById(`feedback-section-${orderId}`);
  if (section) {
    const buttons = section.querySelectorAll(".star-btn");
    buttons.forEach((btn, index) => {
      if (index < rating) {
        btn.textContent = "★";
        btn.style.color = "var(--accent-color)";
      } else {
        btn.textContent = "☆";
        btn.style.color = "var(--text-muted)";
      }
    });
  }

  const commentDiv = document.getElementById(`feedback-comment-${orderId}`);
  if (commentDiv) {
    commentDiv.style.display = "block";
  }
}

async function submitFeedback(orderId) {
  const rating = selectedRatings[orderId] || 5;
  const commentInput = document.getElementById(`feedback-text-${orderId}`);
  const comment = commentInput ? commentInput.value.trim() : "";

  if (typeof apiSubmitFeedback === "function") {
    try {
      const res = await apiSubmitFeedback(orderId, rating, comment);
      if (res && res.ok) {
        alert(res.message || "Feedback enviado com sucesso!");
      }
    } catch (e) {
      console.warn("Could not submit feedback to backend:", e.message);
    }
  }

  clearClientOrder(orderId);
}

