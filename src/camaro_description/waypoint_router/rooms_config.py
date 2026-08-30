"""
Coordenadas das salas no mapa (frame 'map'), extraídas diretamente do
mundo `corridor_rooms.sdf` -- não são chute.

  - BASE   : pose do modelo 'home_base' (disco verde de spawn)
  - DOORS  : centro do vão de cada porta (entre os pares doorwall_a/b de
             cada sala), com yaw = direção de quem está atravessando a
             porta indo pra dentro da sala
  - ROOMS  : pose dos modelos 'checkpoint_a/b/c/d' (discos azuis, ponto
             de entrega em frente à pessoa de cada sala), mesmo yaw da
             porta correspondente (pra manter o robô alinhado reto desde
             a porta até o checkpoint)

ATENÇÃO -- o único valor que NÃO veio direto do SDF é o yaw da BASE: o
mundo não define orientação de spawn (isso é definido no
`gazebo.launch.py`/spawner). Deixei 0.0 (olhando pro corredor, +x) como
suposição -- ajuste se o spawn real for diferente.
"""
import math

# distância (m) do ponto de aproximação até a PORTA (não até o checkpoint)
# -- fica dentro do corredor (que tem ~4m de largura, y de -2 a 2), então
# o robô já entra alinhado antes de cruzar o vão da porta.
APPROACH_DISTANCE = 0.8

# (x, y, yaw)
BASE = (2.0, 0.0, 0.0)  # home_base -- yaw é suposição, ver nota acima

DOORS = {
    "A": (11.0, 2.0, 1.5708),
    "B": (11.0, -2.0, -1.5708),
    "C": (18.0, 2.0, 1.5708),
    "D": (18.0, -2.0, -1.5708),
}

ROOMS = {
    "A": (11.0, 5.6, 1.5708),   # checkpoint_a
    "B": (11.0, -5.6, -1.5708),  # checkpoint_b
    "C": (18.0, 5.6, 1.5708),   # checkpoint_c
    "D": (18.0, -5.6, -1.5708),  # checkpoint_d
}


def approach_point(pose, distance=APPROACH_DISTANCE):
    """Calcula um ponto 'distance' metros ANTES da pose dada (na mesma
    reta do yaw), pra o robô chegar alinhado. Usado com a pose da PORTA,
    não do checkpoint, pra alinhar antes de cruzar o vão."""
    x, y, yaw = pose
    ax = x - distance * math.cos(yaw)
    ay = y - distance * math.sin(yaw)
    return (ax, ay, yaw)