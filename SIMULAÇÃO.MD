# CAMARO SIM

Tutorial de como utilizar o robô de entregas autônomo "Camaro" (GIPAR) em
um ambiente virtual chamado "Gazebo". Atualmente, está incluso no projeto
o mapeamento (SLAM), a navegação autônoma via Nav2 e o teleoperador para
controle manual do robô.

> ⚠️ Este tutorial cobre **apenas a simulação**. A parte física (Arduino,
> sensores reais, integração com o dashboard/LLM) fica para um tutorial à
> parte.

1 - O projeto ainda está em desenvolvimento (migração de ROS1 para ROS2
Jazzy em andamento), severas atualizações são esperadas ao longo deste
tempo.

2 - Contribuições novas devem ser feitas fora da branch principal (crie
uma branch própria ou use a branch "Desenvolvimento").

## 1 - Primeiros Passos 📋

É necessário instalar bibliotecas e diferentes dependências para o
correto funcionamento das simulações e pacotes. O projeto foi construído
utilizando o Ubuntu 24.04, o ROS2 Jazzy e o Gazebo Harmonic — logo,
possivelmente não funcionará em um sistema alternativo.

Primeiramente faça a instalação do ROS2 Jazzy, seguindo o seguinte
tutorial: (https://docs.ros.org/en/jazzy/Installation.html)

### 1.1 - Instalando Dependências Iniciais

Abra o terminal e cole as seguintes linhas de código:

```shell
sudo apt install python3-colcon-* \
    ros-jazzy-ros-gz \
    ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-slam-toolbox \
    ros-jazzy-nav2-map-server \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup
```

O Camaro usa direção Ackermann simulada pelo plugin nativo do Gazebo
Harmonic (`gz-sim-ackermann-steering-system`). Ele já vem embutido no
pacote `ros-jazzy-ros-gz-sim` instalado acima — **não é necessário
instalar nada separado para o Ackermann**, só garantir que o Gazebo
Harmonic esteja corretamente instalado junto do ROS2 Jazzy.

O teleoperador do Camaro usa **pygame** para capturar teclado/joystick.
Instale com:

```shell
pip install pygame --break-system-packages
```

(ou `sudo apt install python3-pygame`, se preferir pelo apt)

### 1.2 - Preparando o Workspace

Com os arquivos baixados deste GitHub, mova a pasta "noblecamaro-main"
para o diretório padrão do seu computador, e em ***um novo terminal***
use os seguintes comandos para compilar a simulação:

```shell
cd ~/noblecamaro-main/camaro_description && \
    colcon build --symlink-install
```

> Ajuste o caminho acima caso o `camaro_description` esteja em uma
> subpasta diferente dentro do `noblecamaro-main` no seu workspace.

Agora devemos permitir que nosso pacote seja encontrado pelo sistema,
junto com o ROS. Para isso, rode os seguintes comandos:

```shell
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && \
    echo "source ~/noblecamaro-main/camaro_description/install/setup.bash" >> ~/.bashrc && \
    echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc && \
    echo "echo "Terminal Ativado no Domínio do ROS: '"${ROS_DOMAIN_ID}"'"" >> ~/.bashrc
```

Obs: O `.bashrc` roda toda vez que um novo terminal é aberto, por isso,
os próximos comandos só vão funcionar depois de abrir ***um novo
terminal***.

## 2 - Simulação 🌎

### 2.1 - Abrindo o Mundo com o Camaro

Estes são os comandos básicos para rodar a simulação via terminal.
Primeiro, suba o mundo do Gazebo (o corredor com as salas, usado para os
testes de navegação e entrega):

```shell
ros2 launch camaro_description gazebo.launch.py world:=corridor_rooms
```

Em outro terminal, se quiser abrir o robô junto com o RViz2 para
visualizar TFs, sensores e o modelo (sem Nav2/SLAM ainda), use:

```shell
ros2 launch camaro_description display.launch.py
```

> Confira se os nomes dos argumentos (`world:=`, etc.) batem exatamente
> com os que estão nos seus arquivos de launch — ajuste se for
> diferente.

### 2.2 - Controlando pelo Teleoperador

Com o mundo e o robô já rodando, você pode controlar o Camaro
manualmente pelo teclado ou joystick:

```shell
ros2 run camaro_description camaro_teleop.py
```

Esse script usa **pygame** para capturar as teclas/joystick, então é
necessário ter uma janela do pygame em foco para os comandos serem
reconhecidos (não basta digitar direto no terminal).

### 2.3 - Inicializando o SLAM

Para mapear o ambiente em tempo real enquanto navega, suba o SLAM junto
com o RViz2. Normalmente isso é feito habilitando o SLAM no próprio
launch de navegação:

```shell
ros2 launch camaro_description nav2.launch.py slam:=true
```

Assim como na NARA, o mapa pode ser salvo diretamente pelo slam_toolbox:

```shell
ros2 service call /camaro/slam_toolbox/save_map slam_toolbox/srv/SaveMap "name: {data: 'my_map'}"
```

> Se o seu `nav2.launch.py` usar outro nome de argumento para ativar o
> SLAM (em vez de `slam:=true`), ou se o SLAM estiver num launch
> separado, me fala o nome certo que eu ajusto essa seção.

### 2.4 - Inicializando a Navegação Autônoma 🗺️

#### 2.4.1 - Navegação Autônoma com SLAM

Com o SLAM ativado (seção 2.3), o próprio `nav2.launch.py` já cuida da
navegação autônoma enquanto mapeia e se localiza em tempo real.

#### 2.4.2 - Nav2 com um Mapa Previamente Salvo

Quando já existe um mapa gerado e salvo no computador, suba o Nav2 sem o
SLAM, passando o mapa direto:

```shell
ros2 launch camaro_description nav2.launch.py map_file:=/coloque/o/caminho/do/arquivo/aqui/nome_do_seu_mapa.yaml
```

Nota: o Nav2 espera que a localização inicial do robô seja a coordenada
(0, 0) do mapa. Se não for, publique a pose inicial pelo "2D Pose
Estimate" no RViz2, ou mova o robô manualmente por um tempo até ele se
localizar corretamente via AMCL.

### 2.5 - Footprint Dinâmico e Recovery Inteligente 🧠

Duas coisas importantes do Nav2 configuradas no Camaro, especialmente
por causa da direção Ackermann (o robô não gira no próprio eixo):

**Footprint dinâmico:** o footprint (a "silhueta" que o Nav2 usa pra
saber onde o robô pode ou não passar) muda de tamanho/forma dependendo
do contexto — por exemplo, encolhe em corredores apertados ou portas
estreitas, e volta ao tamanho normal em espaços abertos. Isso evita que
o planejador rejeite caminhos válidos só porque o footprint "cheio" não
caberia, mesmo quando o robô conseguiria passar com folga real.

**Recovery inteligente:** quando o Camaro fica preso ou o planejador não
encontra caminho (situação comum com Ackermann, já que ele não consegue
girar no lugar como um robô diferencial), em vez de aplicar sempre a
mesma sequência genérica de recovery do Nav2 (girar no lugar, andar para
trás), o comportamento de recovery é adaptado à cinemática Ackermann —
priorizando manobras que o robô realmente consegue executar (marcha à
ré em linha reta, pequenos ajustes de ângulo de esterçamento) antes de
escalar para comportamentos mais agressivos.

> Se quiser, dá pra detalhar aqui os parâmetros exatos usados nos
> arquivos de configuração do Nav2 (`nav2_params.yaml`) para o footprint
> dinâmico e os plugins de recovery — me manda o arquivo de config que eu
> incluo os valores reais no tutorial.

## 3 - Encerrando a Simulação

Para fechar tudo de forma limpa, use `Ctrl+C` em cada terminal (Gazebo,
Nav2/SLAM, teleop) e aguarde o encerramento antes de fechar o terminal,
evitando processos do Gazebo travados em segundo plano.