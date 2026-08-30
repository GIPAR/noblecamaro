# 🗺️ maps/ — Mapas para Navegação

Esta pasta contém mapas pré-gerados do ambiente para uso com o Nav2 (navegação autônoma).

---

## 📄 Arquivos

Cada mapa é composto de **2 arquivos** que trabalham juntos:

### `corridor_rooms.pgm` — Imagem do mapa

Arquivo de imagem em escala de cinza onde:
- **Branco** = espaço livre (o robô pode passar)
- **Preto** = obstáculo (paredes, objetos)
- **Cinza** = área desconhecida

### `corridor_rooms.yaml` — Metadados do mapa

Arquivo de configuração que informa ao Nav2 como interpretar a imagem `.pgm`:
```yaml
image: corridor_rooms.pgm  # nome da imagem
resolution: 0.05           # cada pixel = 5cm do mundo real
origin: [x, y, theta]      # posição do canto inferior esquerdo no mundo
occupied_thresh: 0.65      # acima disso = obstáculo
free_thresh: 0.196         # abaixo disso = livre
```

---

## 🔄 Como usar um mapa salvo

```bash
ros2 launch camaro_description nav2.launch.py map_file:=/caminho/para/corridor_rooms.yaml
```

---

## 💾 Como gerar e salvar um novo mapa

1. Inicie o Gazebo:
   ```bash
   ros2 launch camaro_description gazebo.launch.py
   ```
2. Inicie o SLAM:
   ```bash
   ros2 launch camaro_description nav2.launch.py slam:=true
   ```
3. Controle o robô pelo teleoperador para mapear o ambiente
4. Quando o mapa estiver completo, salve:
   ```bash
   ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "name: {data: 'meu_mapa'}"
   ```
5. Mova os arquivos `meu_mapa.pgm` e `meu_mapa.yaml` para esta pasta
