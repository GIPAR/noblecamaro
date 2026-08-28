"""
Executa UMA rota de verdade, mandando o Camaro navegar pelos waypoints
via Nav2 (isso MOVE o robô, ao contrário do evaluate_routes.py que só
calcula).

Uso -- por ID da rota (rode `python3 route_generator.py` pra ver a lista
com os IDs de todas as 64):

    python3 execute_route.py --id R05

Uso -- direto pela ordem das salas (não precisa saber o ID de cor):

    python3 execute_route.py --order A C
    python3 execute_route.py --order B          # só uma sala
    python3 execute_route.py --order D A C B    # as 4, nessa ordem

PRÉ-REQUISITO: Gazebo + Nav2 já rodando e o robô localizado (mesmo esquema
do evaluate_routes.py).
"""
import argparse
import sys

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from tf_transformations import quaternion_from_euler

from route_generator import generate_routes


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


def find_route(routes, route_id=None, order=None):
    if route_id:
        route_id = route_id.upper()
        for r in routes:
            if r["id"] == route_id:
                return r
        return None
    if order:
        order = [o.upper() for o in order]
        for r in routes:
            if r["order"] == order:
                return r
        return None
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Executa uma das 64 rotas geradas, navegando de verdade com o Nav2."
    )
    parser.add_argument("--id", help="ID da rota, ex: R05 (veja a lista com route_generator.py)")
    parser.add_argument("--order", nargs="+", help="Ordem das salas, ex: --order A C")
    args = parser.parse_args()

    if not args.id and not args.order:
        print("Use um dos dois:")
        print("  python3 execute_route.py --id R05")
        print("  python3 execute_route.py --order A C")
        print("\n(rode `python3 route_generator.py` pra ver a lista completa com IDs)")
        sys.exit(1)

    routes = generate_routes()
    route = find_route(routes, route_id=args.id, order=args.order)

    if route is None:
        print("Rota não encontrada. Confira o ID (ex: R05) ou a ordem das salas (ex: A C).")
        sys.exit(1)

    print(f"Executando {route['id']}: base -> {' -> '.join(route['order'])} -> base")
    print(f"({len(route['waypoints'])} waypoints, incluindo aproximações e portas)\n")

    rclpy.init()
    navigator = BasicNavigator()
    navigator.waitUntilNav2Active()

    # pula o primeiro waypoint (a própria BASE) -- é só a posição de
    # partida, não um alvo de navegação; o robô já deve estar lá
    waypoints = [make_pose(navigator, wp) for wp in route["waypoints"][1:]]

    navigator.followWaypoints(waypoints)

    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback:
            atual = feedback.current_waypoint + 1
            print(f"Indo pro waypoint {atual}/{len(waypoints)}...")

    result = navigator.getResult()
    if result == TaskResult.SUCCEEDED:
        print("\n✅ Rota concluída com sucesso!")
    elif result == TaskResult.CANCELED:
        print("\n⚠️ Rota cancelada.")
    elif result == TaskResult.FAILED:
        print("\n❌ Falha ao executar a rota (algum waypoint não foi alcançado).")

    navigator.lifecycleShutdown()
    rclpy.shutdown()


if __name__ == "__main__":
    main()