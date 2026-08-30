# 📦 camaro_description — Pacote Principal

Este é o único pacote ROS 2 do projeto. Todo o conteúdo da simulação — modelo do robô, mundos, configurações de navegação e scripts — fica aqui dentro.

---

## 🗂️ O que tem nesta pasta

| Pasta / Arquivo | O que é |
|---|---|
| `launch/` | Arquivos `.launch.py` para iniciar a simulação |
| `urdf/` | Modelo 3D e física do robô (Xacro + Gazebo plugins) |
| `config/` | Parâmetros de navegação, controle e sensores |
| `scripts/` | Teleoperador e utilitários Python |
| `worlds/` | Cenários/mapas do Gazebo Harmonic |
| `maps/` | Mapas gerados pelo SLAM para navegação autônoma |
| `meshes/` | Modelos 3D do robô em 3D (`.glb` e `.stl`) |
| `models/` | Objetos e móveis presentes nos cenários |
| `behavior_trees/` | Árvore de comportamento do Nav2 |
| `plugins/` | Plugin de recuperação Ackermann para o Nav2 |
| `waypoint_router/` | Scripts de roteamento de entregas |
| `src/` | Código-fonte C++ (compilado pelo CMake) |
| `include/` | Headers C++ dos nós compilados |
| `CMakeLists.txt` | Instruções de compilação do pacote |
| `package.xml` | Metadados e dependências do pacote |

---

## 🔧 Como compilar

```bash
cd ~/noblecamaro-main
colcon build --symlink-install
source install/setup.bash
```

> 💡 O `--symlink-install` cria links simbólicos em vez de copiar os arquivos, então mudanças em Python e YAML são refletidas imediatamente sem recompilar. Para mudanças em C++, recompile sempre.
