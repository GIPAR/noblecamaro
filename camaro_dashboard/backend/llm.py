# backend/llm.py
from __future__ import annotations
"""
LLM Orchestrator — Gemini via REST API & Smart Rule-Based Engine.
Acts as the delivery coordinator for the Camaro autonomous robot.
"""

import json
import re
import requests
try:
    from backend.config import GOOGLE_API_KEY, GEMINI_API_URL
    import backend.database as db
except ImportError:
    from config import GOOGLE_API_KEY, GEMINI_API_URL
    import database as db


# ─── System Prompt ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é o orquestrador de IA do robô de entrega autônomo **Camaro**, operando em laboratório de robótica.

## Responsabilidades
1. Responder perguntas sobre status, localização, velocidade, ETA e bateria do robô.
2. Processar pedidos via chat: detectar componentes (ESP32, Sensor Ultrassônico, Módulo Relé), quantidades e destinos.
3. Suportar múltiplos componentes no mesmo pedido (ex: "2 ESP32 e 1 relé").
4. Controlar a interface: abrir carrinho, limpar, escolher sala, confirmar pedido, ir para mapa.
5. Para o admin: confirmar todos os pedidos, sugerir rota em lote quando há múltiplos pedidos pendentes.
6. Reportar telemetria em linguagem humana.

## Ações Disponíveis
Use tags <ACTION>{...}</ACTION> NO INÍCIO da resposta.

1. Adicionar ao carrinho (pode ter múltiplas ações para múltiplos produtos):
<ACTION>{"action":"add_to_cart","product_id":"<ID>","product_name":"<NOME>","quantity":<QTD>}</ACTION>

2. Escolher sala de destino:
<ACTION>{"action":"set_destination","destination":"<SALA A|SALA B|SALA C|SALA D>"}</ACTION>

3. Submeter pedido completo (usa o carrinho atual, não precisa de product_id se já tiver itens no carrinho):
<ACTION>{"action":"submit_order","destination":"<SALA>","timing":"now","notes":""}</ACTION>

4. Abrir modal do carrinho:
<ACTION>{"action":"open_cart"}</ACTION>

5. Limpar carrinho:
<ACTION>{"action":"clear_cart"}</ACTION>

6. Mostrar mapa/acompanhamento:
<ACTION>{"action":"show_tracking"}</ACTION>

7. Mostrar catálogo:
<ACTION>{"action":"show_catalog"}</ACTION>

8. [ADMIN ONLY] Confirmar todos os pedidos pendentes (modo individual):
<ACTION>{"action":"confirm_all"}</ACTION>

9. [ADMIN ONLY] Autorizar rota em lote (somente quando IA sugeriu):
<ACTION>{"action":"batch_route","order_ids":["<ID1>","<ID2>"]}</ACTION>

IDs disponíveis: esp32, sensor_us, relay

