------------------------------------------------------------------------------------------------------

Vamos começar pelo URDF/XACRO

Por que começamos pelo URDF?
O URDF é a "planta baixa" do robô. Antes de qualquer coisa o Gazebo precisa saber como o robô é — quantas rodas tem, onde ficam, qual o tamanho, onde fica o LiDAR. Sem isso não tem simulação.
O que mudou no URDF?
Só 3 coisas mudaram, o resto ficou igual:

O plugin que liga o Gazebo ao ROS mudou de nome
As <transmission> sumiram e viraram o bloco <ros2_control>
O sensor do LiDAR mudou de plugin antigo para sensor nativo

------------------------------------------------------------------------------------------------------

Segunda etapa é o controllers.yaml

Por que o controllers.yaml vem logo depois?
Porque depois de montar o robô fisicamente, o Gazebo precisa saber como movê-lo. O controllers.yaml é tipo o 
"manual de controle" — diz qual junta recebe comando de posição, qual recebe velocidade, qual o tamanho da roda, etc.

O que mudou no controllers.yaml?
No ROS1 eram vários arquivos separados, no ROS2 virou um arquivo só
Algumas opções mudaram de nome
Ganhou o joint_state_broadcaster que é obrigatório no ROS2

------------------------------------------------------------------------------------------------------

CMakeLists.txt — O que é?
É o "manual de instalação" do pacote. Ensina o ROS2 onde estão os arquivos do pacote para ele encontrar na hora de rodar.
O que mudou?

ROS1 usava catkin, ROS2 usa ament_cmake
No ROS2 precisa declarar explicitamente quais pastas instalar

------------------------------------------------------------------------------------------------------

package.xml — O que é?
É o "RG do pacote". Diz o nome, versão e quais outros pacotes ele precisa para funcionar.
O que mudou?

format="2" virou format="3"
catkin virou ament_cmake
<run_depend> virou <exec_depend>

------------------------------------------------------------------------------------------------------

display.launch.py — O que é?
É o arquivo que sobe o RViz2 para visualizar o robô antes de simular. Serve para checar se o URDF está correto, se as juntas estão no lugar certo e se a mesh aparece certinha.
O que mudou?

ROS1 usava XML .launch, ROS2 usa Python .launch.py
(find pacote) virou get_package_share_directory()
<node pkg=...> virou Node(package=...)
<param name=...> virou parameters=[...]

Resultado: Camaro apareceu no RViz2 com mesh e juntas funcionando ✅

------------------------------------------------------------------------------------------------------

gazebo.launch.py — O que é?
É o arquivo principal da simulação. Sobe o Gazebo Harmonic, spawna o robô dentro do mundo e liga os controllers.
O que mudou?

gazebo_ros/empty_world.launch virou gz sim empty.sdf
spawn_model virou ros_gz_sim create
Plugin da mesh mudou de package:// para file:// com caminho absoluto
Variável GZ_SIM_RESOURCE_PATH necessária para o Gazebo encontrar as meshes

Resultado: Camaro apareceu no Gazebo Harmonic ROS2 ✅

------------------------------------------------------------------------------------------------------

Código para rodar a simulação

ros2 launch camaro_description display.launch.py
ros2 launch camaro_description gazebo.launch.py

------------------------------------------------------------------------------------------------------

Ingredientes que o plugin Ackermann precisa (NOVA FORMA DE CONTROLAR O CAMARO PELA SIMULAÇÃO TOTALMENTE NATIVA):

🍰 Quais são as 4 juntas das rodas → pra saber quais rodas girar
🍰 Quais são as 2 juntas de direção → pra saber quais rodas virar
🍰 Wheel base → distância entre eixo dianteiro e traseiro (0.6m)
🍰 Wheel separation → distância entre roda esquerda e direita (0.46m)
🍰 Wheel radius → raio da roda (0.1m)

O plugin faz o resto sozinho:

Calcula o ângulo de cada roda dianteira (geometria Ackermann)
Publica odometria
Aceita /cmd_vel automaticamente

------------------------------------------------------------------------------------------------------

Vamos criar o Bridge no gazebo.launch.py
Por que precisamos?
O Gazebo e o ROS2 falam línguas diferentes. O Gazebo só entende /model/steer_bot/cmd_vel e o ROS2 fala /cmd_vel. O bridge é o tradutor entre os dois.
O que é o Bridge?
É um nó — um programa que fica rodando em segundo plano escutando o /cmd_vel do ROS2 e repassando pro Gazebo no formato que ele entende.
O que é um Nó?
É um programa com uma função específica. Igual funcionários numa empresa — cada um faz uma coisa. O bridge é o funcionário tradutor.
O que muda no código?
Só adicionamos mais um Node() no gazebo.launch.py — igual os outros que já estão lá. Nada mais muda!
Resultado esperado:
Conseguir controlar o Camaro com ros2 topic pub /cmd_vel e futuramente com teleop e Nav2 ✅

------------------------------------------------------------------------------------------------------

CURIOSIDADE SOBRE O ACKERMAN STEERING CONTROLLER E SUA MOVIMENTAÇÃO
As rodas dianteiras devem virar automaticamente (a interna vira um pouco mais que a externa → efeito Ackermann real).

------------------------------------------------------------------------------------------------------
