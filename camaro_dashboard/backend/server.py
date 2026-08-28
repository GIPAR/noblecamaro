# backend/server.py
from __future__ import annotations
"""
Flask REST API for Camaro Dashboard.
Runs on http://localhost:5000
"""

import sys
import os
import json
import time
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import database as db
import llm as llm_module
from robot_bridge import start_bridge, robot_state
from room_map import ROOMS
from config import FLASK_PORT, FLASK_DEBUG

DASHBOARD_DIR = str(Path(__file__).resolve().parent.parent)

app = Flask(__name__, static_folder=DASHBOARD_DIR, static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

db.init_db()
start_bridge()  # começa a escutar o rosbridge (ROS2/Gazebo) assim que o servidor sobe

_SESSIONS_FILE = Path(__file__).parent / "sessions.json"


def _load_sessions() -> dict:
    """Load persisted sessions from disk (survives server restarts)."""
    try:
        if _SESSIONS_FILE.exists():
            return json.loads(_SESSIONS_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_sessions(sessions: dict) -> None:
    """Persist sessions to disk."""
    try:
        _SESSIONS_FILE.write_text(json.dumps(sessions))
    except Exception:
        pass


SESSIONS: dict = _load_sessions()

ROOM_DISTANCES: dict = {
    "SALA A": 3,
    "SALA C": 4,
    "SALA B": 6,
    "SALA D": 7,
}

# Mapeia o nome usado no sistema ("SALA A") para a chave usada no mundo
# Gazebo / room_map.py ("A"), onde estão as coordenadas reais dos checkpoints.
ROOM_NAME_TO_KEY = {
    "SALA A": "A",
    "SALA B": "B",
    "SALA C": "C",
    "SALA D": "D",
}


def sala_mais_proxima(x: float, y: float) -> str:
    """Retorna o nome da sala (ex: 'SALA A') cujo checkpoint está mais
    perto da posição (x, y) informada, usando as coordenadas reais
    extraídas do SDF em room_map.py."""

    def dist2(nome_sala: str) -> float:
        key = ROOM_NAME_TO_KEY[nome_sala]
        rx, ry, _yaw = ROOMS[key]
        return (rx - x) ** 2 + (ry - y) ** 2

    return min(ROOM_NAME_TO_KEY, key=dist2)


_delivery_lock = threading.Lock()
_delivery_running = False
_next_batch_group = 1


def make_token() -> str:
    return str(uuid.uuid4())


def get_session(req) -> dict | None:
    token = req.headers.get("X-Session-Token") or req.args.get("token")
    return SESSIONS.get(token)


def require_auth(req):
    session = get_session(req)
    if not session:
        return None, jsonify({"error": "Não autenticado"}), 401
    return session, None, None


@app.route("/")
def serve_index():
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    if path.startswith("api/"):
        return jsonify({"error": "Endpoint não encontrado"}), 404
    target = Path(DASHBOARD_DIR) / path
    if target.exists() and target.is_file():
        return send_from_directory(DASHBOARD_DIR, path)
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = (data or {}).get("username", "").strip()
    password = (data or {}).get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400
    user = db.authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Usuário ou senha incorretos"}), 401
    token = make_token()
    SESSIONS[token] = {"username": user["username"], "name": user["name"], "role": user["role"]}
    _save_sessions(SESSIONS)  # persist so restarts don't invalidate token
    return jsonify({"token": token, "username": user["username"], "name": user["name"], "role": user["role"]})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    token = request.headers.get("X-Session-Token")
    if token and token in SESSIONS:
        del SESSIONS[token]
        _save_sessions(SESSIONS)  # persist removal
    return jsonify({"ok": True})


@app.route("/api/products", methods=["GET"])
def list_products():
    return jsonify(db.get_products())


@app.route("/api/products/<product_id>", methods=["GET"])
def get_product(product_id):
    p = db.get_product(product_id)
    if not p:
        return jsonify({"error": "Produto não encontrado"}), 404
    return jsonify(p)


@app.route("/api/orders", methods=["GET"])
def list_orders():
    session = get_session(request)
    if not session:
        # No token / invalid token — return empty list instead of 401
        # This prevents the frontend polling loop from triggering infinite 401 cascades
        return jsonify([])
    username_filter = None if session["role"] == "admin" else session["username"]
    status_filter = request.args.get("status")
    orders = db.get_orders(username=username_filter, status=status_filter)
    return jsonify(orders)


@app.route("/api/orders", methods=["POST"])
def create_order():
    session, err, code = require_auth(request)
    if err:
        return err, code
    data = request.get_json()
    items = data.get("items", [])
    destination = data.get("destination", "SALA A")
    timing = data.get("timing", "Imediata")
    notes = data.get("notes", "")
    if not items:
        return jsonify({"error": "Nenhum item no pedido"}), 400
    try:
        order = db.create_order(
            customer_username=session["username"],
            customer_name=session["name"],
            items=items,
            destination=destination,
            timing=timing,
            notes=notes,
        )
        return jsonify(order), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@app.route("/api/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    session, err, code = require_auth(request)
    if err:
        return err, code
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
    if session["role"] != "admin" and order["customer_username"] != session["username"]:
        return jsonify({"error": "Acesso negado"}), 403
    return jsonify(order)


@app.route("/api/orders/<order_id>/status", methods=["PATCH"])
def update_order_status(order_id):
    session, err, code = require_auth(request)
    if err:
        return err, code
    if session["role"] != "admin":
        return jsonify({"error": "Apenas administradores podem alterar status"}), 403
    data = request.get_json()
    new_status = data.get("status")
    valid_statuses = ["pending", "preparing", "delivering", "delivered", "canceled"]
    if new_status not in valid_statuses:
        return jsonify({"error": f"Status inválido. Use: {valid_statuses}"}), 400
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
    db.update_order_status(order_id, new_status)
    if new_status == "preparing":
        destination = order.get("destination", "SALA A")
        db.enqueue_mission(order_id, destination, mode="single")
        _try_start_next_mission()
    return jsonify({"ok": True, "order_id": order_id, "status": new_status})


@app.route("/api/queue", methods=["GET"])
def get_queue():
    queue = db.get_full_mission_queue()
    telemetry = db.get_telemetry()
    enriched = []
    for m in queue:
        order = db.get_order(m["order_id"])
        enriched.append({
            **m,
            "summary_text": order["summary_text"] if order else "",
            "customer_name": order["customer_name"] if order else "",
        })
    return jsonify({
        "queue": enriched,
        "active_order_id": telemetry.get("current_order_id"),
        "robot_status": telemetry.get("status", "idle"),
    })


@app.route("/api/queue/confirm-all", methods=["POST"])
def confirm_all_orders():
    session, err, code = require_auth(request)
    if err:
        return err, code
    if session["role"] != "admin":
        return jsonify({"error": "Apenas administradores"}), 403
    pending = db.get_orders(status="pending")
    confirmed = []
    for order in pending:
        db.update_order_status(order["id"], "preparing")
        db.enqueue_mission(order["id"], order["destination"], mode="single")
        confirmed.append(order["id"])
    _try_start_next_mission()
    return jsonify({"ok": True, "confirmed": confirmed, "count": len(confirmed)})


@app.route("/api/queue/batch-confirm", methods=["POST"])
def batch_confirm():
    session, err, code = require_auth(request)
    if err:
        return err, code
    if session["role"] != "admin":
        return jsonify({"error": "Apenas administradores"}), 403
    data = request.get_json() or {}
    order_ids = data.get("order_ids", [])
    if len(order_ids) < 2:
        return jsonify({"error": "Rota em lote requer pelo menos 2 pedidos"}), 400

    global _next_batch_group
    batch_group = _next_batch_group
    _next_batch_group += 1

    orders_with_dist = []
    for oid in order_ids:
        order = db.get_order(oid)
        if not order:
            continue
        dist = ROOM_DISTANCES.get(order["destination"], 5)
        orders_with_dist.append((dist, order))

    orders_with_dist.sort(key=lambda x: x[0])

    confirmed = []
    for dist, order in orders_with_dist:
        db.update_order_status(order["id"], "preparing")
        db.enqueue_mission(order["id"], order["destination"], mode="batch", batch_group=batch_group)
        confirmed.append(order["id"])

    _try_start_next_mission()
    route_text = " → ".join(o["destination"] for _, o in orders_with_dist) + " → Doca Base"
    return jsonify({
        "ok": True,
        "batch_group": batch_group,
        "confirmed": confirmed,
        "route": route_text,
        "count": len(confirmed),
    })


@app.route("/api/telemetry", methods=["GET"])
def get_telemetry():
    return jsonify(db.get_telemetry())


@app.route("/api/telemetry", methods=["PATCH"])
def update_telemetry():
    session, err, code = require_auth(request)
    if err:
        return err, code
    if session["role"] != "admin":
        return jsonify({"error": "Apenas administradores"}), 403
    data = request.get_json()
    allowed = {"status", "speed", "battery", "distance", "eta", "current_order_id",
               "start_time", "delivery_end_time", "return_end_time"}
    filtered = {k: v for k, v in data.items() if k in allowed}
    db.update_telemetry(filtered)
    return jsonify({"ok": True})


@app.route("/api/robot/status", methods=["GET"])
def robot_status():
    """Posição atual real do robô (vinda do ROS2/Gazebo via rosbridge) e a
    sala mais próxima dela, calculada com as coordenadas reais do mapa."""
    x, y = robot_state["x"], robot_state["y"]
    return jsonify({
        "x": x,
        "y": y,
        "conectado": robot_state["connected"],
        "sala_mais_proxima": sala_mais_proxima(x, y),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    session = get_session(request)
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    username = session["username"] if session else data.get("username", "cliente")
    user_role = session["role"] if session else "client"
    session_id = data.get("session_id", username)
    cart = data.get("cart", [])

    if not user_message:
        return jsonify({"error": "Mensagem vazia"}), 400

    db.save_chat_message(session_id, username, "user", user_message)

    telemetry = db.get_telemetry()
    products = db.get_products()
    all_orders = db.get_orders(username=username if user_role != "admin" else None)
    active_orders = [o for o in all_orders if o["status"] not in ("canceled", "delivered")]
    pending_orders = [o for o in active_orders if o["status"] == "pending"]
    history = db.get_chat_history(session_id, limit=20)
    queue = db.get_mission_queue()

    context_data = {
        "telemetry": telemetry,
        "products": products,
        "active_orders": active_orders,
        "pending_orders": pending_orders,
        "cart": cart,
        "queue": queue,
        "user_role": user_role,
    }

    result = llm_module.process_message(user_message, history, context_data)

    executed_actions = []
    for action in result.get("actions", []):
        action_type = action.get("action") or action.get("type")

        if action_type == "add_to_cart":
            product = db.get_product(action.get("product_id", ""))
            executed_actions.append({
                "type": "add_to_cart",
                "product_id": action.get("product_id"),
                "product_name": action.get("product_name") or (product["name"] if product else "Componente"),
                "quantity": action.get("quantity", 1),
            })
            q_norm = llm_module.normalize_query(user_message)
            db.save_ai_pattern(q_norm, "add_to_cart", action.get("product_id"))

        elif action_type == "submit_order":
            executed_actions.append({
                "type": "submit_order",
                "product_id": action.get("product_id"),
                "product_name": action.get("product_name"),
                "quantity": action.get("quantity", 1),
                "destination": action.get("destination", "SALA A"),
                "timing": action.get("timing", "now"),
                "notes": action.get("notes", "Pedido via Chat AI"),
            })
            q_norm = llm_module.normalize_query(user_message)
            db.save_ai_pattern(q_norm, "submit_order", action.get("product_id"))

        elif action_type == "set_destination":
            executed_actions.append({
                "type": "set_destination",
                "destination": action.get("destination", "SALA A"),
            })

        elif action_type == "batch_route":
            order_ids = action.get("order_ids", [])
            if order_ids and len(order_ids) >= 2:
                global _next_batch_group
                batch_group = _next_batch_group
                _next_batch_group += 1
                orders_with_dist = []
                for oid in order_ids:
                    order = db.get_order(oid)
                    if order:
                        dist = ROOM_DISTANCES.get(order["destination"], 5)
                        orders_with_dist.append((dist, order))
                orders_with_dist.sort(key=lambda x: x[0])
                for dist, order in orders_with_dist:
                    db.update_order_status(order["id"], "preparing")
                    db.enqueue_mission(order["id"], order["destination"], mode="batch", batch_group=batch_group)
                _try_start_next_mission()
                route_text = " → ".join(o["destination"] for _, o in orders_with_dist) + " → Doca Base"
                executed_actions.append({"type": "batch_route", "batch_group": batch_group, "route": route_text})
            else:
                executed_actions.append({"type": "batch_route"})

        elif action_type == "confirm_all":
            pending = db.get_orders(status="pending")
            for order in pending:
                db.update_order_status(order["id"], "preparing")
                db.enqueue_mission(order["id"], order["destination"], mode="single")
            _try_start_next_mission()
            executed_actions.append({"type": "confirm_all", "count": len(pending)})

        elif action_type == "clear_cart":
            executed_actions.append({"type": "clear_cart"})
        elif action_type == "open_cart":
            executed_actions.append({"type": "open_cart"})
        elif action_type == "show_tracking":
            executed_actions.append({"type": "show_tracking"})
        elif action_type == "show_catalog":
            executed_actions.append({"type": "show_catalog"})

    db.save_chat_message(
        session_id, username, "assistant",
        result["text"],
        {"actions": executed_actions, "source": result.get("source", "fallback")}
    )

    return jsonify({
        "text": result["text"],
        "actions": executed_actions,
        "source": result.get("source", "fallback"),
    })


@app.route("/api/chat/history", methods=["GET"])
def chat_history():
    session = get_session(request)
    session_id = request.args.get("session_id") or (session["username"] if session else "cliente")
    limit = int(request.args.get("limit", 30))
    history = db.get_chat_history(session_id, limit)
    return jsonify(history)


@app.route("/api/llm/training-stats", methods=["GET"])
def training_stats():
    session, err, code = require_auth(request)
    if err:
        return err, code
    if session["role"] != "admin":
        return jsonify({"error": "Apenas administradores"}), 403
    stats = db.get_training_stats()
    patterns = db.get_top_patterns(10)
    feedback_stats = db.get_feedback_stats()
    return jsonify({**stats, "top_patterns": patterns, "feedback": feedback_stats})


@app.route("/api/orders/<order_id>/feedback", methods=["POST"])
def submit_order_feedback(order_id):
    """Client submits 1-5 star rating after confirming receipt."""
    data = request.get_json() or {}
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Rating deve ser um inteiro entre 1 e 5"}), 400

    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404

    db.save_order_feedback(order_id, rating, comment)
    return jsonify({
        "ok": True,
        "order_id": order_id,
        "rating": rating,
        "stars": "⭐" * rating,
        "message": "Obrigado pelo seu feedback! A IA utilizará esta avaliação para melhorar continuamente."
    })


@app.route("/api/llm/status", methods=["GET"])
def llm_status():
    from config import GOOGLE_API_KEY, GEMINI_MODEL
    return jsonify({
        "api_key_configured": bool(GOOGLE_API_KEY),
        "model": GEMINI_MODEL if GOOGLE_API_KEY else "rule-based-fallback",
        "mode": "gemini" if GOOGLE_API_KEY else "fallback",
    })


# ─── Delivery Simulation Engine ───────────────────────────────────────────

PREP_SECONDS = 5
TRAVEL_PER_METER = 3
RETURN_SECONDS = 15


def _distance_for(destination: str) -> int:
    return ROOM_DISTANCES.get(destination, 5)


def _travel_time(destination: str) -> int:
    return _distance_for(destination) * TRAVEL_PER_METER


def _try_start_next_mission():
    global _delivery_running
    with _delivery_lock:
        if _delivery_running:
            return
        queue = db.get_mission_queue()
        if not queue:
            return
        _delivery_running = True
    thread = threading.Thread(target=_run_delivery_engine, daemon=True)
    thread.start()


def _run_delivery_engine():
    global _delivery_running
    try:
        while True:
            queue = db.get_mission_queue()
            if not queue:
                break
            first = queue[0]
            is_batch = first.get("mode") == "batch"
            batch_group = first.get("batch_group")
            if is_batch and batch_group is not None:
                batch = [m for m in queue if m.get("batch_group") == batch_group]
                _execute_batch_route(batch)
            else:
                _execute_single_mission(first)
    finally:
        with _delivery_lock:
            _delivery_running = False
        db.update_telemetry({
            "status": "idle",
            "current_order_id": None,
            "speed": 0.0,
            "distance": 0,
            "eta": 0,
            "battery": 100.0,
        })


def _execute_single_mission(mission: dict):
    order_id = mission["order_id"]
    destination = mission["destination"]
    travel_secs = _travel_time(destination)
    distance_m = _distance_for(destination)

    db.update_mission_status(order_id, "active")
    now = int(time.time() * 1000)
    db.update_telemetry({
        "status": "preparing",
        "current_order_id": order_id,
        "speed": 0.0,
        "distance": distance_m,
        "eta": PREP_SECONDS + travel_secs,
        "start_time": now,
        "delivery_end_time": now + (PREP_SECONDS + travel_secs) * 1000,
        "return_end_time": now + (PREP_SECONDS + travel_secs + RETURN_SECONDS) * 1000,
        "battery": 98.0,
    })
    db.update_order_status(order_id, "preparing")
    time.sleep(PREP_SECONDS)

    db.update_telemetry({"status": "delivering", "speed": 1.2})
    db.update_order_status(order_id, "delivering")
    for elapsed in range(travel_secs):
        time.sleep(1)
        remaining = travel_secs - elapsed - 1
        dist = max(0, round(distance_m * remaining / travel_secs))
        battery = max(80, 98 - (elapsed * 0.3))
        db.update_telemetry({"distance": dist, "eta": remaining, "battery": battery, "speed": 1.2})

    db.update_order_status(order_id, "delivered")
    db.update_mission_status(order_id, "done")
    db.update_telemetry({"status": "returning", "speed": 1.0, "distance": distance_m, "eta": RETURN_SECONDS})

    for i in range(RETURN_SECONDS):
        time.sleep(1)
        battery = max(75, 80 - (i * 0.2))
        dist_ret = max(0, distance_m - round(distance_m * i / RETURN_SECONDS))
        db.update_telemetry({"distance": dist_ret, "eta": RETURN_SECONDS - i, "battery": battery})

    db.update_telemetry({"status": "idle", "current_order_id": None, "speed": 0.0,
                          "distance": 0, "eta": 0, "battery": 100.0})
    time.sleep(2)


def _execute_batch_route(batch: list):
    if not batch:
        return
    total_orders = len(batch)
    for idx, mission in enumerate(batch):
        order_id = mission["order_id"]
        destination = mission["destination"]
        travel_secs = _travel_time(destination)
        distance_m = _distance_for(destination)
        is_first = idx == 0
        is_last = idx == total_orders - 1

        db.update_mission_status(order_id, "active")

        if is_first:
            db.update_telemetry({
                "status": "preparing",
                "current_order_id": order_id,
                "speed": 0.0,
                "distance": distance_m,
                "eta": PREP_SECONDS + travel_secs,
                "battery": 98.0,
            })
            db.update_order_status(order_id, "preparing")
            time.sleep(PREP_SECONDS)

        db.update_telemetry({"status": "delivering", "speed": 1.2, "current_order_id": order_id})
        db.update_order_status(order_id, "delivering")
        for elapsed in range(travel_secs):
            time.sleep(1)
            remaining = travel_secs - elapsed - 1
            dist = max(0, round(distance_m * remaining / travel_secs))
            battery = max(70, 98 - ((idx * travel_secs + elapsed) * 0.25))
            db.update_telemetry({"distance": dist, "eta": remaining, "battery": battery, "speed": 1.2})

        db.update_order_status(order_id, "delivered")
        db.update_mission_status(order_id, "done")

        if not is_last:
            next_mission = batch[idx + 1]
            next_dist = _distance_for(next_mission["destination"])
            db.update_telemetry({
                "status": "delivering",
                "speed": 1.0,
                "distance": next_dist,
                "eta": _travel_time(next_mission["destination"]),
            })
            time.sleep(2)

    last_dist = _distance_for(batch[-1]["destination"])
    db.update_telemetry({"status": "returning", "speed": 1.0, "distance": last_dist, "eta": RETURN_SECONDS})
    for i in range(RETURN_SECONDS):
        time.sleep(1)
        battery = max(70, 75 - (i * 0.2))
        dist_ret = max(0, last_dist - round(last_dist * i / RETURN_SECONDS))
        db.update_telemetry({"distance": dist_ret, "eta": RETURN_SECONDS - i, "battery": battery})

    db.update_telemetry({"status": "idle", "current_order_id": None, "speed": 0.0,
                          "distance": 0, "eta": 0, "battery": 100.0})
    time.sleep(2)


if __name__ == "__main__":
    print(f"[Camaro Backend] Starting on http://localhost:{FLASK_PORT}")
    print(f"[Camaro Backend] Serving static files from: {Path(__file__).parent.parent}")
    from config import GOOGLE_API_KEY, GEMINI_MODEL
    if GOOGLE_API_KEY:
        print(f"[LLM] Using Gemini model: {GEMINI_MODEL}")
    else:
        print("[LLM] No API key found — using smart rule-based fallback")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True)