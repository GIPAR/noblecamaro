import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg        = get_package_share_directory('smart_camaro')
    slam_pkg   = get_package_share_directory('slam_toolbox')

    nav2_params   = os.path.join(pkg, 'config', 'nav2_params.yaml')
    slam_params   = os.path.join(pkg, 'config', 'slam_params.yaml')
    filter_params = os.path.join(pkg, 'config', 'laser_filter.yaml')

    # =========================================================
    # SLAM TOOLBOX — publica /map e transform map → odom
    # =========================================================
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_pkg, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'slam_params_file': slam_params,
            'use_sim_time': 'true',
        }.items()
    )

    # =========================================================
    # LASER FILTER — remove leituras do próprio chassi do Camaro
    # Entrada: /scan (bruto) → Saída: /scan_filtered (limpo)
    # =========================================================
    laser_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='laser_filter',
        output='screen',
        parameters=[filter_params, {'use_sim_time': True}],
        remappings=[
            ('scan', '/scan'),
            ('scan_filtered', '/scan_filtered'),
        ]
    )

    # =========================================================
    # NAV2 — nós individuais (sem docking_server, sem AMCL)
    # =========================================================
    params = [nav2_params, {'use_sim_time': True}]

    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        output='screen',
        parameters=params
    )

    smoother_server = Node(
        package='nav2_smoother',
        executable='smoother_server',
        output='screen',
        parameters=params
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        output='screen',
        parameters=params
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        output='screen',
        parameters=params
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        output='screen',
        parameters=params
    )

    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        output='screen',
        parameters=params
    )

    # velocity_smoother = Node(
    #     package='nav2_velocity_smoother',
    #     executable='velocity_smoother',
    #     output='screen',
    #     parameters=params
    # )

    collision_monitor = Node(
        package='nav2_collision_monitor',
        executable='collision_monitor',
        output='screen',
        parameters=params
    )

    # =========================================================
    # LIFECYCLE MANAGER — ativa todos os nós Nav2 na ordem certa
    # =========================================================
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': [
                'controller_server',
                'smoother_server',
                'planner_server',
                'behavior_server',
                'bt_navigator',
                'waypoint_follower',
                # 'velocity_smoother',
                'collision_monitor',
            ]
        }]
    )

    # =========================================================
    # RVIZ2
    # =========================================================
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # Nav2 sobe 5s depois do SLAM para evitar conflito de TF
    nav2_nodes = TimerAction(
        period=5.0,
        actions=[
            controller_server,
            smoother_server,
            planner_server,
            behavior_server,
            bt_navigator,
            waypoint_follower,
            # velocity_smoother,
            collision_monitor,
            lifecycle_manager,
        ]
    )

    return LaunchDescription([
        slam,
        laser_filter,
        nav2_nodes,
        rviz,
    ])