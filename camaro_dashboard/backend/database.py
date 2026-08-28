# backend/database.py
from __future__ import annotations
"""
SQLite database layer for Camaro Dashboard.
Handles schema creation, seeding, and all CRUD operations.
"""

import sqlite3
import hashlib
import uuid
import json
from datetime import datetime, timezone
try:
    from backend.config import DB_PATH, DEFAULT_USERS, DEFAULT_PRODUCTS
except ImportError:
    from config import DB_PATH, DEFAULT_USERS, DEFAULT_PRODUCTS


# ─── Helpers ───────────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Schema ────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'client',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    stock       INTEGER NOT NULL DEFAULT 0,
    image       TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT 'componente'
);

CREATE TABLE IF NOT EXISTS orders (
    id                  TEXT PRIMARY KEY,
    customer_username   TEXT NOT NULL,
    customer_name       TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    destination         TEXT NOT NULL DEFAULT 'SALA A',
    timing              TEXT NOT NULL DEFAULT 'Imediata',
    notes               TEXT NOT NULL DEFAULT '',
    summary_text        TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (customer_username) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        TEXT NOT NULL,
    product_id      TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    username    TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    status          TEXT NOT NULL DEFAULT 'idle',
    current_order_id TEXT,
    speed           REAL NOT NULL DEFAULT 0.0,
    battery         REAL NOT NULL DEFAULT 100.0,
    distance        INTEGER NOT NULL DEFAULT 0,
    eta             INTEGER NOT NULL DEFAULT 0,
    start_time      INTEGER NOT NULL DEFAULT 0,
    delivery_end_time INTEGER NOT NULL DEFAULT 0,
    return_end_time INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_username);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_username ON chat_history(username);

CREATE TABLE IF NOT EXISTS ai_patterns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query_norm  TEXT NOT NULL,
    action_type TEXT NOT NULL,
    product_id  TEXT,
    frequency   INTEGER NOT NULL DEFAULT 1,
    last_seen   TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_patterns_unique ON ai_patterns(query_norm, action_type, COALESCE(product_id, ''));

