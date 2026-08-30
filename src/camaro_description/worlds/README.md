# 🌍 worlds/ — Mundos do Gazebo

Esta pasta contém os cenários (mundos) em que o Camaro é simulado.

---

## 📄 Arquivos

### `corridor_rooms.sdf` — Corredor com 4 salas ⭐ (padrão)

O mapa principal do projeto. Representa um ambiente interno com:

- Um **lobby** central de entrada
- Um **corredor** de ~4 metros de largura conectando os ambientes
- **4 salas** de ~5×8 metros com portas de ~2 metros de abertura

O corredor e as portas foram dimensionados com folga para o Camaro (footprint `0.6×0.46m`) conseguir manobrar com sua direção Ackermann.

**Plugins do mundo (obrigatórios no Gazebo Harmonic):**
- `gz-sim-physics-system` — Simulação de física
- `gz-sim-user-commands-system` — Permite spawnar objetos pelo terminal
- `gz-sim-scene-broadcaster-system` — Transmite a cena para o cliente visual
- `gz-sim-sensors-system` — Processa os sensores (LiDAR usa GPU para renderizar)

**Para usar:**
```bash
ros2 launch camaro_description gazebo.launch.py world:=corridor_rooms
```

---

### `museum.world` — Museu (legado)

Mundo alternativo em formato `.world` (Gazebo Classic). Pode ser usado, mas o `corridor_rooms.sdf` é o ambiente oficial de testes.

```bash
ros2 launch camaro_description gazebo.launch.py world:=museum
```

---

## 🗺️ Como criar um mundo novo

1. Abra o Gazebo e monte o ambiente visualmente (arraste paredes, objetos, etc.)
2. Salve como `.sdf` usando `File > Save World As`
3. Coloque o arquivo `.sdf` nesta pasta
4. Use com: `ros2 launch camaro_description gazebo.launch.py world:=/caminho/completo/para/seu_mundo.sdf`
