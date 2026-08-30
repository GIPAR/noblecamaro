# 📖 Tutorial de Simulação — Smart Camaro

Guia completo para rodar o **Camaro Delivery** no Gazebo Harmonic com ROS 2 Jazzy.
Leia do começo ao fim na primeira vez. Nas próximas, use como cola rápida! 🏎️

---

## 📋 Índice

1. [Pré-requisitos e Instalação](#1--pré-requisitos-e-instalação)
2. [Preparando o Workspace](#2--preparando-o-workspace)
3. [Rodando a Simulação](#3--rodando-a-simulação)
4. [Controlando o Robô (Teleop)](#4--controlando-o-robô-teleop)
5. [Múltiplos Robôs na Mesma Simulação](#5--múltiplos-robôs-na-mesma-simulação)
6. [Mapeamento com SLAM](#6--mapeamento-com-slam)
7. [Navegação Autônoma (Nav2)](#7--navegação-autônoma-nav2)
8. [Recursos Avançados](#8--recursos-avançados)
9. [Encerrando a Simulação](#9--encerrando-a-simulação)
10. [Problemas Comuns (FAQ)](#10--problemas-comuns-faq)

---

## 1 — Pré-requisitos e Instalação

> ⚠️ O projeto foi construído no **Ubuntu 24.04** com **ROS 2 Jazzy** e **Gazebo Harmonic**. Não é garantido que funcione em outros sistemas.

### 1.1 — Instalar o ROS 2 Jazzy

Siga o tutorial oficial (se ainda não instalou):
👉 [https://docs.ros.org/en/jazzy/Installation.html](https://docs.ros.org/en/jazzy/Installation.html)

### 1.2 — Instalar as dependências do projeto

Abra o terminal e cole tudo de uma vez:

```bash
sudo apt install python3-colcon-* \
    ros-jazzy-ros-gz \
    ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-slam-toolbox \
    ros-jazzy-nav2-map-server \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-laser-filters
```

### 1.3 — Instalar o Pygame (teleoperador)

```bash
pip install pygame --break-system-packages
```

---

## 2 — Preparando o Workspace

Faça isso **apenas uma vez** após clonar o repositório.

### 2.1 — Compilar o pacote

```bash
cd ~/noblecamaro-main
colcon build --symlink-install
```

> ⏳ A compilação demora alguns minutos na primeira vez. Aguarde até aparecer `Summary: X packages finished`.

### 2.2 — Configurar o terminal (source)

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
echo "source ~/noblecamaro-main/install/setup.bash" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc
source ~/.bashrc
```

> 💡 Você só precisa fazer isso uma vez. Depois, todo terminal novo já vai encontrar o pacote automaticamente.

---

## 3 — Rodando a Simulação

### 3.1 — Simulação padrão (1 robô)

Este é o comando principal. Ele abre o Gazebo Harmonic com o mapa `corridor_rooms` e spawna um Camaro.

```bash
ros2 launch camaro_description gazebo.launch.py
```

**Argumentos opcionais:**

| Argumento | Padrão | O que faz |
|---|---|---|
| `world:=` | `corridor_rooms` | Troca o mapa do Gazebo (`corridor_rooms` ou `museum`) |
| `robot_name:=` | `smart_camaro` | Nome interno do robô no Gazebo |
| `robot_namespace:=` | `smart_camaro` | Namespace dos tópicos ROS 2 |
| `x:=` `y:=` `z:=` | `0 0 0` | Posição de spawn do robô |

**Exemplo com argumento:**
```bash
ros2 launch camaro_description gazebo.launch.py world:=museum
```

---

## 4 — Controlando o Robô (Teleop)

Com a simulação aberta, **em outro terminal**, rode o teleoperador:

```bash
ros2 run camaro_description camaro_teleop.py --ros-args -r __ns:=/smart_camaro
```

Uma janela do **pygame** vai abrir. **Clique nela** para dar foco e então use:

| Tecla | Ação |
|---|---|
| `W` | Andar para frente |
| `S` | Ré |
| `A` | Virar à esquerda |
| `D` | Virar à direita |
| `Espaço` | Freio de emergência |

> 🎮 Se tiver um joystick conectado, ele é detectado automaticamente e assume o controle.

---

## 5 — Múltiplos Robôs na Mesma Simulação

> ✨ **Novidade!** Agora é possível spawnar vários robôs na mesma simulação sem criar nada manualmente.

### 5.1 — Iniciar com múltiplos robôs

Passe os nomes dos robôs separados por vírgula no argumento `robot_names`:

```bash
ros2 launch camaro_description multi_gazebo.launch.py robot_names:=camaro_a,camaro_b,camaro_c
```

Isso vai:
- Abrir o Gazebo com o mapa padrão
- Spawnar **3 robôs** automaticamente, espaçados 2 metros no eixo Y
- Criar tópicos separados para cada um (ex: `/camaro_a/cmd_vel`, `/camaro_b/cmd_vel`)

**Argumentos disponíveis:**

| Argumento | Padrão | O que faz |
|---|---|---|
| `robot_names:=` | `smart_camaro_1,smart_camaro_2` | Lista de nomes separados por vírgula |
| `world:=` | `corridor_rooms` | Mapa do Gazebo |

### 5.2 — Controlar cada robô separadamente

Abra um terminal pra cada robô:

```bash
# Terminal 1 — controla o camaro_a
ros2 run camaro_description camaro_teleop.py --ros-args -r __ns:=/camaro_a

# Terminal 2 — controla o camaro_b
ros2 run camaro_description camaro_teleop.py --ros-args -r __ns:=/camaro_b

# Terminal 3 — controla o camaro_c
ros2 run camaro_description camaro_teleop.py --ros-args -r __ns:=/camaro_c
```

### 5.3 — Ver todos os tópicos criados

```bash
ros2 topic list
```

Você verá tópicos como:
```
/camaro_a/cmd_vel
/camaro_a/odom
/camaro_a/scan
/camaro_b/cmd_vel
/camaro_b/odom
...
```

### 5.4 — Adicionar o Camaro na simulação de um amigo

Se a simulação do seu amigo já estiver rodando com o Gazebo aberto, ele pode spawnar o Camaro no mundo dele com:

```bash
ros2 launch camaro_description spawn_robot.launch.py \
    robot_name:=smart_camaro \
    robot_namespace:=smart_camaro \
    x:=2.0 y:=0.0 z:=0.1
```

> 📦 O seu amigo só precisa ter o pacote `camaro_description` compilado no workspace dele.

---

## 6 — Mapeamento com SLAM

O SLAM mapeia o ambiente em tempo real enquanto você controla o robô. **Primeiro inicie o Gazebo** (seção 3), depois em outro terminal:

```bash
ros2 launch camaro_description nav2.launch.py slam:=true
```

O RViz2 vai abrir automaticamente — você verá o mapa sendo construído enquanto o robô se move.

### Salvar o mapa

Quando o mapa estiver bom, salve assim:

```bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "name: {data: 'meu_mapa'}"
```

Isso cria dois arquivos (`meu_mapa.pgm` e `meu_mapa.yaml`) na pasta atual.

---

## 7 — Navegação Autônoma (Nav2)

Com um mapa já salvo, você pode fazer o robô navegar sozinho.

**Passo 1:** Inicie o Gazebo:
```bash
ros2 launch camaro_description gazebo.launch.py
```

**Passo 2:** Inicie o Nav2 com o mapa:
```bash
ros2 launch camaro_description nav2.launch.py map_file:=/caminho/para/meu_mapa.yaml
```

**Passo 3:** No RViz2 que abriu:
1. Clique em **"2D Pose Estimate"** e marque no mapa onde o robô está
2. Clique em **"Nav2 Goal"** e marque onde o robô deve ir
3. O robô vai navegar sozinho! 🎉

> 📍 O Nav2 precisa saber a posição inicial do robô para funcionar. Se o mapa ficou "perdido", use o "2D Pose Estimate" para corrigir.

---

## 8 — Recursos Avançados

### Footprint Dinâmico

O Camaro ajusta automaticamente o tamanho da sua "silhueta" de colisão para caberem em corredores e portas mais estreitas. Não é necessário configurar nada — acontece sozinho.

### Recovery Inteligente (Ackermann)

Quando o robô fica preso, em vez de tentar girar no próprio eixo (o que não funciona com Ackermann), ele executa manobras reais como:
- Ré em linha reta
- Manobra de 3 pontos (ré com esterço)

Isso é gerenciado automaticamente pelo Nav2.

---

## 9 — Encerrando a Simulação

Para fechar tudo de forma limpa, pressione `Ctrl + C` em cada terminal aberto e aguarde os processos encerrarem antes de fechar o terminal.

> ⚠️ Fechar o terminal sem `Ctrl + C` pode deixar processos do Gazebo rodando em segundo plano. Se isso acontecer, use:
> ```bash
> pkill -f gz
> ```

---

## 10 — Problemas Comuns (FAQ)

**❓ O Gazebo abriu mas o robô não apareceu**
- Aguarde alguns segundos — o spawn pode demorar
- Verifique se fez o `source install/setup.bash` antes de rodar

**❓ O teleoperador abre mas o robô não se move**
- Confirme que a janela do pygame está em foco (clique nela)
- Verifique se o namespace está correto: `--ros-args -r __ns:=/smart_camaro`

**❓ "Package not found" na compilação**
- Execute `sudo apt install ros-jazzy-<nome-do-pacote>` para o pacote faltante
- Rode `colcon build --symlink-install` novamente

**❓ O Lidar não aparece no RViz2**
- Verifique se o tópico `/smart_camaro/scan` existe com `ros2 topic list`
- Reinicie o launch do Gazebo

**❓ O SLAM não inicia**
- O SLAM deve ser iniciado **depois** do Gazebo estar rodando
- Aguarde o Gazebo carregar completamente antes de rodar o nav2.launch.py