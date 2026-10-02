# Códigos Utilizados 🛠️

Comandos e configurações utilizados no projeto SMART CAMARO (ROS2 Jazzy + Gazebo Harmonic).

## Compilação do Workspace

```shell
cd ~/noblecamaro-main/src/camaro_description && \
    colcon build --symlink-install
```

Configuração no `.bashrc`:

```shell
source /opt/ros/jazzy/setup.bash
source ~/noblecamaro-main/install/setup.bash
export ROS_DOMAIN_ID=70
```

## Rodando a Simulação

| Passo | Comando |
|-------|---------|
| Subir o mundo (Gazebo) | `ros2 launch camaro_description gazebo.launch.py` |
| Abrir o robô + RViz (sem Nav2) | `ros2 launch camaro_description display.launch.py` |
| SLAM + Navegação + RViz | `ros2 launch camaro_description nav2.launch.py` |
| Navegação com mapa salvo | `ros2 launch camaro_description nav2.launch.py map_file:=/caminho/mapa.yaml` |
| Teleoperador (WASD/joystick) | `ros2 run camaro_description camaro_teleop.py` |

## Tópicos e Serviços

- Teleoperador publica em: `/cmd_vel`
- LiDAR bruto: `/scan` → filtrado: `/scan_filtered`
- Salvar mapa SLAM:
  ```shell
  ros2 service call /camaro/slam_toolbox/save_map slam_toolbox/srv/SaveMap "name: {data: 'my_map'}"
  ```

## Correção do Filtro do LiDAR

Problema: o LiDAR enxergava o próprio chassi (malha GLB maior que o collision box).

O LiDAR real fica **embaixo da frente, próximo do chão** — posição em
`camaro.xacro`:

```xml
<joint name="lidar_to_chassi" type="fixed">
  <parent link="base_link"/>
  <child link="lidarA2"/>
  <origin xyz="0.55 0 0.06" rpy="0 0 0"/>
</joint>
```

Correção aplicada em `config/laser_filter.yaml` (polígono na silhueta do robô,
robusto ao esterço Ackermann):

```yaml
scan_to_scan_filter_chain:
  ros__parameters:
    filter1:
      name: body_polygon
      type: laser_filters/LaserScanPolygonFilter
      params:
        polygon_frame: lidarA2
        polygon: "[[0.05, -0.37], [-0.05, -0.37], [-0.40, -0.37], [-0.60, -0.33], [-1.15, -0.33], [-1.15, 0.33], [-0.60, 0.33], [-0.40, 0.37], [-0.05, 0.37], [0.05, 0.37]]"
        polygon_padding: 0.05
        invert: false  # Remove pontos DENTRO do polígono
```

> ⚠️ Requisitos para o filtro funcionar:
> 1. No `nav2.launch.py`, carregar o YAML via `parameters=[...]` (não `arguments`)
> 2. O `name` do nó deve ser `scan_to_scan_filter_chain` (bater com a chave do YAML)
> 3. No RViz, exibir `/scan_filtered` (não `/scan`)

## Comandos de Diagnóstico

- Verificar se o nó do filtro está rodando:
  ```shell
  ros2 node list | grep scan_to_scan
  ```
- Verificar frequência do filtro:
  ```shell
  ros2 topic hz /scan_filtered
  ```
- Contar pontos removidos (NaN) no scan filtrado vs. bruto:
  ```shell
  ros2 topic echo /scan --field ranges --once | grep -c "nan"
  ros2 topic echo /scan_filtered --field ranges --once | grep -c "nan"
  ```
- Verificar transformção do LiDAR:
  ```shell
  ros2 run tf2_ros tf2_echo lidarA2 lidarA2
  ```