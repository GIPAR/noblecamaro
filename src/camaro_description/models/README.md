# 🏛️ models/ — Modelos de Objetos do Cenário

Esta pasta contém modelos 3D extras que **populam os cenários** do Gazebo — como paredes, móveis e estruturas dos ambientes de teste.

---

## 📁 Estrutura

```
models/
├── model.config        ← Registro do modelo principal
├── model.sdf           ← Definição SDF do modelo principal
├── bloco_G/            ← Modelo do Bloco G do IFBA
├── iscas_museum/       ← Modelo do museu (cenário alternativo)
└── meshes/             ← Malhas 3D usadas pelos modelos dos cenários
```

---

## 📄 Arquivos principais

### `model.config` e `model.sdf`

Definem o modelo padrão do cenário registrado no Gazebo. O `model.config` contém nome, versão e autor do modelo. O `model.sdf` descreve a geometria, colisões e materiais.

### `bloco_G/`

Modelo 3D do **Bloco G do IFBA** — usado para testes em ambientes que representam o campus real.

### `iscas_museum/`

Modelo do ambiente **museu** (ISCAS Museum) — cenário alternativo de navegação.

---

## 📦 Como o Gazebo encontra esses modelos

O Gazebo procura modelos nos caminhos definidos pela variável `GZ_SIM_RESOURCE_PATH`. Após compilar e dar `source install/setup.bash`, o ROS 2 configura esse caminho automaticamente para incluir a pasta `share/camaro_description/models/`.

---

## 🛠️ Como adicionar um modelo novo

1. Crie uma subpasta com o nome do modelo (ex: `models/sala_reunioes/`)
2. Adicione um `model.config` e um `model.sdf` dentro dela
3. Referencie no arquivo `.sdf` do mundo em `worlds/`
4. Recompile para que o ROS 2 registre o novo modelo
