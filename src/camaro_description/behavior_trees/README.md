# 🌳 behavior_trees/ — Árvores de Comportamento do Nav2

Esta pasta contém as **Behavior Trees (BT)** usadas para definir a lógica de navegação do Camaro no Nav2.

---

## 📄 Arquivos

### `camaro_nav.xml` — Árvore de navegação principal

Uma Behavior Tree é uma forma visual e estruturada de definir **como o robô toma decisões**. Em vez de programar `if/else` gigantes, cada comportamento é um "nó" na árvore e o Nav2 percorre essa árvore para decidir o que fazer.

A árvore do Camaro define:
1. Tentar navegar até o goal
2. Se falhar → tentar recovery (ré inteligente)
3. Se o recovery funcionar → tentar navegar de novo
4. Se tudo falhar → reportar falha

---

## 🤔 Por que o Camaro precisa de uma BT customizada?

O Nav2 vem com uma Behavior Tree padrão que funciona bem para robôs diferenciais (que giram no próprio eixo). O Camaro usa **direção Ackermann**, então:

- Não consegue girar no lugar
- Precisa de espaço para manobrar
- O recovery padrão (girar + ré) não funciona

A BT customizada direciona o Nav2 para usar o **AckermannRecovery** (definido em `plugins/`) quando o robô fica preso.

---

## 🔗 Onde é referenciado

O arquivo é carregado pelo `nav2_params.yaml` através do parâmetro:
```yaml
bt_navigator:
  ros__parameters:
    default_bt_xml_filename: "camaro_nav.xml"
```
