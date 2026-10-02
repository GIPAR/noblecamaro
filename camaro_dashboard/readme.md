# Camaro Dashboard — Documentação Técnica Completa

> **Documento de referência para artigo científico e reprodução do projeto.**
> Descreve o `camaro_dashboard`: estação web de controle e delivery do robô
> autônomo **Camaro** — ideia geral, arquitetura, códigos, câmeras, chatbot,
> servidor, dependências, comandos e estado atual.

---

## 1. Resumo

O **Camaro Dashboard** é uma aplicação web que funciona como a "central de
operações" de um robô móvel autônomo voltado a **entregas (delivery)** de
pequenos componentes eletrônicos dentro de um ambiente interno (corredor com
quatro salas: A, B, C e D). Ele possui duas interfaces:

- **Visão do cliente** — vitrine de produtos, carrinho, checkout com destino,
  acompanhamento da entrega e assistente conversacional;
- **Visão do administrador (operador)** — telemetria em tempo real, câmeras
  do robô (RGB e profundidade da ZED 2i), fila de pedidos, histórico, fila de missões
  e assistente do operador.

O sistema foi projetado em camadas desacopladas: um **backend em Flask**
(API REST + banco SQLite + motor de simulação de entregas), um **frontend
estático** (HTML/CSS/JavaScript puro) e uma **ponte com o ROS 2 / Gazebo**
via `rosbridge` (odometria) e `web_video_server` (câmeras). Na fase atual,
tudo opera sobre **simulação** (Gazebo Harmonic + ROS 2 Jazzy); o objetivo
de longo prazo é conectar o mesmo painel ao **protótipo físico do Camaro em
tamanho real** — veículo com direção Ackermann, câmera ZED 2i e LiDAR — com
o mínimo de alterações, já que os tópicos ROS seguem o mesmo padrão de nomes.

---

## 2. Contexto e motivação

### 2.1. O projeto Camaro

O Camaro é um robô móvel com **direção Ackermann** (como um carro: rodas
dianteiras esterçam, traseiras são fixas), em migração de ROS 1 para
**ROS 2 Jazzy**, com simulação no **Gazebo Harmonic**. O pacote de simulação
chama-se `noblecamaro-main` (pacote ROS `camaro_description`) e inclui
modelo URDF/Xacro, mundos de corredor com salas, SLAM (slam_toolbox),
navegação autônoma (Nav2) e teleoperação manual.

### 2.2. Por que um dashboard?

Um robô de entrega precisa de mais do que navegação: precisa de **pedidos,
fila, operador, cliente e observabilidade**. O dashboard resolve isso em
uma página só, acessível de qualquer navegador da rede local, sem instalar
nada além do backend.

### 2.3. Premissa importante para o artigo

Embora o sistema modele um serviço real de delivery (pedido → confirmação →
trajeto → entrega → avaliação), **na fase atual ele opera somente em
simulação**: o deslocamento do robô é representado por um motor de
temporização no backend (seção 5.5), e não por navegação física. A
integração com o protótipo real — mesmo veículo Camaro, em tamanho real —
é o passo seguinte e está prevista na arquitetura (seção 11).

---

## 3. Arquitetura geral

```
                    ┌─────────────────────────────┐
                    │  Gazebo Harmonic (simulação)│
                    │  + ROS 2 Jazzy              │
                    │  tópicos: /odom, /scan,     │
                    │  /zed/.../image_raw,        │
                    │  /camera_user/image         │
                    └──────┬──────────────┬───────┘
                           │              │
              rosbridge     │              │  ros_gz_image (image_bridge)
              ws://:9090    │              │  + web_video_server :8080
                           │              │
                    ┌──────▼──────────────▼───────┐
                    │  Backend Flask (:5000)      │
                    │  REST / SQLite / simulação  │
                    │  de entregas / proxy MJPEG  │
                    └──────┬──────────────────────┘
                           │  HTTP + JSON
                    ┌──────▼──────────────────────┘
                    │  Frontend (navegador)       │
                    │  portal | cliente | admin   │
                    └─────────────────────────────┘
```

