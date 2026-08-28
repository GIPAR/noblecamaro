# backend/robot_bridge.py
"""
Ponte entre o ROS2/Gazebo e o backend Flask.

Roda numa thread separada, conectada ao rosbridge (ws://localhost:9090),
escutando a pose do robô e guardando sempre a última posição conhecida
na variável global `robot_state`.

Requisitos:
    pip install roslibpy

Pré-requisito de infraestrutura:
    O rosbridge precisa estar rodando ANTES do Flask subir:
        ros2 launch rosbridge_server rosbridge_websocket_launch.xml

Se o robô publicar a pose já localizada no frame 'map' (ex: via AMCL ou
robot_localization), troque ODOM_TOPIC/ODOM_TYPE abaixo pelo tópico
correspondente (ex: '/amcl_pose', 'geometry_msgs/PoseWithCovarianceStamped')
-- assim as coordenadas batem exatamente com as de room_map.py.
"""
import threading
import roslibpy

ROSBRIDGE_HOST = "localhost"
ROSBRIDGE_PORT = 9090

ODOM_TOPIC = "/odom"
ODOM_TYPE = "nav_msgs/Odometry"

# Estado global compartilhado com o resto do backend.
robot_state = {
    "x": 0.0,
    "y": 0.0,
    "connected": False,
}

_client = None


def _on_odom(message):
    pos = message["pose"]["pose"]["position"]
    robot_state["x"] = pos["x"]
    robot_state["y"] = pos["y"]


def _start_listener():
    global _client
    _client = roslibpy.Ros(host=ROSBRIDGE_HOST, port=ROSBRIDGE_PORT)

    def on_ready():
        robot_state["connected"] = True
        print(f"[robot_bridge] Conectado ao rosbridge em "
              f"ws://{ROSBRIDGE_HOST}:{ROSBRIDGE_PORT}, escutando {ODOM_TOPIC}")
        listener = roslibpy.Topic(_client, ODOM_TOPIC, ODOM_TYPE)
        listener.subscribe(_on_odom)

    _client.on_ready(on_ready)

    try:
        _client.run_forever()
    except Exception as e:
        robot_state["connected"] = False
        print(f"[robot_bridge] Conexão com o rosbridge encerrada/falhou: {e}")


def start_bridge():
    """Chame uma vez, no startup do Flask. Roda em background (daemon thread)."""
    thread = threading.Thread(target=_start_listener, daemon=True)
    thread.start()