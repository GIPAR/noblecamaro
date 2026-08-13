/* state.js */

const DEFAULT_PRODUCTS = [
  {
    id: "p1",
    name: "ESP32 DevKit v4 Microcontrolador",
    stock: 15,
    description: "Módulo ESP32-WROOM-32 com Wi-Fi + Bluetooth, pinos soldados, CP2102. Ideal para prototipagem de IoT.",
    image: "assets/product_esp32.jpg"
  },
  {
    id: "p2",
    name: "Sensor de Distância Ultrassônico HC-SR04",
    stock: 24,
    description: "Sensor de distância por ultrassom para projetos eletrônicos. Faixa de detecção de 2cm a 400cm.",
    image: "assets/product_sensor.jpg"
  },
  {
    id: "p3",
    name: "Módulo Relé 5V de 2 Canais",
    stock: 10,
    description: "Módulo de acionamento relé com isolamento por optoacoplador, ideal para controle de cargas AC de alta tensão.",
    image: "assets/product_relay.jpg"
  }
];

const DEFAULT_TELEMETRY = {
  battery: 100,
  status: "idle", // idle, preparing, delivering, returning, charging
  currentOrderId: null,
  speed: 0, // km/h
  distance: 0, // meters
  eta: 0, // seconds
  startTime: null,
  deliveryEndTime: null,
  returnEndTime: null,
  history: [
    { id: "h1", customer: "Alice Silva", product: "ESP32 DevKit v4 (x2)", date: "Hoje, 14:20", status: "delivered", distance: 420 },
    { id: "h2", customer: "Carlos Souza", product: "Sensor de Distância Ultrassônico (x1)", date: "Hoje, 11:05", status: "delivered", distance: 310 }
  ]
};

// Initialize app state in localStorage if not present
function initializeState() {
  if (!localStorage.getItem("camaro_users")) {
    const defaultUsers = [
      { username: "admin", password: "123", role: "admin", name: "Administrador Camaro" },
      { username: "cliente", password: "123", role: "client", name: "Cliente VIP" }
    ];
    localStorage.setItem("camaro_users", JSON.stringify(defaultUsers));
  }

  const existingProducts = localStorage.getItem("camaro_products");
  if (!existingProducts || existingProducts.includes("Café Gourmet") || !existingProducts.includes("stock")) {
    localStorage.setItem("camaro_products", JSON.stringify(DEFAULT_PRODUCTS));
  }

  if (!localStorage.getItem("camaro_orders")) {
    localStorage.setItem("camaro_orders", JSON.stringify([]));
  }

  if (!localStorage.getItem("camaro_telemetry")) {
    localStorage.setItem("camaro_telemetry", JSON.stringify(DEFAULT_TELEMETRY));
  }
}


// Getters and Setters
function getUsers() {
  return JSON.parse(localStorage.getItem("camaro_users")) || [];
}

function saveUsers(users) {
  localStorage.setItem("camaro_users", JSON.stringify(users));
}

function getProducts() {
  return JSON.parse(localStorage.getItem("camaro_products")) || [];
}

function saveProducts(products) {
  localStorage.setItem("camaro_products", JSON.stringify(products));
}

function getOrders() {
  return JSON.parse(localStorage.getItem("camaro_orders")) || [];
}

function saveOrders(orders) {
  localStorage.setItem("camaro_orders", JSON.stringify(orders));
}

function getTelemetry() {
  return JSON.parse(localStorage.getItem("camaro_telemetry")) || DEFAULT_TELEMETRY;
}

function saveTelemetry(telemetry) {
  localStorage.setItem("camaro_telemetry", JSON.stringify(telemetry));
}

function getCurrentUser() {
  return JSON.parse(sessionStorage.getItem("camaro_current_user")) || null;
}

function setCurrentUser(user) {
  if (user) {
    sessionStorage.setItem("camaro_current_user", JSON.stringify(user));
  } else {
    sessionStorage.removeItem("camaro_current_user");
  }
}