- **Porta 5000** — backend Flask; serve a API (`/api/*`) **e** os arquivos
  estáticos do site (o `index.html` é entregue pelo próprio Flask).
- **Porta 9090** — `rosbridge_websocket`: expõe tópicos ROS 2 via
  WebSocket; o backend assina a odometria (`/odom`).
- **Porta 8080** — `web_video_server`: converte tópicos de imagem ROS 2 em
  MJPEG/HTTP (`/stream?topic=...`) e JPEG único (`/snapshot?topic=...`).
- **Banco SQLite** (`backend/camaro.db`) — usuários, produtos, pedidos,
  telemetria, fila de missões, histórico de chat, padrões aprendidos pela
  IA e avaliações (feedback 1–5 estrelas).

### 3.1. Estrutura de pastas

```
camaro_dashboard/
├── index.html            # página única (portal + cliente + admin)
├── css/
│   ├── variables.css     # tema (cores, fontes, raios, sombras)
│   ├── styles.css        # base/layout
│   └── components.css    # componentes (cards, chat, câmeras, telemetria)
├── js/
│   ├── api.js            # cliente REST (fetch + token de sessão)
│   ├── state.js          # estado local + sincronização com backend
│   ├── app.js            # login, registro, roteamento de telas
│   ├── client.js         # vitrine, carrinho, checkout, rastreio, chat
│   └── admin.js          # telemetria, câmeras, fila, histórico, chat admin
├── assets/               # imagens dos produtos
├── backend/
│   ├── server.py         # API Flask + motor de entregas + proxy de câmera
│   ├── database.py       # SQLite (schema + consultas)
│   ├── llm.py            # orquestrador IA: Gemini + fallback por regras
│   ├── robot_bridge.py   # escuta /odom via rosbridge (thread dedicada)
│   ├── room_map.py       # coordenadas reais das salas (extraídas do SDF)
│   ├── config.py         # portas, chave Gemini, seeds de usuários/produtos
│   └── sessions.json     # sessões persistidas (sobrevivem a reinícios)
├── requirements.txt
└── start_backend.sh
```

---

## 4. Ideia principal do sistema (fluxo de ponta a ponta)

1. O **cliente** entra (`cliente` / `123`), monta o carrinho na vitrine
   (ou pede pelo chat em linguagem natural: *"adicione 2 ESP32 e 1 relé"*),
   escolhe o destino (Sala A–D) e confirma o pedido → status `pending`.
2. O **admin** (`admin` / `123`) vê o pedido na fila, com **sugestão
   proativa de rota em lote** quando há 2+ pedidos para destinos
   diferentes, e confirma o envio (individual ou em lote otimizado por
   distância).
3. O **motor de entregas** do backend executa a missão: `preparing` (5 s) →
   `delivering` (tempo proporcional à distância) → `delivered` → retorno à
   base (`returning`, 15 s) → `idle`; a telemetria (bateria, velocidade,
   distância, ETA) é atualizada a cada segundo.
4. O cliente acompanha tudo na tela de rastreio e, ao receber, **avalia de
   1 a 5 estrelas** — avaliação que alimenta as estatísticas de aprendizado
   da IA.
5. Durante a missão, o admin assiste às **câmeras RGB e de profundidade da ZED 2i**
   ao vivo e monitora odometria real e sala mais próxima no HUD.

---

## 5. Backend (Flask) — `backend/server.py`

Servidor em **Python/Flask** (`host 0.0.0.0`, porta **5000**,
`threaded=True`), com CORS liberado para `/api/*`. Serve tanto a API
quanto o frontend estático (rota `/` e fallback para `index.html`).

### 5.1. Autenticação por token

- `POST /api/auth/login` — valida usuário/senha (hash) e devolve um token
  UUID; o frontend o envia no header `X-Session-Token`.
- `POST /api/auth/logout` — invalida o token.
- Sessões são **persistidas em `sessions.json`**, logo sobrevivem a
  reinícios do servidor. Papéis: `client` (vê só os próprios pedidos) e
  `admin` (vê tudo, confirma envios, altera telemetria).

### 5.2. Principais endpoints REST

