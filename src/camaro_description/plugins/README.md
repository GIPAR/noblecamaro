# 🔌 plugins/ — Plugin de Recovery Ackermann

Esta pasta registra o plugin de recovery customizado do Camaro para o Nav2.

---

## 📄 Arquivos

### `camaro_recovery_plugin.xml` — Registro do plugin

Este arquivo XML informa ao Nav2 que existe um plugin de recovery chamado `AckermannRecovery` e onde encontrá-lo (na biblioteca `ackermann_recovery_plugin`).

```xml
<library path="ackermann_recovery_plugin">
  <class name="camaro_nav/AckermannRecovery" .../>
</library>
```

---

## 🤔 O que é o AckermannRecovery?

Quando o Nav2 não consegue traçar um caminho (robô preso, espaço pequeno), ele aciona um **recovery behavior**. O comportamento padrão do Nav2 tenta girar o robô no lugar — o que **não funciona** com o Camaro, pois ele tem direção Ackermann.

O `AckermannRecovery` substitui esse comportamento por manobras reais:

1. **Ré simples** — recua em linha reta calculando o espaço disponível atrás
2. **Manobra de 3 pontos** — ré com esterço + avanço com esterço oposto (para espaços muito apertados)

---

## 🔗 Onde fica o código-fonte

O código C++ do plugin está em:
- `src/ackermann_recovery.cpp` — Implementação
- `include/camaro_description/ackermann_recovery.hpp` — Header

Ele é compilado pelo `CMakeLists.txt` como uma biblioteca compartilhada (`.so`) e registrado via `pluginlib`.

---

## 🔧 Como o Nav2 usa este plugin

No `config/nav2_params.yaml`:
```yaml
behavior_server:
  ros__parameters:
    behavior_plugins: ["AckermannRecovery"]
    AckermannRecovery:
      plugin: "camaro_nav/AckermannRecovery"
```
