# backend/config.py
import os

# ─── Gemini API ────────────────────────────────────────────────────────────
# Coloque sua chave aqui ou defina a variável de ambiente GOOGLE_API_KEY
# Chave gratuita: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# Modelo Gemini a usar
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# ─── Servidor ──────────────────────────────────────────────────────────────
FLASK_PORT = 5000
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# ─── Banco de dados ────────────────────────────────────────────────────────
import pathlib
BASE_DIR = pathlib.Path(__file__).parent
DB_PATH = str(BASE_DIR / "camaro.db")

# ─── Usuários padrão (seed inicial) ───────────────────────────────────────
DEFAULT_USERS = [
    {"username": "admin", "password": "123", "name": "Administrador", "role": "admin"},
    {"username": "cliente", "password": "123", "name": "Cliente Demo", "role": "client"},
]

# ─── Produtos padrão (seed inicial) ───────────────────────────────────────
DEFAULT_PRODUCTS = [
    {
        "id": "esp32",
        "name": "ESP32 DevKit",
        "description": "Microcontrolador dual-core 240MHz com Wi-Fi e Bluetooth integrados.",
        "stock": 15,
        "image": "assets/product_esp32.jpg",
        "category": "microcontrolador",
    },
    {
        "id": "sensor_us",
        "name": "Sensor Ultrassônico HC-SR04",
        "description": "Sensor de distância por ultrassom, alcance 2cm a 4m.",
        "stock": 20,
        "image": "assets/product_sensor.jpg",
        "category": "sensor",
    },
    {
        "id": "relay",
        "name": "Módulo Relé 5V",
        "description": "Módulo relé de 1 canal para controle de cargas de até 250VAC / 10A.",
        "stock": 30,
        "image": "assets/product_relay.jpg",
        "category": "atuador",
    },
]