| Método | Rota | Papel |
|---|---|---|
| POST | `/api/auth/login`, `/api/auth/logout` | sessão |
| GET | `/api/products`, `/api/products/<id>` | catálogo |
| GET/POST | `/api/orders` | listar / criar pedido |
| GET | `/api/orders/<id>` | detalhe |
| PATCH | `/api/orders/<id>/status` | admin muda status (`pending`, `preparing`, `delivering`, `delivered`, `canceled`); `preparing` enfileira missão |
| GET | `/api/queue` | fila de missões + telemetria resumida |
| POST | `/api/queue/confirm-all` | admin confirma todos (modo individual) |
| POST | `/api/queue/batch-confirm` | admin autoriza rota em lote (ordena por distância) |
| GET/PATCH | `/api/telemetry` | telemetria (PATCH só admin) |
| GET | `/api/robot/status` | odometria real + sala mais próxima |
| POST | `/api/chat` | chatbot (texto + ações executáveis) |
| GET | `/api/chat/history` | histórico de conversa |
| GET | `/api/llm/status`, `/api/llm/training-stats` | modo da IA + estatísticas de aprendizado |
| POST | `/api/orders/<id>/feedback` | avaliação 1–5 estrelas + comentário |
| GET | `/api/camera/status` | câmeras: online? tópicos, URLs |
| GET | `/api/camera/stream?topic=...` | **proxy MJPEG** da câmera |
| GET | `/api/camera/snapshot?topic=...` | frame JPEG único |

### 5.3. Ponte com o robô — `robot_bridge.py`

Thread dedicada (daemon) que conecta ao `rosbridge` (`ws://localhost:9090`)
com `roslibpy`, assina **`/odom`** (`nav_msgs/Odometry`), converte o
quaternion de orientação em *yaw* e mantém o dicionário global
`robot_state` (`x, y, z, yaw, orientation, connected`). Se o ROS cair, a
thread tenta reconectar a cada 3 s; o endpoint `/api/robot/status`
combina a pose com a **sala mais próxima**, calculada em `room_map.py`
pelas coordenadas reais dos checkpoints extraídas do mundo SDF do Gazebo.

### 5.4. Mapa de salas — `room_map.py`

Coordenadas **reais** (não arbitrárias) do mundo `corridor_rooms.sdf`:
base de spawn, portas e checkpoints de entrega das Salas A–D
(ex.: A ≈ (11,0, 5,6), B ≈ (11,0, −5,6), C ≈ (18,0, 5,6), D ≈ (18,0, −5,6),
corredor de ~4 m de largura). Inclui `approach_point()` (ponto 0,8 m antes
da porta, para alinhamento do robô).

### 5.5. Motor de simulação de entregas

Como ainda não há navegação física, `server.py` emula a missão com
temporização em thread separada (`_run_delivery_engine`):

- `PREP_SECONDS = 5` (preparo na base), `TRAVEL_PER_METER = 3`
  (3 s por metro), `RETURN_SECONDS = 15` (volta à base);
- distâncias nominais: A = 3 m, C = 4 m, B = 6 m, D = 7 m;
- a cada segundo atualiza telemetria (distância restante, ETA, bateria
  com decaimento, velocidade) e transiciona os status do pedido;
- rotas **em lote** encadeiam paradas sem retorno intermediário à base,
  ordenadas da sala mais próxima à mais distante.

### 5.6. Banco de dados — `database.py` (SQLite)

Tabelas: `users`, `products` (+ `update_product_stock`), `orders` +
`order_items`, `chat_history`, `telemetry` (linha única, `id = 1`),
`mission_queue` (`single`/`batch`, `batch_group`), `ai_patterns`
(aprendizado: consulta normalizada → ação, com frequência),
`order_feedback` (nota 1–5 + comentário). Seeds iniciais: usuários
`admin`/`cliente` (senha `123`) e 3 produtos (ESP32, HC-SR04, módulo relé).

---

## 6. Frontend — `index.html` + `js/` + `css/`

Página única com três seções alternadas por login/papel:

