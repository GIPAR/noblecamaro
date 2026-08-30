import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def launch_setup(context, *args, **kwargs):
    # Obtém a lista de robôs como string e divide por vírgula
    robot_names_str = context.perform_substitution(LaunchConfiguration('robot_names'))
    names = [name.strip() for name in robot_names_str.split(',') if name.strip()]
    
    urdf_pkg_val = context.perform_substitution(LaunchConfiguration('urdf_package'))
    urdf_file_val = context.perform_substitution(LaunchConfiguration('urdf_file'))

    pkg = get_package_share_directory('camaro_description')
    
    entities = []
    # Espaçamento de 2.0 metros entre os robôs no eixo Y para evitar colisão ao nascer
    y_spacing = 2.0
    
    for i, name in enumerate(names):
        y_pos = float(i) * y_spacing
        entities.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg, 'launch', 'spawn_robot.launch.py')
                ),
                launch_arguments={
                    'robot_name': name,
                    'robot_namespace': name,
                    'x': '0.0',
                    'y': str(y_pos),
                    'z': '0.1',
                    'urdf_package': urdf_pkg_val,
                    'urdf_file': urdf_file_val,
                }.items()
            )
        )
    return entities

def generate_launch_description():
    pkg = get_package_share_directory('camaro_description')

    # Argumento para definir a lista de robôs
    robot_names_arg = DeclareLaunchArgument(
        'robot_names',
        default_value='camaro_a,camaro_b,camaro_c',
        description='Lista de nomes de robôs separados por vírgula (ex: "camaro_a,camaro_b,camaro_c")'
    )

    # Argumento para selecionar o mundo
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='corridor_rooms',
        description='Nome do arquivo de mundo na pasta worlds (ex: "corridor_rooms" ou "museum") ou caminho completo'
    )

    # Argumento para abrir o RViz2 pré-configurado
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Abrir RViz2 pré-configurado para múltiplos robôs (true/false)'
    )

    # Argumentos para personalizar o modelo do robô (permitindo outros robôs)
    urdf_pkg_arg = DeclareLaunchArgument(
        'urdf_package',
        default_value='camaro_description',
        description='Pacote ROS 2 do modelo do robô (permite spawnar outros robôs)'
    )

    urdf_file_arg = DeclareLaunchArgument(
        'urdf_file',
        default_value='urdf/camaro.xacro',
        description='Caminho relativo do Xacro/URDF do robô dentro do pacote'
    )
    
    # OpaqueFunction para resolver o caminho completo do mundo e lançar o Gazebo
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

    # === RVIZ2 MULTI-ROBOT PRE-CONFIGURADO ===
    rviz_config_path = os.path.join(pkg, 'config', 'multi_camaro.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path],
        condition=IfCondition(LaunchConfiguration('rviz')),
        output='screen'
    )

    return LaunchDescription([
        robot_names_arg,
        world_arg,
        rviz_arg,
        urdf_pkg_arg,
        urdf_file_arg,
        gz_sim_opaque,
        clock_bridge,
        rviz_node,
        OpaqueFunction(function=launch_setup)
    ])
