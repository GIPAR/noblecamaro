# 🏎️ Smart Camaro — Robô de Delivery Autônomo

O **Smart Camaro** é um robô de delivery autônomo desenvolvido pelo **GIPAR (IFBA)** para operar em ambientes internos. Ele tem forma de Camaro e usa **direção Ackermann** (igual a um carro de verdade, não gira no próprio eixo).

Este repositório contém a simulação completa em **ROS 2 Jazzy** + **Gazebo Harmonic**, com:

- 🗺️ Mapeamento em tempo real com SLAM
- 🚗 Navegação autônoma via Nav2
- 🕹️ Teleoperador por teclado e joystick
- 👥 Suporte a **múltiplos robôs** na mesma simulação

---

## 🗂️ Estrutura do Repositório

```
noblecamaro-main/
├── README.md                    ← Você está aqui
├── SIMULAÇÃO.MD                 ← Tutorial completo de como rodar
├── src/
│   └── camaro_description/      ← Pacote principal do ROS 2
│       ├── launch/              ← Arquivos para iniciar a simulação
│       ├── urdf/                ← Modelo 3D e física do robô
│       ├── config/              ← Parâmetros de navegação e controle
│       ├── scripts/             ← Teleoperador e utilitários
│       ├── worlds/              ← Mundos (cenários) do Gazebo
│       ├── maps/                ← Mapas pré-gerados para navegação
│       ├── meshes/              ← Modelos 3D do robô (.glb / .stl)
│       ├── models/              ← Objetos extras para os mundos
│       ├── behavior_trees/      ← Lógica de decisão de navegação
│       ├── plugins/             ← Plugins de recuperação de rota
│       ├── waypoint_router/     ← Roteamento de waypoints de entrega
│       ├── src/                 ← Código C++ compilado
│       └── include/             ← Headers C++
```

> Cada subpasta dentro de `camaro_description/` tem um `README.md` próprio explicando o que ela faz.

---

## ⚙️ Pré-requisitos

- **Sistema Operacional:** Ubuntu 24.04
- **ROS 2:** Jazzy
- **Simulador:** Gazebo Harmonic

Se ainda não instalou, siga o tutorial oficial:
[https://docs.ros.org/en/jazzy/Installation.html](https://docs.ros.org/en/jazzy/Installation.html)

---

## 🚀 Início Rápido

Para rodar a simulação com **um robô**, abra o terminal e execute:

```bash
ros2 launch camaro_description gazebo.launch.py
```

Para rodar com **múltiplos robôs** (ex: 3 camaros), execute:

```bash
ros2 launch camaro_description multi_gazebo.launch.py robot_names:=camaro_a,camaro_b,camaro_c
```

📖 Para o tutorial completo (instalação, SLAM, Nav2, teleop), abra o arquivo:

```
SIMULAÇÃO.MD
```

---

## 🤝 Regras de Contribuição

Para manter o projeto organizado, **não faça commit diretamente na branch principal**:

- Crie uma branch com o nome do seu enfoque (`feature/meu-sensor`, `fix/navegacao`)
- Ou use a branch `Desenvolvimento`

---

## 👥 Sobre o Projeto

Desenvolvido pelo grupo **GIPAR** no Instituto Federal da Bahia (IFBA).
O robô físico é equipado com câmera **ZED 2** e **LiDAR** — a integração dos sensores reais está planejada para etapas futuras.