1. **Portal** (`#portal-view`) — abas de login/registro e atalhos de acesso.
2. **Cliente** (`#client-view`) — banner de instruções, busca, grade de
   produtos, carrinho em modal (destino, imediata/agendada, observações),
   rastreio de entregas com linha do tempo e chatbot lateral ("Assistente
   Camaro AI" com chips de comando rápido e avaliação por estrelas).
3. **Admin** (`#admin-view`) — cartões de telemetria (bateria, status,
   velocidade, distância, ETA), **câmeras em tempo real** (seção 7), fila de
   pedidos com sugestão de lote, histórico e chat do operador.

Módulos JS: `api.js` (fetch com token via caminho relativo `/api`,
tratamento de 401/offline, toasts e diálogos de confirmação),
`state.js` (estado local + `syncWithBackend`), `app.js` (auth e
roteamento), `client.js` (vitrine/carrinho/checkout/rastreio/chat e
execução das ações vindas da IA), `admin.js` (polling de `/api/robot/status`
a cada 1 s e de `/api/camera/status` a cada 5 s, fila e histórico com refresh
dedicado a cada 4 s com preservação de rolagem, stats da IA a cada 30 s, lote).
Tema escuro próprio em `variables.css` (destaque amarelo `#ffcc00`); avisos
usam toasts não-bloqueantes em vez de `alert()`/`confirm()` nativos.

---

## 7. Câmeras RGB e de profundidade (ZED 2i) — teoria, código e comandos

### 7.1. Ideia principal

Dar ao operador **os olhos do robô** dentro do dashboard, sem exigir ROS no
navegador. A solução usa três peças encadeadas:

1. **Sensores no Gazebo** publicam imagens no padrão de tópicos da ZED;
2. **`web_video_server`** converte esses tópicos ROS em **MJPEG via HTTP**;
3. o **Flask faz proxy** desse MJPEG (evita CORS e segunda porta no
   frontend) e o **admin exibe dois `<img>` ao vivo**, lado a lado.

### 7.2. Os dois pontos de vista

| Câmera | Tópico ROS | Montagem física | O que mostra |
|---|---|---|---|
| RGB (ZED 2i) | `/zed/zed_node/rgb/image_raw` | `rgbd_camera` 640×480 no `zed_mount`, sobre haste de 0,60 m no aerofólio | corredor à frente; o capô amarelo do Camaro aparece na base da imagem (1ª pessoa) |
| Profundidade (ZED 2i, colorida) | `/zed/zed_node/rgb/depth_image_viz` | gerada pelo nó `depth_viz_node.py` a partir do depth float | mapa TURBO (perto = claro, longe = escuro), mesma geometria do RGB |

Tópicos complementares (ponte ativa, fora do painel): `/camera_user/image`
(traseira 800×800, `rgb8`) e `/zed/zed_node/points` (nuvem de pontos
`PointCloud2` 640×480 densa, p/ RViz2) — ambos acessíveis via proxy direto.

> Por que um nó para a profundidade? O tópico bruto
> `/zed/zed_node/rgb/image_raw/depth_image` sai em ponto flutuante
> (`32FC1`, metros) e o `web_video_server` não o converte sozinho para
> MJPEG — o frame chega preto/roxo. O `depth_viz_node.py` normaliza
> (clip 0,2–20 m, perto = claro) e republica em `rgb8` com colormap TURBO,
> que o MJPEG exibe normalmente.

### 7.3. Código 1 — sensores no modelo (`camaro.gazebo`)

```xml
<gazebo reference="zed_mount">
  <!-- ZED 2i: segue o padrão do driver real (zed_wrapper) -->
  <sensor name="zed2i_rgbd" type="rgbd_camera">
    <topic>/zed/zed_node/rgb/image_raw</topic>  <!-- gera image, depth_image e points -->
    <update_rate>15</update_rate>
    ...
```

### 7.4. Código 2 — pontes no launch (`gazebo.launch.py`)

```python
image_bridge = Node(  # Gazebo -> ROS 2 (mesmos nomes de tópico)
    package='ros_gz_image', executable='image_bridge', ...
    arguments=['/zed/zed_node/rgb/image_raw/image',
               '/zed/zed_node/rgb/image_raw/depth_image',
               '/camera_user/image', ...])

web_video_server = Node(  # ROS 2 -> MJPEG em http://localhost:8080
    package='web_video_server', executable='web_video_server',
    parameters=[{'port': 8080}])

rosbridge = Node(  # ROS 2 -> WebSocket em ws://localhost:9090
    package='rosbridge_server', executable='rosbridge_websocket',
    parameters=[{'port': 9090}])

# Nuvem de pontos da 2i: Gazebo (PointCloudPacked) -> ROS 2 (PointCloud2)
#   /zed/zed_node/rgb/image_raw/points  :=  /zed/zed_node/points
# (argumento extra do parameter_bridge principal, com remap)

depth_viz = Node(  # float32 -> rgb8 TURBO p/ o dashboard exibir
    package='camaro_description', executable='depth_viz_node.py',
    parameters=[{'use_sim_time': True}])
```

### 7.4b. Código 2b — `depth_viz_node.py` (a peça que faltava)

Nó ROS 2 puro (`rclpy` + `numpy` + `cv2`, sem `cv_bridge`): assina o depth
`32FC1`, aplica `clip` no alcance do sensor, inverte (perto = claro),
mapeia para TURBO e publica `rgb8` em
`/zed/zed_node/rgb/depth_image_viz`. Instalado via `CMakeLists.txt`
(`install(PROGRAMS ...)`) e validado ao vivo: snapshot JPEG íntegro e
geometria idêntica ao RGB.

### 7.5. Código 3 — proxy no Flask (`server.py`)

```python
CAMERA_TOPICS = {  # allowlist do proxy (stream + snapshot)
    "/zed/zed_node/rgb/image_raw": "ZED 2i — RGB (visão do robô)",
    "/zed/zed_node/rgb/image_raw/depth_image": "float32, sem vídeo",
    "/zed/zed_node/rgb/depth_image_viz": "ZED 2i — Profundidade (colorida)",
    "/camera_user/image": "Câmera do usuário (traseira)",
}
STATUS_VISIBLE_TOPICS = {  # o /api/camera/status anuncia só o que está no site
    "/zed/zed_node/rgb/image_raw",
    "/zed/zed_node/rgb/depth_image_viz",
}

@app.route("/api/camera/stream")
def camera_stream():  # repassa o MJPEG do web_video_server em streaming
    ...
```

Tópico fora da lista → `400`; `web_video_server` fora do ar → `503` com
dica de como subir a simulação. O painel do admin trata esses casos
exibindo o placeholder "Câmera offline".

### 7.6. Código 4 — painel duplo no admin (`admin.js`)

```js
const ZED_PANELS = [
  { key: "rgb",   topic: "/zed/zed_node/rgb/image_raw" },
  { key: "depth", topic: "/zed/zed_node/rgb/depth_image_viz" },
];
```

Cada painel tem `<img>` com `src = /api/camera/stream?topic=...`, dot de
status AO VIVO/OFFLINE e três botões: recarregar (↻), **tirar foto** (📷,
baixa o frame via `/api/camera/snapshot`) e abrir em nova aba (⧉); o
`src` só é trocado se o tópico mudar, para não reiniciar o MJPEG a cada
polling (5 s). Layout em `.zed-duo-grid` (2 colunas ≥ 900 px, 1 coluna no
mobile).

### 7.7. Validação realizada

Duas frentes: (a) com a simulação desligada, publicador de teste ROS +
`web_video_server` real — snapshot JPEG válido (magic `ffd8`) e MJPEG
multipart íntegro via proxy; (b) com a simulação ligada
(`corridor_rooms_high.sdf`), snapshots ao vivo de RGB e profundidade
colorida com geometria idêntica entre si. Sem imagem publicada, o painel
exibe corretamente "offline".

Evidência fotográfica do fluxo completo (pedido real `ORD_8DD9F07B`, com a
simulação ligada) na pasta `prints_dashboard/` (Área de Trabalho):
portal, vitrine, carrinho, pedido pelo chatbot, rastreio até ENTREGUE,
chat de status, fila do admin, pedido EM ROTA e câmeras ao vivo
(`01_...` a `10_...`, geradas via Playwright + Chrome headless).

---

## 8. Chatbot / IA — `llm.py` + `/api/chat`

Orquestrador em dois níveis (`process_message`):

1. **Gemini** (`gemini-1.5-flash` via REST) com *system prompt* de
   coordenador de delivery e contexto ao vivo (telemetria, estoque,
   pedidos, carrinho, fila, papel do usuário); a IA devolve texto +
   tags `<ACTION>{...}</ACTION>` (ex.: `add_to_cart`, `submit_order`,
   `set_destination`, `open_cart`, `confirm_all`, `batch_route`), que o
   backend valida/executa e o frontend reflete na tela;
2. **Fallback por regras** (sempre ativo sem chave de API): NLP com
   normalização (`normalize_query`), detecção multi-produto e quantidades
   (dígitos e por extenso), destinos, status do robô, comandos de admin e
   **sugestão proativa de rota em lote** com estimativa de economia de
   tempo (`_build_batch_suggestion`).

**Aprendizado contínuo:** cada comando executado é salvo em `ai_patterns`
(consulta normalizada → ação, com frequência); padrões com frequência ≥ 3
são reutilizados antes das regras. `training-stats` expõe volume de
mensagens, padrões mais usados e média das avaliações — fechando o ciclo
pedido → entrega → nota → IA melhor.

---

## 9. Dependências

### 9.1. Sistema e ROS (Ubuntu 24.04)

- ROS 2 Jazzy + Gazebo Harmonic (instalação oficial do ROS);
- `python3-colcon-*`, `ros-jazzy-ros-gz`, `ros-jazzy-ros-gz-sim`,
  `ros-jazzy-ros-gz-bridge`, `ros-jazzy-ros-gz-image`,
  `ros-jazzy-robot-state-publisher`, `ros-jazzy-joint-state-publisher*`,
  `ros-jazzy-rosbridge-server`, `ros-jazzy-web-video-server`,
  `ros-jazzy-slam-toolbox`, `ros-jazzy-navigation2`, `ros-jazzy-nav2-bringup`
  (SLAM/Nav2 só para navegação; o dashboard usa os marcados para ponte e
  vídeo);
- `pygame` (teleoperação manual, opcional para o dashboard).

### 9.2. Dashboard (venv Python)

```
flask==3.1.3  flask-cors==6.0.5  requests==2.34.2
werkzeug==3.1.8  (+ roslibpy, para o robot_bridge)
```

Navegador moderno (Chrome/Firefox) para o frontend; nada a instalar nele.

---

## 10. Como executar (passo a passo)

```shell
# 1 — Compilar a simulação (uma vez; symlink faz o launch valer na hora)
cd ~/noblecamaro-main/src/camaro_description && colcon build --symlink-install
source /opt/ros/jazzy/setup.bash
source ~/noblecamaro-main/install/setup.bash

# 2 — Subir a simulação (traz Gazebo + image_bridge + web_video_server + rosbridge)
ros2 launch camaro_description gazebo.launch.py world:=corridor_rooms_high.sdf
# (mundo leve alternativo: world:=corridor_rooms_light.sdf)

# 3 — Subir o dashboard INTEIRO com um comando (backend + Chrome)
cd ~/camaro_dashboard
python3 abrir_site.py
# (valida venv, porta 5000 e saúde do backend; log em /tmp/camaro_backend.log)
# Manual, se preferir: ./backend/venv/bin/python3 backend/server.py
# e abrir http://localhost:5000   (admin / 123  |  cliente / 123)
```

Verificações rápidas:

```shell
curl http://localhost:5000/api/robot/status
curl http://localhost:5000/api/camera/status
curl "http://localhost:5000/api/camera/snapshot?topic=/zed/zed_node/rgb/depth_image_viz" -o profundidade.jpg
curl "http://localhost:5000/api/camera/snapshot?topic=/camera_user/image" -o traseira.jpg
```

Sem a simulação no ar, o dashboard funciona integralmente (pedidos, chat,
entregas simuladas), exibindo câmeras e odometria como *offline*.

---

## 11. Estado atual, limitações e caminho para o robô real

**Funciona hoje (simulação):** autenticação e papéis; catálogo/carrinho/
checkout; rastreio; motor de entregas com fila individual e em lote;
telemetria; odometria real do Gazebo via rosbridge; câmeras RGB e de
profundidade da ZED 2i ao vivo (+ nuvem de pontos p/ RViz2); chatbot
Gemini/fallback com ações e aprendizado; feedback por estrelas; toasts e
foto das câmeras.

**Limitações conhecidas:** deslocamento emulado por temporização (sem Nav2
acoplado ao pedido); sem HTTPS/autenticação forte (ambiente de
laboratório); frontend em polling (1–30 s conforme o dado), não WebSocket;
malha 3D da câmera ainda é ZED 2 (comportamento do sensor já é 2i).

**Transição para o protótipo físico (mesmo Camaro, tamanho real):** a
arquitetura já isola os pontos de troca — (a) `robot_bridge.py` passa a
assinar a odometria real (AMCL/`robot_localization`) mantendo
`/api/robot/status` intacto; (b) os tópicos de câmera mantêm os mesmos
nomes (driver ZED SDK publica `/zed/zed_node/rgb/image_raw`), de modo que
`web_video_server` + proxy + painel funcionam sem mudança; (c) o motor de
temporização é substituído pelo despacho de metas ao Nav2 e telemetria
real; (d) `room_map.py` recebe as coordenadas do ambiente físico. Nenhuma
tela precisa ser reescrita.

---

## 12. Mapa arquivo → papel (para citação no artigo)

| Arquivo | Papel no sistema |
|---|---|
| `backend/server.py` | API REST, motor de entregas, proxy MJPEG, sessões |
| `backend/database.py` | persistência SQLite (pedidos, telemetria, chat, IA, feedback) |
| `backend/llm.py` | IA: Gemini + fallback, ações, sugestão de lote, aprendizado |
| `backend/robot_bridge.py` | odometria ROS→Flask via rosbridge |
| `backend/room_map.py` | coordenadas reais das salas/checkpoints |
| `js/api.js`, `js/state.js` | comunicação REST e estado do frontend |
| `js/app.js` | login/registro/roteamento portal-cliente-admin |
| `js/client.js` | vitrine, carrinho, checkout, rastreio, chat do cliente |
| `js/admin.js` | telemetria, câmeras RGB+profundidade (2i), foto, fila/lote, histórico, toasts |
| `js/api.js` | REST relativo, sessão, toasts, `confirmDialog` |
| `abrir_site.py` | lançador único (valida venv/porta/saúde, abre o Chrome) |
| `gazebo.launch.py` | sobe mundo, bridges (odom/scan/points), `image_bridge`, `web_video_server`, `rosbridge`, `depth_viz` |
| `scripts/depth_viz_node.py` | float32 → RGB TURBO (`depth_image_viz`) |
| `urdf/camaro.xacro` + `urdf/camaro.gazebo` | modelo e sensores (ZED 2i RGBD+pontos, traseira, LiDAR) |

## 13. Glossário mínimo

- **ROS 2 (Jazzy)** — middleware de robótica por tópicos publish/subscribe.
- **Gazebo Harmonic** — simulador físico 3D onde o Camaro virtual existe.
- **Nav2 / SLAM** — navegação autônoma / mapeamento e localização
  simultâneos (usados na simulação, independentes do dashboard).
- **Ackermann** — direção tipo carro do Camaro (física e simulada).
- **rosbridge** — expõe tópicos ROS via WebSocket (JSON).
- **web_video_server** — expõe imagens ROS via HTTP/MJPEG.
- **MJPEG** — vídeo como sequência de JPEGs sobre HTTP (ideal p/ `<img>`).
- **ZED 2i** — câmera estéreo (RGB + profundidade + nuvem de pontos;
  no simulador, `rgbd_camera` com os mesmos tópicos do driver real).
- **Nuvem de pontos** — conjunto 3D de pontos (XYZRGB) da cena; no site
  aparece achatada em 2D (profundidade colorida), na íntegra via RViz2.
- **LiDAR** — sensor laser de distância (presente no modelo; dados usados
  na navegação, não no dashboard atual).

---

*Documento gerado a partir do código-fonte vigente do `camaro_dashboard` e
do pacote `camaro_description` (simulação), para fins de artigo científico
e reprodução do experimento.*