// Update simulation telemetry based on timestamps
function updateSimulation() {
  const telemetry = getTelemetry();
  if (!telemetry.currentOrderId) {
    // If charging, simulate battery gain
    if (telemetry.status === "charging") {
      if (telemetry.battery < 100) {
        telemetry.battery = Math.min(100, telemetry.battery + 0.5);
      } else {
        telemetry.status = "idle";
        telemetry.speed = 0;
      }
      saveTelemetry(telemetry);
    }
    return telemetry;
  }

  const now = Date.now();
  const orders = getOrders();
  const currentOrder = orders.find(o => o.id === telemetry.currentOrderId);

  if (!currentOrder) {
    // Clean up if order is missing
    telemetry.currentOrderId = null;
    telemetry.status = "idle";
    telemetry.speed = 0;
    telemetry.distance = 0;
    telemetry.eta = 0;
    saveTelemetry(telemetry);
    return telemetry;
  }

  // Delivery simulation times:
  // - "preparing": from start to startTime + 3s
  // - "delivering": from startTime + 3s to deliveryEndTime
  // - "returning": from deliveryEndTime to returnEndTime

  const prepTime = telemetry.startTime + 3000;

  if (now < prepTime) {
    // 1. Preparing state
    telemetry.status = "preparing";
    telemetry.speed = 0;
    telemetry.distance = 450; // Distance to delivery waypoint
    telemetry.eta = Math.max(1, Math.round((telemetry.deliveryEndTime - now) / 1000));
    
    if (currentOrder.status !== "preparing") {
      currentOrder.status = "preparing";
      saveOrders(orders);
    }
  } else if (now < telemetry.deliveryEndTime) {
    // 2. Out for delivery (A caminho)
    telemetry.status = "delivering";
    telemetry.speed = 12.5; // Simulated speed (e.g. 12.5 km/h)
    
    // Linearly interpolate distance from 450m to 0m
    const totalDeliveryDuration = telemetry.deliveryEndTime - prepTime;
    const elapsedDelivery = now - prepTime;
    const progress = elapsedDelivery / totalDeliveryDuration;
    telemetry.distance = Math.max(0, Math.round(450 * (1 - progress)));
    
    // Simulate battery drainage during delivery
    telemetry.battery = Math.max(10, 95 - (progress * 8)); // drops from 95% to 87%
    
    telemetry.eta = Math.max(1, Math.round((telemetry.deliveryEndTime - now) / 1000));

    if (currentOrder.status !== "delivering") {
      currentOrder.status = "delivering";
      saveOrders(orders);
    }
  } else if (now < telemetry.returnEndTime) {
    // 3. Returning state (Retornando à base)
    if (currentOrder.status !== "delivered") {
      currentOrder.status = "delivered";
      saveOrders(orders);
      
      // Add delivery to history
      const formattedDate = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      telemetry.history.unshift({
        id: "h_" + now,
        customer: currentOrder.customerName,
        product: currentOrder.summaryText || currentOrder.productName,
        date: `Hoje, ${formattedDate}`,
        status: "delivered",
        distance: 450
      });
      // Cap history at 10 items
      if (telemetry.history.length > 10) {
        telemetry.history.pop();
      }
    }
    
    telemetry.status = "returning";
    telemetry.speed = 15.0; // returns slightly faster empty
    
    // Linearly interpolate distance from 0m back to 450m
    const totalReturnDuration = telemetry.returnEndTime - telemetry.deliveryEndTime;
    const elapsedReturn = now - telemetry.deliveryEndTime;
    const progress = elapsedReturn / totalReturnDuration;
    telemetry.distance = Math.min(450, Math.round(450 * progress));
    
    // Simulate battery drainage during return
    telemetry.battery = Math.max(10, 87 - (progress * 5)); // drops from 87% to 82%
    telemetry.eta = Math.max(1, Math.round((telemetry.returnEndTime - now) / 1000));
  } else {
    // 4. Mission finished, returning to dock
    telemetry.status = "charging";
    telemetry.speed = 0;
    telemetry.distance = 0;
    telemetry.eta = 0;
    telemetry.currentOrderId = null;
  }

  saveTelemetry(telemetry);
  return telemetry;
}

// Global initialization
initializeState();
