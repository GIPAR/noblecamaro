"""
Gera as 24 rotas possíveis (permutações de A, B, C, D), cada uma:
  - começando na BASE
  - para cada sala: ponto de aproximação (corredor, alinhado com a porta)
    -> porta (cruza o vão) -> checkpoint (ponto de entrega dentro da sala)
  - terminando de volta na BASE
"""
from itertools import permutations
from rooms_config import BASE, DOORS, ROOMS, approach_point


def generate_routes():
    """
    Retorna uma lista de dicts:
    {
        "id": "R01",
        "order": ["A", "B", "C", "D"],
        "waypoints": [BASE, aprox_A, porta_A, checkpoint_A, aprox_B, ..., BASE]
    }
    """
    routes = []
    room_names = list(ROOMS.keys())  # ["A", "B", "C", "D"]

    for i, order in enumerate(permutations(room_names), start=1):
        waypoints = [BASE]
        for room in order:
            door = DOORS[room]
            waypoints.append(approach_point(door))
            waypoints.append(door)
            waypoints.append(ROOMS[room])
        waypoints.append(BASE)

        routes.append({
            "id": f"R{i:02d}",
            "order": list(order),
            "waypoints": waypoints,
        })
    return routes


if __name__ == "__main__":
    routes = generate_routes()
    print(f"Total de rotas geradas: {len(routes)}\n")
    for r in routes:
        print(f"{r['id']}: base -> {' -> '.join(r['order'])} -> base "
              f"({len(r['waypoints'])} waypoints, incluindo aproximações e portas)")