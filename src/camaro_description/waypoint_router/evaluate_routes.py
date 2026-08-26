"""
Avalia as 24 rotas geradas usando o planejador global do Nav2
(nav2_simple_commander) -- sem mover o robô de verdade, só pedindo o
caminho planejado (getPath) para cada trecho e medindo:

  - distância total do caminho planejado (m)
  - número de "curvas" significativas (mudanças de direção > TURN_THRESHOLD_DEG)
  - tempo estimado (distância / velocidade média configurada)

No final, ranqueia as rotas por um score simples (distância + peso das
curvas) e mostra a melhor. Isso é só um ranking automático por enquanto --
depois dá pra trocar esse ranking por uma LLM.

PRÉ-REQUISITOS: Gazebo + Nav2 (bringup completo, com mapa e
localização/AMCL já rodando) precisam estar ativos ANTES de rodar este
script.

Como rodar (depois do bringup do Nav2 já estar de pé em outro terminal):
    cd ~/seu_workspace
    source install/setup.bash
    python3 src/waypoint_router/evaluate_routes.py
"""
import json
import math

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator
from tf_transformations import quaternion_from_euler

from route_generator import generate_routes

AVG_SPEED_MPS = 0.8   # velocidade média estimada do Camaro, ajuste se precisar
TURN_THRESHOLD_DEG = 15.0   # abaixo disso não conta como "curva"
TURN_PENALTY_M = 1.5        # cada curva "pesa" como se fossem X metros a mais no score


def make_pose(navigator, xyyaw):
    x, y, yaw = xyyaw
    pose = PoseStamped()
    pose.header.frame_id = "map"
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    q = quaternion_from_euler(0, 0, yaw)
    pose.pose.orientation.x = q[0]
    pose.pose.orientation.y = q[1]
    pose.pose.orientation.z = q[2]
    pose.pose.orientation.w = q[3]
    return pose


def path_metrics(path_msg):
    """Calcula distância total e número de curvas de um nav_msgs/Path."""
    points = [(p.pose.position.x, p.pose.position.y) for p in path_msg.poses]
    if len(points) < 3:
        return 0.0, 0

    total_dist = 0.0
    for i in range(1, len(points)):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]
        total_dist += math.hypot(x2 - x1, y2 - y1)

    turns = 0
    for i in range(1, len(points) - 1):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        v1 = (x1 - x0, y1 - y0)
        v2 = (x2 - x1, y2 - y1)
        n1 = math.hypot(*v1)
        n2 = math.hypot(*v2)
        if n1 < 1e-6 or n2 < 1e-6:
            continue
        cos_angle = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
        angle_deg = math.degrees(math.acos(cos_angle))
        if angle_deg > TURN_THRESHOLD_DEG:
            turns += 1

    return total_dist, turns


def evaluate_all_routes(output_path="routes_metrics.json"):
    rclpy.init()
    navigator = BasicNavigator()
    navigator.waitUntilNav2Active()

    routes = generate_routes()
    results = []

    for route in routes:
        waypoints = route["waypoints"]
        full_distance = 0.0
        full_turns = 0
        segment_ok = True

        # calcula o caminho segmento a segmento (base->aprox_A->A->aprox_B->...->base)
        for i in range(len(waypoints) - 1):
            seg_start = make_pose(navigator, waypoints[i])
            seg_goal = make_pose(navigator, waypoints[i + 1])
            path = navigator.getPath(seg_start, seg_goal)
            if path is None:
                segment_ok = False
                break
            dist, turns = path_metrics(path)
            full_distance += dist
            full_turns += turns

        if not segment_ok:
            print(f"[AVISO] {route['id']} ({'->'.join(route['order'])}): "
                  f"planner não encontrou caminho para algum trecho, pulando.")
            continue

        est_time_s = full_distance / AVG_SPEED_MPS if AVG_SPEED_MPS > 0 else None
        score = full_distance + full_turns * TURN_PENALTY_M

        result = {
            "id": route["id"],
            "order": route["order"],
            "distance_m": round(full_distance, 2),
            "turns": full_turns,
            "estimated_time_s": round(est_time_s, 1) if est_time_s else None,
            "score": round(score, 2),
        }
        results.append(result)
        print(f"{route['id']}: base->{'->'.join(route['order'])}->base | "
              f"dist={result['distance_m']}m | curvas={result['turns']} | "
              f"tempo~{result['estimated_time_s']}s | score={result['score']}")

    results.sort(key=lambda r: r["score"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{len(results)} rotas avaliadas. Métricas salvas em {output_path}")
    if results:
        best = results[0]
        print(f"\n>>> MELHOR ROTA: {best['id']} "
              f"(base -> {' -> '.join(best['order'])} -> base)")
        print(f"    distância={best['distance_m']}m | curvas={best['turns']} | "
              f"tempo~{best['estimated_time_s']}s | score={best['score']}")

    navigator.lifecycleShutdown()
    rclpy.shutdown()
    return results


if __name__ == "__main__":
    evaluate_all_routes()