/* app.js */

document.addEventListener("DOMContentLoaded", () => {
  // Setup routing and UI
  checkAuth();
  
  // Login / Register Form submission handling
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", handleRegister);
  }

  // Handle portal tab toggles
  const tabButtons = document.querySelectorAll(".portal-tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      
      const mode = btn.dataset.tab; // "login" or "register"
      if (mode === "login") {
        document.getElementById("login-form-container").style.display = "block";
        document.getElementById("register-form-container").style.display = "none";
      } else {
        document.getElementById("login-form-container").style.display = "none";
        document.getElementById("register-form-container").style.display = "block";
      }
    });
  });

  // Handle logouts
  const logoutButtons = document.querySelectorAll(".btn-logout");
  logoutButtons.forEach(btn => {
    btn.addEventListener("click", logout);
  });

  // Handle storage syncing across tabs
  window.addEventListener("storage", (e) => {
    // If telemetry or orders change in another tab, update current dashboards
    if (e.key === "camaro_telemetry" || e.key === "camaro_orders") {
      syncUI();
    }
  });

  // Start telemetry simulation poll loop
  setInterval(async () => {
    if (typeof syncWithBackend === "function") {
      try {
        await syncWithBackend();
      } catch (e) {
        // Backend offline: run client-side simulation only if still logged in
        if (getCurrentUser()) {
          updateSimulation();
        }
      }
    } else {
      if (getCurrentUser()) {
        updateSimulation();
      }
    }
    // Only update UI if user is still logged in (not cleared by 401 handler)
    if (getCurrentUser()) {
      syncUI();
    }
  }, 1000);
});

async function checkAuth() {
  const user = getCurrentUser();
  const sections = document.querySelectorAll(".view-section");
  sections.forEach(s => s.classList.remove("active"));

  if (!user) {
    document.getElementById("portal-view").classList.add("active");
    return;
  }

  // If we have a local session but NO backend token, try to re-authenticate silently
  // This happens when the server restarts and loses its in-memory session
  const token = getToken();
  if (!token && typeof apiLogin === "function") {
    try {
      // Re-use credentials stored in localStorage users list
      const users = getUsers();
      const localUser = users.find(u => u.username === user.username);
      if (localUser) {
        await apiLogin(localUser.username, localUser.password);
      }
    } catch (err) {
      console.warn("Silent re-auth failed (backend offline?):", err.message);
    }
  }

  // Set user profile info
  const profileNames = document.querySelectorAll(".user-name-display");
  profileNames.forEach(span => {
    span.textContent = user.name || user.username;
  });

  if (user.role === "admin") {
    document.getElementById("admin-view").classList.add("active");
    if (typeof initAdminDashboard === "function") {
      initAdminDashboard();
    }
  } else {
    document.getElementById("client-view").classList.add("active");
    if (typeof initClientDashboard === "function") {
      initClientDashboard();
    }
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const usernameField = document.getElementById("login-username");
  const passwordField = document.getElementById("login-password");
  
  if (!usernameField || !passwordField) return;

  const username = usernameField.value.trim().toLowerCase();
  const password = passwordField.value;

  const users = getUsers();
  const user = users.find(u => u.username === username && u.password === password);

  if (user) {
    setCurrentUser(user);
    // Await apiLogin so the token is saved in localStorage BEFORE the first sync tick
    if (typeof apiLogin === "function") {
      try {
        await apiLogin(username, password);
      } catch (err) {
        // Backend offline — continue with local-only mode
        console.warn("Backend login failed, running offline:", err.message);
      }
    }
    // Clean fields
    usernameField.value = "";
    passwordField.value = "";
    document.getElementById("login-error").textContent = "";
    checkAuth();
  } else {
    document.getElementById("login-error").textContent = "Usuário ou senha inválidos.";
  }
}

function handleRegister(e) {
  e.preventDefault();
  const nameField = document.getElementById("reg-name");
  const usernameField = document.getElementById("reg-username");
  const passwordField = document.getElementById("reg-password");
  const roleSelect = document.getElementById("reg-role");

  if (!nameField || !usernameField || !passwordField || !roleSelect) return;

  const name = nameField.value.trim();
  const username = usernameField.value.trim().toLowerCase();
  const password = passwordField.value;
  const role = roleSelect.value;

  const users = getUsers();
  const exists = users.some(u => u.username === username);

  if (exists) {
    document.getElementById("register-error").textContent = "Nome de usuário já existe.";
    return;
  }

  // Create and save new user
  const newUser = { name, username, password, role };
  users.push(newUser);
  saveUsers(users);

  // Set message and switch to login tab
  document.getElementById("register-error").style.color = "var(--status-delivered)";
  document.getElementById("register-error").textContent = "Conta criada com sucesso! Faça login.";
  
  // Reset fields
  nameField.value = "";
  usernameField.value = "";
  passwordField.value = "";
  
  // Auto switch back to login tab after 1.5 seconds
  setTimeout(() => {
    document.getElementById("register-error").textContent = "";
    document.getElementById("register-error").style.color = "var(--status-error)";
    const loginTabBtn = document.querySelector(".portal-tab-btn[data-tab='login']");
    if (loginTabBtn) loginTabBtn.click();
  }, 1500);
}

function logout() {
  setCurrentUser(null);
  checkAuth();
}

// Sync UI states
function syncUI() {
  const user = getCurrentUser();
  if (!user) return;

  if (user.role === "admin") {
    if (typeof renderAdminUI === "function") {
      renderAdminUI();
    }
  } else {
    if (typeof renderClientUI === "function") {
      renderClientUI();
    }
  }
}
