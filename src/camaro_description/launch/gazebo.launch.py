import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg = get_package_share_directory('camaro_description')
    xacro_file = os.path.join(pkg, 'urdf', 'camaro.xacro')
    robot_description = xacro.process_file(xacro_file).toxml()

    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', '-r', os.path.join(pkg, 'worlds', 'BlocoG-Antigo.sdf')],
        output='screen'
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'smart_camaro',
            '-topic', '/robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.0'
        ],
        output='screen'
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/model/smart_camaro/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist', # <--- ATUALIZE O TÓPICO
            '/model/smart_camaro/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
        ],
        remappings=[
            ('/model/smart_camaro/cmd_vel', '/cmd_vel'),
            ('/model/smart_camaro/odometry', '/odom'),
        ],
        output='screen'
    )

    return LaunchDescription([
        gz_sim,
        robot_state_publisher_node,
        spawn_entity,
        bridge
    ])