CREATE TABLE IF NOT EXISTS mission_queue (
    position    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    TEXT NOT NULL UNIQUE,
    destination TEXT NOT NULL DEFAULT 'SALA A',
    mode        TEXT NOT NULL DEFAULT 'single',
    batch_group INTEGER,
    status      TEXT NOT NULL DEFAULT 'queued',
    enqueued_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mission_queue_status ON mission_queue(status);
"""


def init_db():
    """Create tables and seed initial data."""
    conn = get_connection()
    conn.executescript(SCHEMA)

    # Seed users
    for u in DEFAULT_USERS:
        existing = conn.execute("SELECT id FROM users WHERE username=?", (u["username"],)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO users (id, username, password, name, role, created_at) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), u["username"], hash_password(u["password"]), u["name"], u["role"], now_iso())
            )

    # Seed products
    for p in DEFAULT_PRODUCTS:
        existing = conn.execute("SELECT id FROM products WHERE id=?", (p["id"],)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO products (id, name, description, stock, image, category) VALUES (?,?,?,?,?,?)",
                (p["id"], p["name"], p["description"], p["stock"], p["image"], p["category"])
            )

    # Seed telemetry row (singleton)
    existing = conn.execute("SELECT id FROM telemetry WHERE id=1").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO telemetry (id, status, current_order_id, speed, battery, distance, eta, start_time, delivery_end_time, return_end_time, updated_at) "
            "VALUES (1,'idle',NULL,0.0,100.0,0,0,0,0,0,?)",
            (now_iso(),)
        )

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ─── User Operations ───────────────────────────────────────────────────────

def get_user(username: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def authenticate_user(username: str, password: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Product Operations ────────────────────────────────────────────────────

def get_products():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_product_stock(product_id: str, delta: int):
    """Atomically add delta to stock (negative = deduct)."""
    conn = get_connection()
    conn.execute("UPDATE products SET stock = stock + ? WHERE id=?", (delta, product_id))
    conn.commit()
    conn.close()


def save_products(products: list):
    """Bulk-save products list (used for admin edits)."""
    conn = get_connection()
    for p in products:
        conn.execute(
            "UPDATE products SET name=?, description=?, stock=?, image=?, category=? WHERE id=?",
            (p["name"], p["description"], p["stock"], p["image"], p.get("category", "componente"), p["id"])
        )
    conn.commit()
    conn.close()


# ─── Order Operations ──────────────────────────────────────────────────────

def get_orders(username: str = None, status: str = None):
    conn = get_connection()
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    if username:
        query += " AND customer_username=?"
        params.append(username)
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    orders = []
    for r in rows:
        order = dict(r)
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id=?", (order["id"],)
        ).fetchall()
        order["items"] = [dict(i) for i in items]
        orders.append(order)
    conn.close()
    return orders


def get_order(order_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row:
        conn.close()
        return None
    order = dict(row)
    items = conn.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
    order["items"] = [dict(i) for i in items]
    conn.close()
    return order


def create_order(customer_username: str, customer_name: str, items: list,
                 destination: str, timing: str, notes: str) -> dict:
    """Create an order and deduct stock. Returns the created order dict."""
    conn = get_connection()

    # Check stock
    for item in items:
        row = conn.execute("SELECT stock FROM products WHERE id=?", (item["productId"],)).fetchone()
        if not row or row["stock"] < item["quantity"]:
            conn.close()
            raise ValueError(f"Estoque insuficiente para: {item.get('productName', item['productId'])}")

    order_id = "ord_" + str(uuid.uuid4())[:8].upper()
    summary_text = ", ".join(f"{it['quantity']}x {it['productName']}" for it in items)
    summary_text += f" [Destino: {destination}]"
    ts = now_iso()

    conn.execute(
        "INSERT INTO orders (id, customer_username, customer_name, status, destination, timing, notes, summary_text, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (order_id, customer_username, customer_name, "pending", destination, timing, notes, summary_text, ts, ts)
    )

    for item in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, quantity) VALUES (?,?,?,?)",
            (order_id, item["productId"], item["productName"], item["quantity"])
        )
        # Deduct stock
        conn.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item["quantity"], item["productId"]))

    conn.commit()

    order = dict(conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone())
    items_rows = conn.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
    order["items"] = [dict(i) for i in items_rows]
    conn.close()
    return order


def update_order_status(order_id: str, new_status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status=?, updated_at=? WHERE id=?",
        (new_status, now_iso(), order_id)
    )
    conn.commit()
    conn.close()


# ─── Chat History ──────────────────────────────────────────────────────────

def save_chat_message(session_id: str, username: str, role: str, content: str, metadata: dict = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (session_id, username, role, content, metadata, created_at) VALUES (?,?,?,?,?,?)",
        (session_id, username, role, content, json.dumps(metadata or {}), now_iso())
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id: str, limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content, metadata, created_at FROM chat_history WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_all_chat_history(username: str, limit: int = 50) -> list:
    """Get all messages for a user across sessions (for training context)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content, metadata, created_at FROM chat_history WHERE username=? ORDER BY created_at DESC LIMIT ?",
        (username, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_training_stats() -> dict:
    conn = get_connection()
    total_msgs = conn.execute("SELECT COUNT(*) as c FROM chat_history").fetchone()["c"]
    total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) as c FROM chat_history").fetchone()["c"]
    total_users = conn.execute("SELECT COUNT(DISTINCT username) as c FROM chat_history").fetchone()["c"]
    top_queries = conn.execute(
        "SELECT content, COUNT(*) as c FROM chat_history WHERE role='user' GROUP BY content ORDER BY c DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return {
        "total_messages": total_msgs,
        "total_sessions": total_sessions,
        "total_users": total_users,
        "top_queries": [dict(r) for r in top_queries],
    }


# ─── Telemetry ─────────────────────────────────────────────────────────────

def get_telemetry() -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM telemetry WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else {}


def update_telemetry(data: dict):
    conn = get_connection()
    data["updated_at"] = now_iso()
    sets = ", ".join(f"{k}=?" for k in data.keys())
    vals = list(data.values()) + [1]
    conn.execute(f"UPDATE telemetry SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


# ─── AI Patterns (Continuous Learning) ────────────────────────────────────

def save_ai_pattern(query_norm: str, action_type: str, product_id: str = None):
    """Upsert a learned pattern: increment frequency or insert new."""
    conn = get_connection()
    product_id = product_id or ""
    existing = conn.execute(
        "SELECT id, frequency FROM ai_patterns WHERE query_norm=? AND action_type=? AND COALESCE(product_id,'')=?",
        (query_norm, action_type, product_id)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE ai_patterns SET frequency=?, last_seen=? WHERE id=?",
            (existing["frequency"] + 1, now_iso(), existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO ai_patterns (query_norm, action_type, product_id, frequency, last_seen) VALUES (?,?,?,1,?)",
            (query_norm, action_type, product_id or None, now_iso())
        )
    conn.commit()
    conn.close()


def get_top_patterns(limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT query_norm, action_type, product_id, frequency, last_seen FROM ai_patterns ORDER BY frequency DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_learned_pattern(query_norm: str) -> dict | None:
    """Return the best learned action for a normalized query, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT action_type, product_id, frequency FROM ai_patterns WHERE query_norm=? ORDER BY frequency DESC LIMIT 1",
        (query_norm,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Mission Queue ─────────────────────────────────────────────────────────

def enqueue_mission(order_id: str, destination: str, mode: str = "single", batch_group: int = None):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO mission_queue (order_id, destination, mode, batch_group, status, enqueued_at) VALUES (?,?,?,?,?,?)",
        (order_id, destination, mode, batch_group, "queued", now_iso())
    )
    conn.commit()
    conn.close()


def get_mission_queue() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mission_queue WHERE status='queued' ORDER BY position ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_full_mission_queue() -> list:
    """All missions including active and completed (last 20)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mission_queue ORDER BY position DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def update_mission_status(order_id: str, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE mission_queue SET status=? WHERE order_id=?",
        (status, order_id)
    )
    conn.commit()
    conn.close()


def get_queue_position(order_id: str) -> int:
    """Return 1-based position of an order in the queued missions."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT order_id FROM mission_queue WHERE status='queued' ORDER BY position ASC"
    ).fetchall()
    conn.close()
    for i, r in enumerate(rows):
        if r["order_id"] == order_id:
            return i + 1
    return 0


def set_batch_group(order_ids: list, batch_group: int):
    """Assign a batch group number to a set of missions."""
    conn = get_connection()
    for oid in order_ids:
        conn.execute(
            "UPDATE mission_queue SET mode='batch', batch_group=? WHERE order_id=?",
            (batch_group, oid)
        )
    conn.commit()
    conn.close()


# ─── Order Feedback ──────────────────────────────────────────────────────────

def save_order_feedback(order_id: str, rating: int, comment: str = "") -> None:
    """Save client feedback for a delivered order (1–5 stars)."""
    conn = get_connection()
    # Ensure table exists (backward compatible migration)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    TEXT NOT NULL UNIQUE,
            rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment     TEXT DEFAULT '',
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO order_feedback (order_id, rating, comment, created_at) VALUES (?,?,?,?)",
        (order_id, rating, comment, now_iso())
    )
    # Also record as an AI pattern so negative feedback can be tracked
    avg_rating = conn.execute(
        "SELECT AVG(rating) FROM order_feedback"
    ).fetchone()[0] or 5.0
    conn.execute(
        """INSERT INTO ai_patterns (query_norm, action_type, product_id, frequency, last_seen)
           VALUES (?, 'delivery_feedback', NULL, ?, ?)
           ON CONFLICT(query_norm, action_type, COALESCE(product_id,''))
           DO UPDATE SET frequency=excluded.frequency, last_seen=excluded.last_seen""",
        (f"feedback_{rating}star", rating, now_iso())
    )
    conn.commit()
    conn.close()


def get_feedback_stats() -> dict:
    """Return aggregated feedback statistics for LLM context."""
    conn = get_connection()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS order_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL UNIQUE, rating INTEGER NOT NULL, comment TEXT DEFAULT '', created_at TEXT NOT NULL)")
        row = conn.execute(
            "SELECT COUNT(*), AVG(rating), MIN(rating), MAX(rating) FROM order_feedback"
        ).fetchone()
        low_feedback = conn.execute(
            "SELECT order_id, rating, comment FROM order_feedback WHERE rating <= 2 ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        recent = conn.execute(
            "SELECT order_id, rating, comment, created_at FROM order_feedback ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
    except Exception:
        conn.close()
        return {"total": 0, "avg_rating": 0, "min": 0, "max": 0, "low_feedback": [], "recent": []}
    conn.close()
    return {
        "total": row[0] or 0,
        "avg_rating": round(row[1] or 0, 2),
        "min_rating": row[2] or 0,
        "max_rating": row[3] or 0,
        "low_feedback": [dict(r) for r in low_feedback],
        "recent": [dict(r) for r in recent],
    }
