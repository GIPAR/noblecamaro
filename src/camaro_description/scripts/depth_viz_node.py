#!/usr/bin/env python3
"""
depth_viz_node.py — Torna a profundidade da ZED visível no dashboard.

Problema: o Gazebo publica a profundidade em float32 (metros, 32FC1) no
tópico /zed/zed_node/rgb/image_raw/depth_image. O web_video_server não
converte float para MJPEG sozinho — o frame chega preto/roxo no navegador.

Solução: este nó assina a imagem float, normaliza (perto = claro, longe =
escuro, com clip no alcance do sensor) e republica colorida (TURBO) em
/zed/zed_node/rgb/depth_image_viz (rgb8), que o web_video_server exibe
normalmente e o Flask entrega ao dashboard.

Uso no launch (gazebo.launch.py):
    Node(package='camaro_description', executable='depth_viz_node.py', ...)
Uso avulso:
    ros2 run camaro_description depth_viz_node.py
"""
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

try:
    import cv2
    _HAS_CV2 = hasattr(cv2, "applyColorMap") and hasattr(cv2, "COLORMAP_TURBO")
except Exception:
    cv2 = None
    _HAS_CV2 = False

RAW_TOPIC = "/zed/zed_node/rgb/image_raw/depth_image"
VIZ_TOPIC = "/zed/zed_node/rgb/depth_image_viz"

# Alcance útil do sensor (igual ao <clip> do camaro.gazebo)
NEAR_M = 0.2
FAR_M = 20.0


def float_depth_to_rgb(data: bytes, width: int, height: int) -> tuple[bytes, str]:
    """Converte buffer 32FC1 (metros) em imagem colorida (rgb8)."""
    depth = np.frombuffer(data, dtype=np.float32).reshape((height, width))
    valid = np.isfinite(depth)
    clipped = np.clip(np.where(valid, depth, FAR_M), NEAR_M, FAR_M)
    # perto -> 1 (claro), longe -> 0 (escuro)
    norm = 1.0 - (clipped - NEAR_M) / (FAR_M - NEAR_M)
    gray = (norm * 255.0).astype(np.uint8)
    if _HAS_CV2:
        bgr = cv2.applyColorMap(gray, cv2.COLORMAP_TURBO)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    else:
        rgb = np.stack([gray, gray, gray], axis=-1)
    return rgb.tobytes(), "rgb8"


class DepthVizNode(Node):
    def __init__(self):
        super().__init__("depth_viz")
        self.pub = self.create_publisher(Image, VIZ_TOPIC, 10)
        self.sub = self.create_subscription(Image, RAW_TOPIC, self.on_depth, 10)
        self.get_logger().info(f"depth_viz: {RAW_TOPIC} -> {VIZ_TOPIC}")

    def on_depth(self, msg: Image):
        try:
            if msg.encoding not in ("32FC1",):
                return
            buf, enc = float_depth_to_rgb(msg.data, msg.width, msg.height)
        except Exception as e:
            self.get_logger().warn(f"falha ao converter depth: {e}", throttle_duration_sec=5.0)
            return
        out = Image()
        out.header = msg.header
        out.height = msg.height
        out.width = msg.width
        out.encoding = enc
        out.is_bigendian = 0
        out.step = msg.width * 3
        out.data = buf
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = DepthVizNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
