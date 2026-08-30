# 📍 waypoint_router/ — Roteador de Waypoints

Esta pasta contém scripts Python para **planejar e otimizar rotas de entrega** entre pontos pré-definidos no mapa.

---

## 📄 Arquivos

### `rooms_config.py` — Configuração dos quartos/salas

Define as coordenadas dos **pontos de parada** (waypoints) no mapa, com um nome amigável para cada um:

```python
ROOMS = {
    "sala_a": {"x": 5.0, "y": 2.0, "theta": 0.0},
    "sala_b": {"x": 10.0, "y": -3.0, "theta": 1.57},
    # ...
}
```

Edite este arquivo para adicionar ou mover os pontos de entrega de acordo com o seu mapa.

---

### `route_generator.py` — Gerador de rota

Gera uma sequência de waypoints a partir de uma lista de salas desejadas. Pode ser usado para criar uma missão simples de "ir de A para B para C".

---

### `evaluate_routes.py` — Avaliador de rotas

Calcula e compara diferentes rotas possíveis entre os waypoints, estimando distâncias e tempos de percurso. Útil para otimizar a ordem de entrega em missões com múltiplos destinos.

---

### `Routes.md` — Documentação das rotas

Arquivo de referência com a descrição das rotas disponíveis, os waypoints de cada uma e notas sobre o comportamento esperado do robô em cada trecho.

---

## 🚀 Como usar

1. Edite `rooms_config.py` com as coordenadas reais das salas do seu mapa
2. Use `route_generator.py` para criar uma rota
3. Envie os waypoints para o Nav2:
   ```bash
   # Exemplo usando o Nav2 waypoint follower
   ros2 action send_goal /follow_waypoints nav2_msgs/action/FollowWaypoints "{poses: [...]}"
   ```
