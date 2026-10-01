import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('camaro_description')

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value='nav2_params_light.yaml',
        description='Config do Nav2 por perfil: nav2_params_light.yaml ou nav2_params_high.yaml'
    )
    nav2_params   = PathJoinSubstitution([pkg, 'config', LaunchConfiguration('params_file')])
    filter_params = os.path.join(pkg, 'config', 'laser_filter.yaml')
    map_file      = os.path.join(pkg, 'maps', 'corridor_rooms.yaml')  # <- seu mapa novo

    params = [nav2_params, {'use_sim_time': True}]

    # =========================================================
    # LASER FILTER
    # =========================================================
    laser_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        output='screen',
        parameters=[filter_params, {'use_sim_time': True}],
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
                         output='screen', parameters=params + [{
                             'default_nav_to_pose_bt_xml': os.path.join(pkg, 'behavior_trees', 'camaro_nav.xml')
                         }])
    waypoint_follower = Node(package='nav2_waypoint_follower', executable='waypoint_follower',
                              output='screen', parameters=params)
    collision_monitor = Node(package='nav2_collision_monitor', executable='collision_monitor',
                              output='screen', parameters=params)

    # =========================================================
    # DYNAMIC FOOTPRINT — recalcula o footprint do chassi a partir
    # do esterço (/joint_states) e publica nos tópicos que os costmaps
    # assinam (geometry_msgs/Polygon em .../footprint)
    # =========================================================
    dynamic_footprint = Node(
        package='camaro_description',
        executable='dynamic_footprint_node',
        name='dynamic_footprint_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'wheelbase': 0.71,
            'half_width': 0.23,
            'half_length_front': 0.30,
            'half_length_rear': 0.30,
            'safety_margin': 0.05,
            'max_steering_angle': 0.6,
            'publish_rate_hz': 10.0,
            'local_footprint_topic': '/local_costmap/footprint',
            'global_footprint_topic': '/global_costmap/footprint',
        }]
    )

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
            bt_navigator, waypoint_follower, collision_monitor, dynamic_footprint,
            lifecycle_manager_navigation,
        ]
    )

    return LaunchDescription([
        params_arg,
        laser_filter,
        *localization_nodes,
        nav2_nodes,
        rviz,
    ])