import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration, PythonExpression

def generate_launch_description():
    robot_name_arg = DeclareLaunchArgument(
        'robot_name',
        default_value='smart_camaro',
        description='Nome do robô a ser resetado (ex: smart_camaro, camaro_a)'
    )
    
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='corridor_rooms',
        description='Nome do mundo no Gazebo'
    )
    
    x_arg = DeclareLaunchArgument('x', default_value='0.0', description='Posição X')
    y_arg = DeclareLaunchArgument('y', default_value='0.0', description='Posição Y')
    z_arg = DeclareLaunchArgument('z', default_value='0.1', description='Posição Z')

    reset_script = ExecuteProcess(
        cmd=[
            'python3',
            os.path.join(
                os.path.dirname(__file__),
                '../scripts/reset_robot.py'
            ),
            '--robot', LaunchConfiguration('robot_name'),
            '--world', LaunchConfiguration('world'),
            '--x', LaunchConfiguration('x'),
            '--y', LaunchConfiguration('y'),
            '--z', LaunchConfiguration('z')
        ],
        output='screen'
    )

    return LaunchDescription([
        robot_name_arg,
        world_arg,
        x_arg,
        y_arg,
        z_arg,
        reset_script
    ])
