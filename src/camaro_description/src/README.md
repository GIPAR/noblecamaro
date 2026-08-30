# 💻 src/ e include/ — Código C++ Compilado

Estas pastas contêm o código-fonte C++ de nós e plugins que precisam de alta performance e não podem ser feitos em Python.

---

## 📄 Arquivos em `src/`

### `ackermann_recovery.cpp` — Implementação do Recovery

Código completo do plugin de recovery behavior adaptado para a cinemática Ackermann do Camaro. Este plugin é registrado no Nav2 e acionado quando o robô fica preso.

**O que ele faz:**
1. Lê o scan do LiDAR e analisa 4 zonas (frente, trás, esquerda, direita)
2. Calcula o espaço disponível atrás do robô
3. Decide entre:
   - **Ré simples** — se há espaço suficiente atrás
   - **Manobra de 3 pontos** — se o corredor é muito estreito
   - **Falha** — se não há saída possível
4. Publica `cmd_vel_nav` para executar a manobra escolhida

---

### `dynamic_footprint_node.cpp` — Nó de Footprint Dinâmico

Nó que ajusta em tempo real o tamanho do footprint (silhueta de colisão) do robô com base no contexto:

- Em **espaços abertos** → footprint completo (`0.6×0.46m`)
- Em **corredores estreitos** → footprint reduzido

Isso evita que o Nav2 rejeite caminhos válidos só porque o footprint completo não "caberia" matematicamente, quando na prática o robô conseguiria passar.

---

## 📄 Arquivos em `include/camaro_description/`

### `ackermann_recovery.hpp` — Header do plugin

Declara a classe `AckermannRecovery` com todos os métodos e atributos. O arquivo `.cpp` implementa o que está declarado aqui.

### `dynamic_footprint.hpp` — Header do nó de footprint

Declara a classe `DynamicFootprintNode`.

---

## 🔧 Como compilar

Qualquer mudança nos arquivos `.cpp` ou `.hpp` exige recompilação:

```bash
cd ~/noblecamaro-main
colcon build --symlink-install
source install/setup.bash
```

> ⚠️ Diferente dos scripts Python e arquivos YAML, mudanças em C++ **não são refletidas automaticamente** mesmo com `--symlink-install`. Sempre recompile após editar.