## Regra importante sobre rota em lote
Você SÓ deve sugerir rota em lote e pedir autorização ao admin quando:
- Há 2 ou mais pedidos pending com destinos DIFERENTES
- O usuário é admin
Nunca execute batch_route sem que o admin confirme explicitamente.
"""


# ─── Query Normalizer ──────────────────────────────────────────────────────

def normalize_query(text: str) -> str:
    """Normalize a query for pattern matching/learning."""
    q = text.lower().strip()
    q = re.sub(r'\d+', 'N', q)
    q = re.sub(r'\s+', ' ', q)
    q = re.sub(r'[^\w\s]', '', q)
    return q[:80]


# ─── Helpers for Rule-Based NLP Matching ───────────────────────────────────

def find_all_products_in_text(text: str, products: list) -> list:
    """Find ALL products mentioned in the text and their quantities."""
    q = text.lower()
    found = []

    product_patterns = {
        "esp32": ["esp32", "esp 32", "microcontrolador", "devkit", "esp"],
        "sensor_us": ["sensor", "ultrassonico", "ultrassônico", "hc-sr04", "hcsr04", "distancia", "distância"],
        "relay": ["rele", "relé", "relay", "modulo rele", "módulo relé"],
    }

    # Split by "e", "mais", "com", ",", "+" to detect multiple items
    # Try to find quantities per segment
    segments = re.split(r'\b(e|mais|com|,|\+)\b', q)

    matched_ids = set()
    for segment in segments:
        segment = segment.strip()
        if not segment or segment in ('e', 'mais', 'com', ',', '+'):
            continue
        for p in products:
            pid = p["id"].lower()
            if pid in matched_ids:
                continue
            keywords = product_patterns.get(pid, [p["name"].lower()])
            if any(k in segment for k in keywords):
                qty = extract_quantity(segment)
                matched_ids.add(pid)
                found.append({
                    "product": p,
                    "quantity": min(qty, p["stock"]) if p["stock"] > 0 else 0
                })

    # Fallback: search entire text if nothing found in segments
    if not found:
        for p in products:
            pid = p["id"].lower()
            keywords = product_patterns.get(pid, [p["name"].lower()])
            if any(k in q for k in keywords):
                qty = extract_quantity(q)
                found.append({
                    "product": p,
                    "quantity": min(qty, p["stock"]) if p["stock"] > 0 else 0
                })

    return found


def find_product_in_text(text: str, products: list) -> dict | None:
    """Find first product mentioned in text (legacy helper)."""
    results = find_all_products_in_text(text, products)
    return results[0]["product"] if results else None


def extract_quantity(text: str) -> int:
    q = text.lower()
    match = re.search(r'(\d+)\s*(?:x|unidades?|peças?|pecas?|pcs?)?', q)
    if match:
        val = int(match.group(1))
        if val > 0:
            return val
    word_map = {
        "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3,
        "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10
    }
    for word, num in word_map.items():
        if re.search(r'\b' + word + r'\b', q):
            return num
    return 1


def extract_room(text: str) -> str | None:
    q = text.lower()
    if any(k in q for k in ["sala a", "sala 1", "sala-a", "lab a"]):
        return "SALA A"
    if any(k in q for k in ["sala b", "sala 2", "sala-b", "lab b"]):
        return "SALA B"
    if any(k in q for k in ["sala c", "sala 3", "sala-c", "lab c"]):
        return "SALA C"
    if any(k in q for k in ["sala d", "sala 4", "sala-d", "lab d"]):
        return "SALA D"
    return None


# ─── Batch Suggestion Builder ──────────────────────────────────────────────

ROOM_DISTANCES = {"SALA A": 3, "SALA C": 4, "SALA B": 6, "SALA D": 7}


def _build_batch_suggestion(pending_orders: list) -> str | None:
    """Return a proactive batch suggestion message if conditions are met."""
    if len(pending_orders) < 2:
        return None
    destinations = [o.get("destination", "") for o in pending_orders]
    unique_dests = list(dict.fromkeys(destinations))
    if len(unique_dests) < 2:
        return None
    # Sort by distance
    sorted_dests = sorted(unique_dests, key=lambda d: ROOM_DISTANCES.get(d, 5))
    single_time = sum(ROOM_DISTANCES.get(d, 5) * 3 * 2 for d in unique_dests)  # travel + return each
    batch_time = sum(ROOM_DISTANCES.get(d, 5) * 3 for d in unique_dests) + 15  # travel all + one return
    savings = max(0, round((1 - batch_time / single_time) * 100))
    route = " → ".join(sorted_dests) + " → Doca Base"
    ids_str = ", ".join(f"'{o['id']}'" for o in pending_orders)
    return (
        f"⚡ **Sugestão de Rota Otimizada** — Detectei {len(pending_orders)} pedidos pendentes "
        f"em destinos diferentes ({', '.join(sorted_dests)}).\n\n"
        f"Posso fazer a entrega em lote numa única rota: **{route}** "
        f"sem voltar à base entre as paradas. Isso economiza aproximadamente **{savings}% do tempo** "
        f"em relação a {len(pending_orders)} missões individuais.\n\n"
        f"Deseja autorizar a rota em lote? Responda **'sim, autorizar lote'** ou clique em **'Autorizar Rota em Lote'**."
    )


# ─── Context Builder ───────────────────────────────────────────────────────

def build_context(telemetry: dict, products: list, active_orders: list, cart: list,
                  pending_orders: list = None, queue: list = None, user_role: str = "client") -> str:
    status_map = {
        "idle": "ocioso na Doca Base",
        "preparing": "preparando itens na Doca Base",
        "delivering": "em rota de entrega ativa",
        "returning": "retornando à Doca Base",
        "charging": "carregando bateria na Doca Base",
    }
    robot_status = status_map.get(telemetry.get("status", "idle"), "desconhecido")

    telemetry_lines = [
        f"- Status: {robot_status}",
        f"- Bateria: {telemetry.get('battery', 100):.0f}%",
        f"- Velocidade: {telemetry.get('speed', 0):.1f} km/h",
        f"- Distância restante: {telemetry.get('distance', 0)}m",
        f"- ETA: {telemetry.get('eta', 0)}s",
    ]
    if telemetry.get("current_order_id"):
        telemetry_lines.append(f"- Missão ativa: {telemetry['current_order_id']}")

    product_lines = []
    for p in products:
        stock_label = "ESGOTADO" if p["stock"] <= 0 else f"{p['stock']} unidades disponíveis"
        product_lines.append(f"- {p['name']} (id: {p['id']}) — Estoque: {stock_label}")

    order_lines = []
    for o in active_orders:
        order_lines.append(
            f"- Pedido {o['id']}: status={o['status']}, destino={o['destination']}, itens={o['summary_text']}"
        )
    if not order_lines:
        order_lines.append("- Nenhum pedido ativo no momento.")

    cart_lines = []
    for item in cart:
        cart_lines.append(f"- {item.get('quantity', 1)}x {item.get('productName', item.get('productId'))}")
    if not cart_lines:
        cart_lines.append("- Carrinho vazio.")

    queue_section = ""
    if queue:
        q_lines = [f"- {m['order_id']} → {m['destination']} [{m['mode']}]" for m in queue[:5]]
        queue_section = f"\n### Fila de Missões\n" + "\n".join(q_lines)

    pending_section = ""
    if pending_orders and user_role == "admin":
        p_lines = [f"- {o['id']}: {o['summary_text']} → {o['destination']}" for o in pending_orders]
        pending_section = f"\n### Pedidos Pendentes de Confirmação\n" + "\n".join(p_lines)

    return f"""
