# Waypoint Router — Camaro

Gera as 24 rotas possíveis entre as salas A, B, C, D (sempre saindo e
voltando pra base) e usa o planejador do Nav2 pra descobrir qual rota é
mais curta e tem menos curvas — priorizando entrar reto pelas portas, já
que o Camaro usa direção Ackermann e não vira no próprio eixo.

## 1. Onde colocar os arquivos

Dentro do seu workspace ROS2 (o mesmo onde está o pacote do Camaro),
crie um pacote Python simples só pra isso:

```bash
cd ~/seu_workspace/src
mkdir waypoint_router
```

Copie estes 4 arquivos pra dentro de `~/seu_workspace/src/waypoint_router/`:

```
waypoint_router/
├── rooms_config.py
├── route_generator.py
├── evaluate_routes.py
└── README.md
```

Não precisa de `colcon build` pra rodar esses scripts — eles são Python
puro que só *usa* as bibliotecas do ROS2/Nav2 já instaladas, não é um nó
que precisa ser "instalado" como pacote. Você roda direto com `python3`
(passo 4).

## 2. Dependências

Confirme que você já tem instalado (normalmente já vem com o Nav2):

```bash
sudo apt install ros-jazzy-nav2-simple-commander ros-jazzy-tf-transformations
```

## 3. Ajustar as coordenadas reais (`rooms_config.py`)

Os valores de `BASE` e `ROOMS` no arquivo `rooms_config.py` são fictícios.
Pra pegar os valores reais do seu mapa, com o Gazebo + Nav2 já rodando e
o mapa carregado:

**Opção mais fácil — clicar no RViz2:**
1. No RViz2, clique na ferramenta "Publish Point" (barra de cima).
2. Clique exatamente na posição da porta/entrega de cada sala no mapa.
3. Em outro terminal, rode `ros2 topic echo /clicked_point` e leia o
   `x` e `y` que aparecem.
4. Repita pra base e pras 4 salas.

**Para o `yaw` (direção que o robô deve olhar ao chegar):** pense em qual
direção é "reto pra dentro da porta" e estime em radianos:
- `0` → olhando para +x
- `1.57` → olhando para +y
- `3.14` → olhando para -x
- `-1.57` → olhando para -y

Se a porta estiver em ângulo diferente desses 4, pode usar qualquer valor
intermediário (ex: `0.78` ≈ 45°).

Edite as tuplas em `rooms_config.py`:

```python
BASE = (0.0, 0.0, 0.0)
ROOMS = {
    "A": (x_A, y_A, yaw_A),
    "B": (x_B, y_B, yaw_B),
    "C": (x_C, y_C, yaw_C),
    "D": (x_D, y_D, yaw_D),
}
```

Também dá pra ajustar `APPROACH_DISTANCE` (quantos metros antes da porta
o robô já deve estar alinhado e reto) — o padrão é 0.8m. Se o corredor até
a porta for curto, diminua um pouco; se for comprido e você quiser mais
margem pra alinhar, aumente.

## 4. Rodar

Em um terminal, suba a simulação completa (Gazebo + Nav2 + mapa +
localização), do mesmo jeito que você já faz normalmente pro Camaro.

Espere o Nav2 estar totalmente ativo (localização convergida, sem erros).

Em outro terminal:

```bash
cd ~/seu_workspace
source install/setup.bash
cd src/waypoint_router
python3 evaluate_routes.py
```

Isso vai:
1. Gerar as 24 rotas (`route_generator.py`).
2. Pedir ao planejador do Nav2 o caminho de cada trecho de cada rota
   (sem mover o robô — é só cálculo, roda rápido).
3. Imprimir no terminal a distância, número de curvas e tempo estimado
   de cada uma das 24 rotas.
4. No final, mostrar qual rota teve o melhor score (menor distância +
   menos curvas) e salvar tudo em `routes_metrics.json`.

Você pode testar só a geração de rotas sem precisar do Gazebo/Nav2
rodando, pra conferir se as 24 combinações estão certas:

```bash
python3 route_generator.py
```

## 5. Próximo passo (depois)

Quando você quiser, trocamos a escolha automática por score (no final de
`evaluate_routes.py`) por uma chamada a uma LLM, passando o
`routes_metrics.json` gerado e deixando ela justificar a escolha da
melhor rota.