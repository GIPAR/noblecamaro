import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def launch_setup(context, *args, **kwargs):
    # Resgata os argumentos como strings do Python
    robot_name = context.perform_substitution(LaunchConfiguration('robot_name'))
    robot_namespace = context.perform_substitution(LaunchConfiguration('robot_namespace'))
    x = context.perform_substitution(LaunchConfiguration('x'))
    y = context.perform_substitution(LaunchConfiguration('y'))
    z = context.perform_substitution(LaunchConfiguration('z'))
    urdf_package = context.perform_substitution(LaunchConfiguration('urdf_package'))
    urdf_file_rel = context.perform_substitution(LaunchConfiguration('urdf_file'))

    # Carrega o Xacro do pacote especificado
    try:
        pkg = get_package_share_directory(urdf_package)
        xacro_file = os.path.join(pkg, urdf_file_rel)
    except Exception as e:
        print(f"⚠️ Não foi possível encontrar o pacote '{urdf_package}'. Usando 'camaro_description' como fallback: {e}")
        pkg = get_package_share_directory('camaro_description')
        xacro_file = os.path.join(pkg, 'urdf', 'camaro.xacro')

    # Processa o Xacro injetando o prefixo nas juntas e links (se suportado pelo xacro)
    prefix = robot_namespace + '/' if robot_namespace else ''
    try:
        robot_description = xacro.process_file(
            xacro_file,
            mappings={'prefix': prefix}
        ).toxml()
    except Exception:
        # Fallback se o xacro do robô externo não usar a variável prefix
        robot_description = xacro.process_file(xacro_file).toxml()

    # === ROBOT STATE PUBLISHER ===
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        namespace=robot_namespace,
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
            'frame_prefix': prefix
        }]
    )

    # === SPAWN DO ROBÔ NO GAZEBO ===
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', robot_name,
            '-topic', f'/{robot_namespace}/robot_description' if robot_namespace else '/robot_description',
            '-x', x,
            '-y', y,
            '-z', z
        ],
        output='screen'
    )

    # === BRIDGE PRINCIPAL: GAZEBO ↔ ROS 2 ===
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            f'/model/{robot_name}/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            f'/model/{robot_name}/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            f'/model/{robot_name}/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
            f'/world/default/model/{robot_name}/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model',
            f'/model/{robot_name}/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
        ],
        remappings=[
            (f'/model/{robot_name}/cmd_vel', 'cmd_vel'),
            (f'/model/{robot_name}/odometry', 'odom'),
            (f'/model/{robot_name}/tf', '/tf'),
            (f'/world/default/model/{robot_name}/joint_state', 'joint_states'),
            (f'/model/{robot_name}/scan', 'scan'),
        ],
        parameters=[{'use_sim_time': True}],
        namespace=robot_namespace,
        output='screen'
    )

    return [
        robot_state_publisher_node,
        spawn_entity,
        bridge
    ]

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('robot_name', default_value='smart_camaro', description='Nome do robô no Gazebo'),
        DeclareLaunchArgument('robot_namespace', default_value='smart_camaro', description='Namespace do ROS 2 do robô'),
        DeclareLaunchArgument('x', default_value='0.0', description='Posição X de spawn'),
        DeclareLaunchArgument('y', default_value='0.0', description='Posição Y de spawn'),
        DeclareLaunchArgument('z', default_value='0.0', description='Posição Z de spawn'),
        DeclareLaunchArgument('urdf_package', default_value='camaro_description', description='Pacote ROS 2 onde fica o URDF/Xacro do robô'),
        DeclareLaunchArgument('urdf_file', default_value='urdf/camaro.xacro', description='Caminho relativo do arquivo .xacro ou .urdf dentro do pacote'),
        OpaqueFunction(function=launch_setup)
    ])
