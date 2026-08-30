# 🚀 launch/ — Arquivos de Inicialização

Esta pasta contém todos os arquivos `.launch.py` do projeto. Cada um serve para iniciar a simulação de uma forma diferente.

---

## 📄 Arquivos

### `gazebo.launch.py` — Simulação principal (1 robô)

O ponto de entrada padrão. Abre o Gazebo Harmonic, cria a ponte de comunicação com o ROS 2 e spawna um único robô no mundo.

```bash
ros2 launch camaro_description gazebo.launch.py
```

**Argumentos:**

| Argumento | Padrão | Descrição |
|---|---|---|
| `world:=` | `corridor_rooms` | Nome do mundo (sem extensão) ou caminho completo |
| `robot_name:=` | `smart_camaro` | Nome do modelo no Gazebo |
| `robot_namespace:=` | `smart_camaro` | Namespace dos tópicos ROS 2 |
| `x:=` `y:=` `z:=` | `0 0 0` | Posição de spawn |
| `spawn_robot:=` | `true` | Se `false`, só abre o Gazebo sem spawnar ninguém |

---

### `spawn_robot.launch.py` — Spawnar 1 robô avulso

Usado para **adicionar um robô a uma simulação já em andamento** (ex: o amigo quer o seu robô no Gazebo dele). Não abre o Gazebo — apenas injeta o robô.

```bash
ros2 launch camaro_description spawn_robot.launch.py \
    robot_name:=smart_camaro \
    robot_namespace:=smart_camaro \
    x:=2.0 y:=0.0 z:=0.1
```

**Argumentos:**

| Argumento | Padrão | Descrição |
|---|---|---|
| `robot_name:=` | `smart_camaro` | Nome do modelo no Gazebo (deve ser único) |
| `robot_namespace:=` | `smart_camaro` | Namespace dos tópicos ROS 2 (deve ser único) |
| `x:=` `y:=` `z:=` | `0 0 0` | Posição de spawn no mundo |

Este launch cria automaticamente:
- `robot_state_publisher` com o prefixo de TF correto
- `ros_gz_bridge` para traduzir os tópicos Gazebo → ROS 2

---

### `multi_gazebo.launch.py` — Múltiplos robôs dinâmicos ✨

Abre o Gazebo e spawna **quantos robôs você quiser** de uma vez só, calculando automaticamente o espaçamento entre eles.

```bash
ros2 launch camaro_description multi_gazebo.launch.py robot_names:=camaro_a,camaro_b,camaro_c
```

**Argumentos:**

| Argumento | Padrão | Descrição |
|---|---|---|
| `robot_names:=` | `smart_camaro_1,smart_camaro_2` | Nomes separados por vírgula |
| `world:=` | `corridor_rooms` | Mundo do Gazebo |

**Como funciona internamente:**
1. Lê a lista de nomes (ex: `camaro_a,camaro_b,camaro_c`)
2. Para cada nome, calcula uma posição Y com espaçamento de 2 metros
3. Chama o `spawn_robot.launch.py` uma vez para cada robô

---

### `nav2.launch.py` — Navegação autônoma

Inicia o stack completo do **Nav2** com AMCL (localização), planejador de rotas, controlador e comportamentos de recovery adaptados para o Camaro Ackermann. Deve ser rodado **com o Gazebo já aberto**.

```bash
# Com um mapa salvo (navegação)
ros2 launch camaro_description nav2.launch.py map_file:=/caminho/para/meu_mapa.yaml

# Com SLAM (mapeamento em tempo real)
ros2 launch camaro_description nav2.launch.py slam:=true
```

---

### `reset_robot.launch.py` — Resetar Posição do Robô 🔄

Teleporta um robô de volta para a posição inicial (ou personalizada) no Gazebo sem reiniciar o simulador.

```bash
ros2 launch camaro_description reset_robot.launch.py robot_name:=camaro_a x:=0.0 y:=0.0
```

**Argumentos:**

| Argumento | Padrão | Descrição |
|---|---|---|
| `robot_name:=` | `smart_camaro` | Nome do robô a ser resetado |
| `world:=` | `corridor_rooms` | Nome do mundo no Gazebo |
| `x:=` `y:=` `z:=` | `0.0 0.0 0.1` | Posição de destino |

---

## 🔁 Fluxo típico de uso

```
Terminal 1: gazebo.launch.py      ← Gazebo + spawn do robô
Terminal 2: camaro_teleop.py      ← Controle manual
Terminal 3: nav2.launch.py        ← SLAM ou Navegação
(Terminal 4: reset_robot.launch.py se o robô capotar/travar)
```
