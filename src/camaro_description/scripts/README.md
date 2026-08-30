# 🕹️ scripts/ — Scripts Python

Esta pasta contém os scripts Python executáveis do projeto: o teleoperador e um utilitário de remapeamento de TF.

---

## 📄 Arquivos

### `camaro_teleop.py` — Teleoperador com Pygame

Interface gráfica para controlar o robô manualmente por **teclado** ou **joystick**. Usa a biblioteca **pygame** para capturar os inputs e publicar no tópico `cmd_vel` do robô.

**Como executar:**

```bash
# Para controlar o robô padrão (smart_camaro)
ros2 run camaro_description camaro_teleop.py --ros-args -r __ns:=/smart_camaro

# Para controlar outro robô em multi-simulação
ros2 run camaro_description camaro_teleop.py --ros-args -r __ns:=/camaro_a
```

**Controles:**

| Teclado | Ação |
|---|---|
| `W` | Avançar |
| `S` | Ré |
| `A` | Virar esquerda |
| `D` | Virar direita |
| `Espaço` | Parar imediatamente |

**Funcionalidades da interface:**
- **Modo RAMPA (toggle):** Ativa aceleração/desaceleração gradual em vez de resposta instantânea
- **Modos de velocidade:** Segurança (lento), Normal, Rápido — selecionáveis pelo botão no canto
- **Campo de tópico:** Exibe o tópico atual onde os comandos estão sendo publicados
- **Joystick:** Se um joystick estiver conectado, é detectado e assume o controle automaticamente

> ⚠️ A janela do pygame precisa estar em foco (clique nela) para os comandos funcionarem.

---

### `tf_remapper.py` — Remapeador de TF

Nó auxiliar que foi usado no sistema de single-robot para corrigir os nomes dos frames de TF vindos do Gazebo (que chegavam com prefixo `smart_camaro/`) removendo esse prefixo.

> ℹ️ **Na simulação multi-robô atual, este nó não é mais necessário.** O `spawn_robot.launch.py` configura o `robot_state_publisher` com `frame_prefix` corretamente, eliminando a necessidade de remapeamento manual. O arquivo é mantido por compatibilidade.
