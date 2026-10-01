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
import time
import threading
import roslibpy

ROSBRIDGE_HOST = "localhost"
ROSBRIDGE_PORT = 9090

ODOM_TOPIC = "/odom"
ODOM_TYPE = "nav_msgs/Odometry"

import math

# Estado global compartilhado com o resto do backend.
robot_state = {
    "x": 2.0,
    "y": 0.0,
    "z": 0.0,
    "yaw": 0.0,
    "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
    "connected": False,
}

_client = None


def _on_odom(message):
    try:
        pose_data = message.get("pose", {}).get("pose", {})
        pos = pose_data.get("position", {})
        ori = pose_data.get("orientation", {})
        
        robot_state["x"] = float(pos.get("x", 0.0))
        robot_state["y"] = float(pos.get("y", 0.0))
        robot_state["z"] = float(pos.get("z", 0.0))
        
        # Converte quaternion para yaw (ângulo de rotação em torno do eixo Z)
        qx = float(ori.get("x", 0.0))
        qy = float(ori.get("y", 0.0))
        qz = float(ori.get("z", 0.0))
        qw = float(ori.get("w", 1.0))
        
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        robot_state["yaw"] = yaw
        robot_state["orientation"] = {"x": qx, "y": qy, "z": qz, "w": qw}
    except Exception as e:
        pass


def _start_listener():
    global _client
    while True:
        try:
            _client = roslibpy.Ros(host=ROSBRIDGE_HOST, port=ROSBRIDGE_PORT)

            def on_ready():
                robot_state["connected"] = True
                print(f"[robot_bridge] Conectado ao rosbridge em "
                      f"ws://{ROSBRIDGE_HOST}:{ROSBRIDGE_PORT}, escutando {ODOM_TOPIC}")
                listener = roslibpy.Topic(_client, ODOM_TOPIC, ODOM_TYPE)
                listener.subscribe(_on_odom)

            _client.on_ready(on_ready)
            _client.run_forever()
        except Exception as e:
            pass
        finally:
            robot_state["connected"] = False
            try:
                if _client and _client.is_connected:
                    _client.close()
            except Exception:
                pass
        time.sleep(3)


def start_bridge():
    """Chame uma vez, no startup do Flask. Roda em background (daemon thread)."""
    thread = threading.Thread(target=_start_listener, daemon=True)
    thread.start()