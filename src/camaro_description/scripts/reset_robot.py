#!/usr/bin/env python3
"""
Script de Reset de Posição do Robô no Gazebo Harmonic.
Teleporta o robô de volta para a posição inicial (ou personalizada) sem precisar fechar a simulação.

Uso:
  ros2 run camaro_description reset_robot.py --robot smart_camaro --x 0.0 --y 0.0 --z 0.1
  ros2 run camaro_description reset_robot.py --robot camaro_a --y 2.0
"""

import sys
import argparse
import subprocess

def reset_pose(robot_name, world_name, x, y, z):
    print(f"🔄 Teleportando '{robot_name}' para ({x}, {y}, {z}) no mundo '{world_name}'...")

    # Comando do Gazebo Harmonic para alterar a pose da entidade
    cmd = [
        "gz", "service",
        "-s", f"/world/{world_name}/set_pose",
        "--reqtype", "gz.msgs.Pose",
        "--reptype", "gz.msgs.Boolean",
        "--req", f'name: "{robot_name}", position: {{x: {x}, y: {y}, z: {z}}}, orientation: {{x: 0, y: 0, z: 0, w: 1}}'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Robô '{robot_name}' resetado com sucesso para a base ({x}, {y}, {z})!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Erro ao resetar pelo Gazebo CLI: {e.stderr}")
        print("💡 Tentando via ROS 2 service bridge...")
        # Fallback via ROS 2 service call
        ros_cmd = [
            "ros2", "service", "call",
            f"/world/{world_name}/set_pose",
            "ros_gz_interfaces/srv/SetEntityPose",
            f"{{entity: {{name: '{robot_name}'}}, pose: {{position: {{x: {x}, y: {y}, z: {z}}}}}}}"
        ]
        try:
            subprocess.run(ros_cmd, check=True)
            print(f"✅ Robô '{robot_name}' resetado com sucesso via ROS 2!")
        except Exception as err:
            print(f"❌ Não foi possível resetar o robô. Verifique se o Gazebo está aberto. Detalhes: {err}")

def main():
    parser = argparse.ArgumentParser(description="Reset de posição do robô no Gazebo Harmonic.")
    parser.add_argument("--robot", "--robot_name", type=str, default="smart_camaro", help="Nome do robô (ex: smart_camaro, camaro_a)")
    parser.add_argument("--world", type=str, default="corridor_rooms", help="Nome do mundo (ex: corridor_rooms)")
    parser.add_argument("--x", type=float, default=0.0, help="Coordenada X")
    parser.add_argument("--y", type=float, default=0.0, help="Coordenada Y")
    parser.add_argument("--z", type=float, default=0.1, help="Coordenada Z")

    args, unknown = parser.parse_known_args()
    reset_pose(args.robot, args.world, args.x, args.y, args.z)

if __name__ == "__main__":
    main()
