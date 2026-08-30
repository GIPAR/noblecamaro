# 🤖 urdf/ — Modelo do Robô

Esta pasta contém a definição completa do robô: sua estrutura física, juntas, rodas, sensores e os plugins do Gazebo que fazem ele se mover e publicar dados.

---

## 📄 Arquivos

### `camaro.xacro` — Estrutura física do robô

**Xacro** é um formato de XML que permite usar variáveis e includes. Este arquivo define todo o esqueleto do Camaro:

- **`base_link`** — Chassi principal com a mesh 3D do Camaro
- **`front_left/right_wheel_steering_link`** — Links de direção (giram para virar)
- **`front_left/right_wheel_link`** — Rodas dianteiras
- **`rear_left/right_wheel_link`** — Rodas traseiras
- **`lidarA2`** — Link do sensor LiDAR montado na frente

**Argumento especial:**

```xml
<xacro:arg name="prefix" default=""/>
```

Este argumento é usado para **multi-robô**: quando um namespace é passado (ex: `camaro_a/`), todos os nomes de links e frames recebem esse prefixo, evitando conflitos entre robôs.

---

### `camaro.gazebo` — Plugins e comportamento no Gazebo

Enquanto o Xacro define a **estrutura**, este arquivo define o **comportamento** dentro do Gazebo:

#### Plugin de Direção Ackermann
```xml
<plugin filename="gz-sim-ackermann-steering-system" ...>
```
Controla as 4 rodas e 2 juntas de direção. Recebe comandos de velocidade linear e angular (`cmd_vel`) e converte para velocidades e ângulos de cada roda usando a geometria Ackermann real.

**Parâmetros importantes:**
- `wheel_base: 0.6` — distância entre eixos (metros)
- `wheel_separation: 0.46` — distância entre rodas do mesmo eixo
- `wheel_radius: 0.1` — raio de cada roda
- `max_velocity: 5` — velocidade máxima (m/s)

#### Plugin Joint State Publisher
Publica o estado de todas as juntas para que o ROS 2 saiba em que posição estão as rodas e a direção.

#### Plugin do LiDAR (GPU)
Sensor laser 2D que varre 360° com 360 pontos por rotação, alcance de 0.3 a 30 metros. Publica no tópico `scan`.

---

## 🔗 Como eles se conectam

```
camaro.xacro  ──include──▶  camaro.gazebo
      │
      ▼
launch/spawn_robot.launch.py  (lê e processa via xacro.process_file())
      │
      ▼
/robot_description topic  ──▶  Gazebo (spawn) + robot_state_publisher (TF)
```
