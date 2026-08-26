import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('camaro_description')

    nav2_params   = os.path.join(pkg, 'config', 'nav2_params.yaml')
    filter_params = os.path.join(pkg, 'config', 'laser_filter.yaml')
    map_file      = os.path.join(pkg, 'maps', 'corridor_rooms.yaml')  # <- seu mapa novo

    params = [nav2_params, {'use_sim_time': True}]

    # =========================================================
    # LASER FILTER
    # =========================================================
    laser_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='laser_filter',
        output='screen',
        arguments=[filter_params],
        parameters=[{'use_sim_time': True}],
        remappings=[
            ('scan', '/scan'),
            ('scan_filtered', '/scan_filtered'),
        ]
    )

    # =========================================================
    # MAP SERVER — carrega o mapa salvo
    # =========================================================
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'use_sim_time': True, 'yaml_filename': map_file}]
    )

    # =========================================================
    # AMCL — localiza o robô dentro do mapa (publica map -> odom)
    # =========================================================
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=params
    )

    # =========================================================
    # LIFECYCLE MANAGER — ativa map_server + amcl
    # =========================================================
    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server', 'amcl']
        }]
    )

    # =========================================================
    # NAV2 — nós de navegação (iguais aos que já tinha)
    # =========================================================
    controller_server = Node(package='nav2_controller', executable='controller_server',
                              output='screen', parameters=params,
                              remappings=[('cmd_vel', 'cmd_vel_nav')])
    smoother_server = Node(package='nav2_smoother', executable='smoother_server',
                            output='screen', parameters=params)
    planner_server = Node(package='nav2_planner', executable='planner_server',
                           output='screen', parameters=params)
    behavior_server = Node(package='nav2_behaviors', executable='behavior_server',
                            output='screen', parameters=params,
                            remappings=[('cmd_vel', 'cmd_vel_nav')])
    bt_navigator = Node(package='nav2_bt_navigator', executable='bt_navigator',
                         output='screen', parameters=params)
    waypoint_follower = Node(package='nav2_waypoint_follower', executable='waypoint_follower',
                              output='screen', parameters=params)
    collision_monitor = Node(package='nav2_collision_monitor', executable='collision_monitor',
                              output='screen', parameters=params)

    lifecycle_manager_navigation = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': [
                'controller_server', 'smoother_server', 'planner_server',
                'behavior_server', 'bt_navigator', 'waypoint_follower',
                'collision_monitor',
            ]
        }]
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        parameters=[{'use_sim_time': True}],
        arguments=['-d', os.path.join(pkg, 'config', 'nav2.rviz')]
    )

    # localização sobe primeiro, navegação 3s depois
    localization_nodes = [map_server, amcl, lifecycle_manager_localization]
    nav2_nodes = TimerAction(
        period=3.0,
        actions=[
            controller_server, smoother_server, planner_server, behavior_server,
            bt_navigator, waypoint_follower, collision_monitor,
            lifecycle_manager_navigation,
        ]
    )

    return LaunchDescription([
        laser_filter,
        *localization_nodes,
        nav2_nodes,
        rviz,
    ])