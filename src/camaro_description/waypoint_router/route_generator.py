"""
Gera TODAS as rotas possíveis: para cada subconjunto de salas (só A, só B,
A+C, A+B+D, as 4 juntas, etc.) e cada ordem possível de visitar esse
subconjunto, sempre começando e terminando na BASE.

Com 4 salas (A, B, C, D), isso dá:
  - 4 rotas de 1 sala   (A, B, C, D)
  - 12 rotas de 2 salas (A-B, A-C, A-D, B-A, B-C, ... todas as ordens)
  - 24 rotas de 3 salas
  - 24 rotas de 4 salas
  = 64 rotas no total

Cada rota, pra cada sala visitada, passa por: ponto de aproximação
(alinhado com a porta) -> porta (cruza o vão) -> checkpoint (ponto de
entrega dentro da sala).
"""
from itertools import combinations, permutations
from rooms_config import BASE, DOORS, ROOMS, approach_point


def generate_routes(active_rooms=None):
    """
    active_rooms: lista das salas que têm entrega hoje (ex: ["A", "C"]).
    Se não passar nada, usa todas as salas cadastradas em ROOMS.

    Retorna uma lista de dicts:
    {
        "id": "R01",
        "order": ["A", "B"],
        "num_rooms": 2,
        "waypoints": [BASE, aprox_A, porta_A, checkpoint_A, aprox_B, ..., BASE]
    }
    """
    if active_rooms is None:
        active_rooms = list(ROOMS.keys())  # ["A", "B", "C", "D"]

    routes = []
    counter = 1

    # subconjuntos de tamanho 1 até o total de salas ativas
    for size in range(1, len(active_rooms) + 1):
        for subset in combinations(active_rooms, size):
            for order in permutations(subset):
                waypoints = [BASE]
                for room in order:
                    door = DOORS[room]
                    waypoints.append(approach_point(door))
                    waypoints.append(door)
                    waypoints.append(ROOMS[room])
                waypoints.append(BASE)

                routes.append({
                    "id": f"R{counter:02d}",
                    "order": list(order),
                    "num_rooms": len(order),
                    "waypoints": waypoints,
                })
                counter += 1

    return routes


if __name__ == "__main__":
    routes = generate_routes()
    print(f"Total de rotas geradas: {len(routes)}\n")

    by_size = {}
    for r in routes:
        by_size.setdefault(r["num_rooms"], []).append(r)

    for size in sorted(by_size):
        print(f"--- rotas de {size} sala(s): {len(by_size[size])} ---")
        for r in by_size[size]:
            print(f"{r['id']}: base -> {' -> '.join(r['order'])} -> base")
        print()