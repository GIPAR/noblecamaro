# ⚙️ config/ — Arquivos de Configuração

Esta pasta contém todos os parâmetros que controlam o comportamento do robô: navegação, controle de velocidade, filtros de sensor e visualização.

> 💡 Você não precisa mexer nesses arquivos para rodar a simulação básica. Eles são ajustados quando se quer **afinar o comportamento** do robô.

---

## 📄 Arquivos

### `nav2_params.yaml` — Parâmetros do Nav2

Arquivo central da navegação autônoma. Configura todos os nós do Nav2:

- **`amcl`** — Localização do robô dentro do mapa (Monte Carlo)
- **`controller_server`** — Controlador que segue o caminho calculado (usa DWB ou RPP adaptado para Ackermann)
- **`planner_server`** — Planejador de rota (NavFn ou Smac com suporte a Ackermann)
- **`collision_monitor`** — Para o robô se detectar obstáculo próximo
- **`behavior_server`** — Comportamentos de recovery (usa o plugin Ackermann customizado)
- **`local_costmap`** / **`global_costmap`** — Mapas de custo para desvio de obstáculos

---

### `slam_params.yaml` — Parâmetros do SLAM Toolbox

Configura o algoritmo de mapeamento em tempo real. Define a frequência de atualização do mapa, o tamanho da célula, e a política de loop closure.

---

### `slam.yaml` — Configuração simplificada de SLAM

Versão compacta dos parâmetros do SLAM para uso com `nav2.launch.py slam:=true`.

---

### `laser_filter.yaml` — Filtro do LiDAR

Define uma zona de exclusão no scan do laser para ignorar pontos que detectam o próprio corpo do robô (chassi, rodas). Sem esse filtro, o Nav2 poderia achar que o robô está dentro de um obstáculo.

```yaml
# Exemplo: ignora leituras entre 0.0 e 0.15 metros (o próprio corpo)
range_filter:
  lower_threshold: 0.0
  upper_threshold: 0.15
```

---

### `controllers.yaml` — Parâmetros do ros2_control

Configurações do controlador de juntas (não usado na simulação atual que usa o plugin nativo do Gazebo, mas mantido para uso com o robô físico).

---

### `nav2.rviz` — Layout do RViz2

Arquivo de configuração visual do RViz2. Define quais tópicos são exibidos, onde ficam os painéis, as cores do mapa de custo, etc. É carregado automaticamente pelo `nav2.launch.py`.

> 🎨 Para personalizar o que aparece no RViz2, você pode salvar um novo layout: `File > Save Config As` dentro do RViz2.
