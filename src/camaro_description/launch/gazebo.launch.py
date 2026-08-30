import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('camaro_description')

    # === ARGUMENTOS ===
    robot_name_arg = DeclareLaunchArgument(
        'robot_name',
        default_value='smart_camaro',
        description='Nome do robô no Gazebo'
    )
    
    robot_namespace_arg = DeclareLaunchArgument(
        'robot_namespace',
        default_value='smart_camaro',
        description='Namespace do ROS 2 do robô'
    )
    
    x_arg = DeclareLaunchArgument('x', default_value='0.0')
    y_arg = DeclareLaunchArgument('y', default_value='0.0')
    z_arg = DeclareLaunchArgument('z', default_value='0.0')
    
    spawn_robot_arg = DeclareLaunchArgument(
        'spawn_robot',
        default_value='true',
        description='Se True, spawna o robô padrão na simulação'
    )

    world_arg = DeclareLaunchArgument(
        'world',
        default_value='corridor_rooms',
        description='Nome do arquivo de mundo na pasta worlds ou caminho completo'
    )

    # === GAZEBO SIM ===
    def gz_sim_setup(context):
        world_val = context.perform_substitution(LaunchConfiguration('world'))
        if not world_val.endswith('.sdf') and not world_val.endswith('.world'):
            if world_val == 'corridor_rooms':
                world_path = os.path.join(pkg, 'worlds', 'corridor_rooms.sdf')
            else:
                world_path = os.path.join(pkg, 'worlds', f'{world_val}.world')
        else:
            world_path = world_val

        return [
            ExecuteProcess(
                cmd=['gz', 'sim', '-r', world_path],
                output='screen'
            )
        ]

    gz_sim_opaque = OpaqueFunction(function=gz_sim_setup)

    # === BRIDGE DO CLOCK (GLOBAL) ===
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
        ],
        output='screen'
    )

    # === SPAWN DO ROBÔ PADRÃO ===
    # Reutiliza o arquivo spawn_robot.launch.py condicionalmente
    spawn_robot_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg, 'launch', 'spawn_robot.launch.py')
        ),
        launch_arguments={
            'robot_name': LaunchConfiguration('robot_name'),
            'robot_namespace': LaunchConfiguration('robot_namespace'),
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'z': LaunchConfiguration('z'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('spawn_robot'))
    )

    return LaunchDescription([
        robot_name_arg,
        robot_namespace_arg,
        x_arg,
        y_arg,
        z_arg,
        spawn_robot_arg,
        world_arg,
        gz_sim_opaque,
        clock_bridge,
        spawn_robot_include,
    ])