## Contexto Atual (Tempo Real)

### Telemetria do Robô Camaro
{chr(10).join(telemetry_lines)}

### Estoque de Componentes
{chr(10).join(product_lines)}

### Pedidos Ativos
{chr(10).join(order_lines)}

### Carrinho Atual do Usuário
{chr(10).join(cart_lines)}
{queue_section}
{pending_section}

### Perfil do Usuário
- Tipo de usuário: {user_role}
"""


# ─── Action Parser ─────────────────────────────────────────────────────────

def parse_actions(text: str) -> tuple[list, str]:
    actions = []
    pattern = re.compile(r'<ACTION>(.*?)</ACTION>', re.DOTALL)
    matches = pattern.findall(text)
    for match in matches:
        try:
            actions.append(json.loads(match.strip()))
        except json.JSONDecodeError:
            pass
    clean_text = pattern.sub("", text).strip()
    return actions, clean_text


# ─── Gemini API Call ───────────────────────────────────────────────────────

def call_gemini(messages: list, system_context: str) -> str:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set")

    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT + "\n\n" + system_context}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 512,
            "topP": 0.9,
        },
    }

    url = f"{GEMINI_API_URL}?key={GOOGLE_API_KEY}"
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from e


# ─── Fallback Rule-Based Responder ────────────────────────────────────────

def rule_based_response(user_message: str, context_data: dict) -> tuple[list, str]:
    q = user_message.lower().strip()
    telemetry = context_data.get("telemetry", {})
    products = context_data.get("products", [])
    active_orders = context_data.get("active_orders", [])
    pending_orders = context_data.get("pending_orders", [])
    cart = context_data.get("cart", [])
    queue = context_data.get("queue", [])
    user_role = context_data.get("user_role", "client")
    actions = []

    # ── 0. Check learned patterns first ────────────────────────────────────
    q_norm = normalize_query(user_message)
    learned = db.find_learned_pattern(q_norm)
    if learned and learned.get("frequency", 0) >= 3:
        action_type = learned["action_type"]
        product_id = learned.get("product_id")
        if action_type == "add_to_cart" and product_id:
            product = next((p for p in products if p["id"] == product_id), None)
            if product and product["stock"] > 0:
                qty = extract_quantity(q)
                actions.append({
                    "action": "add_to_cart",
                    "product_id": product_id,
                    "product_name": product["name"],
                    "quantity": qty
                })
                return actions, f"🧠 [Aprendi com você!] Adicionei {qty}x {product['name']} ao carrinho."

    # ── 1. Admin-only commands ──────────────────────────────────────────────
    if user_role == "admin":
        # Confirm all pending
        if any(k in q for k in ["confirmar todos", "aprovar todos", "confirma tudo", "libera todos", "confirmar todos os pedidos"]):
            if not pending_orders:
                return [], "Não há pedidos pendentes de confirmação no momento."
            actions.append({"action": "confirm_all"})
            names = ", ".join(o["id"] for o in pending_orders[:5])
            return actions, f"✅ Confirmando todos os {len(pending_orders)} pedidos pendentes para envio individual!\nPedidos: {names}"

        # Batch route authorization
        if any(k in q for k in ["autorizar lote", "sim autorizar", "autoriza o lote", "sim faz a rota",
                                  "fazer rota em lote", "confirmar rota em lote", "autorizar rota"]):
            if len(pending_orders) >= 2:
                order_ids = [o["id"] for o in pending_orders]
                actions.append({"action": "batch_route", "order_ids": order_ids})
                dests = " → ".join(
                    sorted(set(o["destination"] for o in pending_orders),
                           key=lambda d: ROOM_DISTANCES.get(d, 5))
                ) + " → Doca Base"
                return actions, f"🗺️ Rota em lote autorizada!\n\n**Rota otimizada:** {dests}\n\nO Camaro irá entregar todos os pedidos sem voltar à base entre as paradas."
            return [], "Preciso de pelo menos 2 pedidos pendentes para criar uma rota em lote."

        # Individual mode
        if any(k in q for k in ["modo individual", "cancelar lote", "entregas individuais"]):
            return [], "Voltando ao modo de entrega individual. Cada pedido será confirmado separadamente."

        # Proactive batch suggestion trigger
        if any(k in q for k in ["ver pedidos", "pedidos pendentes", "fila", "quantos pedidos"]):
            suggestion = _build_batch_suggestion(pending_orders)
            if suggestion:
                return [], suggestion
            if not pending_orders:
                return [], "Não há pedidos pendentes no momento."
            lines = [f"• {o['id']} — {o['summary_text']} → {o['destination']}" for o in pending_orders]
            return [], "📋 Pedidos pendentes:\n\n" + "\n".join(lines)

    # ── 2. UI Navigation ────────────────────────────────────────────────────
    if any(k in q for k in ["limpar carrinho", "esvaziar carrinho", "zerar carrinho"]):
        actions.append({"action": "clear_cart"})
        return actions, "Seu carrinho foi limpo com sucesso!"

    if any(k in q for k in ["abrir carrinho", "ver carrinho", "mostrar carrinho", "meu carrinho"]) and \
       not any(k in q for k in ["adiciona", "quero", "coloca"]):
        actions.append({"action": "open_cart"})
        return actions, "Abrindo o carrinho para você revisar os itens e confirmar o destino."

    if any(k in q for k in ["mostrar mapa", "ver mapa", "abrir mapa", "acompanhar entrega",
                              "acompanhar pedido", "rastrear", "tela de acompanhamento"]):
        actions.append({"action": "show_tracking"})
        return actions, "Alternando para a tela de acompanhamento com o mapa 2D em tempo real!"

    if any(k in q for k in ["ver catalogo", "ver catálogo", "vitrine", "produtos disponíveis", "o que tem no estoque"]):
        actions.append({"action": "show_catalog"})
        return actions, "Aqui está o catálogo completo de componentes eletrônicos."

    # ── 3. Destination Selection Only ──────────────────────────────────────
    room_only_match = extract_room(q)
    if room_only_match and any(k in q for k in ["escolher", "selecionar", "mudar", "definir", "trocar", "estou na", "para a", "pra"]):
        if not find_all_products_in_text(q, products) and \
           not any(k in q for k in ["faz o pedido", "fazer pedido", "confirmar pedido"]):
            actions.append({"action": "set_destination", "destination": room_only_match})
            return actions, f"📍 Local de entrega definido para a **{room_only_match}**! Você pode adicionar mais itens ou dizer 'confirmar pedido'."

    # ── 4. Status / Where is the robot ─────────────────────────────────────
    if any(w in q for w in ["onde", "status", "camaro", "robô", "robo", "cade", "cadê", "posição", "posicao"]):
        status = telemetry.get("status", "idle")
        active_order = active_orders[-1] if active_orders else None
        target_room = active_order.get("destination", "destino") if active_order else "destino"
        queue_size = len(queue)

        if status == "delivering":
            actions.append({"action": "show_tracking"})
            return actions, (
                f"📍 O Camaro está em movimento navegando em direção à {target_room}!\n\n"
                f"• Velocidade: {telemetry.get('speed', 0):.1f} km/h\n"
                f"• Distância restante: {telemetry.get('distance', 0)}m\n"
                f"• ETA: {telemetry.get('eta', 0)}s\n"
                + (f"\n📋 Há mais {queue_size} missão(ões) na fila após esta." if queue_size > 0 else "")
            )
        elif status == "returning":
            actions.append({"action": "show_tracking"})
            return actions, (
                f"🔄 Entrega na {target_room} concluída! Camaro retornando à Doca Base a {telemetry.get('speed', 0):.1f} km/h."
                + (f"\n📋 Há {queue_size} missão(ões) aguardando." if queue_size > 0 else "")
            )
        elif status == "preparing":
            actions.append({"action": "show_tracking"})
            return actions, "📦 O Camaro está sendo preparado na Doca Base. Iniciará o trajeto em instantes."
        else:
            idle_msg = f"⚡ O Camaro está ocioso na Doca Base. Bateria: {telemetry.get('battery', 100):.0f}%."
            if queue_size > 0:
                idle_msg += f"\n📋 Há {queue_size} missão(ões) aguardando confirmação."
            return [], idle_msg

    # ── 5. Multiple or Single Component Request ─────────────────────────────
    matched_products = find_all_products_in_text(q, products)
    if matched_products:
        out_of_stock = [m for m in matched_products if m["quantity"] <= 0]
        available = [m for m in matched_products if m["quantity"] > 0]

        if not available:
            names = ", ".join(m["product"]["name"] for m in out_of_stock)
            return [], f"Infelizmente {names} está(ão) esgotado(s) no momento."

        room = extract_room(q)
        is_auto_submit = room is not None or any(k in q for k in [
            "faz o pedido", "fazer pedido", "pede pra mim", "manda pra",
            "entrega na", "finaliza", "confirmar pedido", "pede agora", "levar pra"
        ])

        # Build add_to_cart actions for each product
        for m in available:
            if is_auto_submit:
                target_room = room or "SALA A"
                actions.append({
                    "action": "submit_order",
                    "product_id": m["product"]["id"],
                    "product_name": m["product"]["name"],
                    "quantity": m["quantity"],
                    "destination": target_room,
                    "timing": "now",
                    "notes": "Pedido via Chat AI"
                })
            else:
                actions.append({
                    "action": "add_to_cart",
                    "product_id": m["product"]["id"],
                    "product_name": m["product"]["name"],
                    "quantity": m["quantity"]
                })

        item_lines = "\n".join(f"• {m['quantity']}x {m['product']['name']}" for m in available)
        out_of_stock_note = ""
        if out_of_stock:
            out_of_stock_note = f"\n\n⚠️ Esgotado: {', '.join(m['product']['name'] for m in out_of_stock)}"

        if is_auto_submit:
            return actions, (
                f"✅ Pedido confirmado com sucesso!\n\n{item_lines}\n"
                f"Destino: {target_room}{out_of_stock_note}\n\n"
                f"O Camaro iniciará o trajeto assim que o operador confirmar o envio."
            )
        else:
            next_tip = "Você pode dizer 'escolher Sala B' ou 'confirmar pedido'."
            return actions, f"🛒 Adicionado ao carrinho:\n\n{item_lines}{out_of_stock_note}\n\n{next_tip}"

    # ── 6. Confirm existing cart ────────────────────────────────────────────
    if any(k in q for k in ["confirmar pedido", "finalizar pedido", "enviar pedido",
                              "pode enviar", "manda o pedido", "fazer pedido", "concluir pedido"]):
        if not cart:
            return [], "Seu carrinho está vazio! Primeiro me diga quais componentes você precisa."
        room = extract_room(q) or "SALA A"
        actions.append({"action": "submit_order", "destination": room, "timing": "now", "notes": "Confirmado via Chat AI"})
        return actions, f"✅ Confirmando o envio do seu carrinho para a {room}! Alternando para o mapa."

    # ── 7. Stock Query ──────────────────────────────────────────────────────
    if any(w in q for w in ["estoque", "o que tem", "componentes disponíveis", "tem disponível"]):
        lines = []
        for p in products:
            lines.append(f"• {p['name']}: {p['stock']} un" if p['stock'] > 0 else f"• {p['name']}: Esgotado")
        return [], "📦 Estoque atual:\n\n" + "\n".join(lines) + "\n\nEx: 'adicione 2 ESP32 e 1 relé'"

    # ── 8. Active Orders Query ──────────────────────────────────────────────
    if any(w in q for w in ["meu pedido", "meus pedidos", "minha entrega"]):
        if not active_orders:
            return [], "Você não tem pedidos ativos no momento."
        latest = active_orders[-1]
        actions.append({"action": "show_tracking"})
        return actions, f"Pedido {latest['id']} — [{latest['summary_text']}] — Status: {latest['status']} → {latest['destination']}"

    # ── 9. Greetings ────────────────────────────────────────────────────────
    if any(w in q for w in ["olá", "oi", "bom dia", "boa tarde", "boa noite", "ola", "help", "ajuda"]):
        if user_role == "admin":
            return [], (
                "Olá, Operador! 🤖 Estou pronto para auxiliar na gestão das entregas.\n\n"
                "Comandos disponíveis:\n"
                "• *'Ver pedidos pendentes'* — lista e sugere rota em lote se aplicável\n"
                "• *'Confirmar todos os pedidos'* — envia todos para fila individual\n"
                "• *'Autorizar lote'* — após sugestão de rota em lote\n"
                "• *'Onde está o Camaro?'* — telemetria em tempo real\n"
                "• *'Ver fila'* — fila de missões atual"
            )
        return [], (
            "Olá! Sou o assistente do robô Camaro 🤖\n\n"
            "Você pode pedir múltiplos componentes de uma vez, ex:\n"
            "• *'Adicione 2 ESP32 e 1 relé'*\n"
            "• *'Abrir carrinho'*\n"
            "• *'Escolher Sala B'*\n"
            "• *'Confirmar pedido'*\n"
            "• *'Onde está o Camaro?'*"
        )

    # ── Proactive batch suggestion for admin (any message) ─────────────────
    if user_role == "admin" and len(pending_orders) >= 2:
        suggestion = _build_batch_suggestion(pending_orders)
        if suggestion:
            return [], suggestion

    # Default
    return [], "Posso te ajudar com pedidos, rastreamento e telemetria do Camaro. Como posso ajudar?"


# ─── Main Entry Point ──────────────────────────────────────────────────────

def process_message(user_message: str, history: list, context_data: dict) -> dict:
    system_context = build_context(
        telemetry=context_data.get("telemetry", {}),
        products=context_data.get("products", []),
        active_orders=context_data.get("active_orders", []),
        cart=context_data.get("cart", []),
        pending_orders=context_data.get("pending_orders", []),
        queue=context_data.get("queue", []),
        user_role=context_data.get("user_role", "client"),
    )

    if GOOGLE_API_KEY:
        try:
            messages = []
            for h in history[-18:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": user_message})
            raw_response = call_gemini(messages, system_context)
            actions, clean_text = parse_actions(raw_response)
            return {"text": clean_text, "actions": actions, "source": "gemini"}
        except Exception as e:
            print(f"[LLM] Gemini error: {e} — using fallback")

    actions, text = rule_based_response(user_message, context_data)
    return {"text": text, "actions": actions, "source": "fallback"}
