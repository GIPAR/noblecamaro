import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg = get_package_share_directory('camaro_description')
    xacro_file = os.path.join(pkg, 'urdf', 'camaro.xacro')
    robot_description = xacro.process_file(xacro_file).toxml()

    # Escolha do mundo: ros2 launch ... gazebo.launch.py world:=corridor_rooms_high.sdf
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='corridor_rooms_high.sdf',
        description='Arquivo de mundo dentro de worlds/'
    )
    world_file = PathJoinSubstitution([pkg, 'worlds', LaunchConfiguration('world')])

    # === GAZEBO SIM ===
    # GZ_HEADLESS=1 roda só o servidor (sem GUI) — útil para testes/CI
    gz_args = ['gz', 'sim', '-r']
    if os.environ.get('GZ_HEADLESS', '0') == '1':
        gz_args.append('-s')
    gz_args.append(world_file)
    gz_sim = ExecuteProcess(
        cmd=gz_args,
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

    # === SPAWN DO ROBÔ NO GAZEBO (na base: home_base fica no meio
    # do lobby, longe da parede p/ nao colidir: x=-4.0, y=0) ===
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'smart_camaro',
            '-topic', '/robot_description',
            '-x', '-4.0',
            '-y', '0.0',
            '-z', '0.0'
        ],
        output='screen'
    )

    # === BRIDGE PRINCIPAL: GAZEBO ↔ ROS 2 ===
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/model/smart_camaro/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/model/smart_camaro/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/model/smart_camaro/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
            '/world/default/model/smart_camaro/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model',
            '/lidarA2/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/zed/zed_node/rgb/image_raw/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/zed/zed_node/rgb/image_raw/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/camera_user/image/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        remappings=[
            ('/model/smart_camaro/cmd_vel', '/cmd_vel'),
            ('/model/smart_camaro/odometry', '/odom_gz'),
            ('/model/smart_camaro/tf', '/tf_gz'),
            ('/world/default/model/smart_camaro/joint_state', '/joint_states'),
            ('/lidarA2/scan', '/scan'),
            # Nuvem de pontos da ZED 2i no padrão do driver real
            ('/zed/zed_node/rgb/image_raw/points', '/zed/zed_node/points'),
        ],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # === BRIDGE DO CLOCK: CRÍTICO para use_sim_time funcionar ===
    # Sem esse nó, todos os outros com use_sim_time ficam sem referência de tempo
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
        ],
        output='screen'
    )

    # === BRIDGE DE IMAGENS (ros_gz_image image_bridge) ===
    # Imagens → ROS 2 nos mesmos nomes de tópico (padrão ZED e camera_user)
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        name='image_bridge',
        arguments=[
            '/zed/zed_node/rgb/image_raw/image',
            '/zed/zed_node/rgb/image_raw/depth_image',
            '/camera_user/image',
            '--ros-args', '-r',
            '/zed/zed_node/rgb/image_raw/image:=/zed/zed_node/rgb/image_raw',
        ],
        output='screen'
    )

    # === FRAME REMAPPER (TF + ODOM) ===
    frame_remapper = Node(
        package='camaro_description',
        executable='tf_remapper.py',
        name='frame_remapper',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # === WEB VIDEO SERVER: expõe as câmeras (ZED + camera_user) via HTTP ===
    # Dashboard (camaro_dashboard) consome em:
    #   http://localhost:8080/stream?topic=/zed/zed_node/rgb/image_raw
    # ou via proxy do Flask: http://localhost:5000/api/camera/stream?topic=...
    web_video_server = Node(
        package='web_video_server',
        executable='web_video_server',
        name='web_video_server',
        parameters=[{'port': 8080}],
        output='screen'
    )

    # === ROSBRIDGE: odometria para o dashboard via ws://localhost:9090 ===
    # (antes era preciso abrir outro terminal com
    #  `ros2 launch rosbridge_server rosbridge_websocket_launch.xml`;
    #  agora sobe junto com a simulação)
    rosbridge = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        parameters=[{'port': 9090}],
        output='screen'
    )

    # === DEPTH VIZ: converte a profundidade float32 da ZED em imagem
    # colorida (rgb8) que o web_video_server/dashboard conseguem exibir:
    #   /zed/zed_node/rgb/image_raw/depth_image  (32FC1, metros)
    #     -> /zed/zed_node/rgb/depth_image_viz   (rgb8, TURBO)
    depth_viz = Node(
        package='camaro_description',
        executable='depth_viz_node.py',
        name='depth_viz',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        world_arg,
        gz_sim,
        robot_state_publisher_node,
        spawn_entity,
        bridge,
        clock_bridge,
        frame_remapper,
        image_bridge,
        web_video_server,
        rosbridge,
        depth_viz,
    ])
