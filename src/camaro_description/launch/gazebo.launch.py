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

    # === GAZEBO SIM ===
    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', '-r', os.path.join(pkg, 'worlds', 'museum.world')],
        output='screen'
    )

    # === ROBOT STATE PUBLISHER ===
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    # === SPAWN DO ROBÔ NO GAZEBO ===
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

    # === BRIDGE: GAZEBO ↔ ROS 2 ===
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Controle: ROS → Gazebo
            '/model/smart_camaro/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            # Odometria: Gazebo → ROS
            '/model/smart_camaro/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            # TF do odom→base_link: Gazebo → ROS (remapeado para /tf_gz)
            '/model/smart_camaro/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
            # Joint States: Gazebo → ROS
            '/model/smart_camaro/joint_state@sensor_msgs/msg/JointState@gz.msgs.JointState',
            # LiDAR: Gazebo → ROS (unidirecional)
            '/lidarA2/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
        ],
        remappings=[
            ('/model/smart_camaro/cmd_vel', '/cmd_vel'),
            ('/model/smart_camaro/odometry', '/odom'),
            ('/model/smart_camaro/tf', '/tf_gz'),  # <-- Remapeado para evitar conflito
            ('/model/smart_camaro/joint_state', '/joint_states'),
            ('/lidarA2/scan', '/scan'),
        ],
        output='screen'
    )

    # === TF REMAPPER: Corrige os frames smart_camaro/* -> * ===
    tf_remapper = Node(
        package='camaro_description',
        executable='tf_remapper.py',
        name='tf_remapper',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        gz_sim,
        robot_state_publisher_node,
        spawn_entity,
        bridge,
        tf_remapper,
    ])