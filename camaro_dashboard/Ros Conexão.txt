# pacote do sistema pra criar venv
sudo apt install python3.12-venv

# instalar rosbridge (mesma máquina do ROS2/Gazebo)
sudo apt install ros-jazzy-rosbridge-server

# dentro da pasta backend/
cd camaro_dashboard/backend
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors roslibpy requests

# subir o rosbridge (deixa esse terminal aberto)
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# em outro terminal, com a venv ativada
cd camaro_dashboard/backend
source venv/bin/activate
python3 server.py

# testar
curl http://localhost:5000/api/robot/status




PROMPT PRA JOGAR NO ANTIGRAVITY E PEDIR PRA ELE TIRAR O MODO ANTIGO DO MAPA
Contexto: tenho um projeto em ~/camaro_dashboard. O backend Flask fica em
backend/server.py, já rodando em http://localhost:5000. Ele expõe a rota
GET /api/robot/status, que retorna a posição atual real do robô (x, y),
vinda do ROS2/Gazebo via rosbridge, e a sala mais próxima:

{"x": 0.0, "y": 0.0, "conectado": true, "sala_mais_proxima": "SALA A"}

As coordenadas reais do mapa (salas, portas, base) estão em
backend/room_map.py, extraídas do mundo Gazebo (corridor_rooms.sdf):

- BASE = (2.0, 0.0, 0.0) — ponto de spawn do robô
- ROOMS = { "A": (11.0, 5.6, ...), "B": (11.0, -5.6, ...),
            "C": (18.0, 5.6, ...), "D": (18.0, -5.6, ...) }
- O corredor tem ~4m de largura (y de -2 a 2) e vai de x=0 até x~20

Já existe, na área de desenvolvedor/admin do site, um mapa 2D fictício
antigo, com posições de salas inventadas (não reais). Quero que você
localize esse mapa existente no frontend e o SUBSTITUA por uma versão
nova, mais lapidada e visualmente parecida com o ambiente do Gazebo
(corredor + salas nas proporções reais), usando as coordenadas
verdadeiras de room_map.py em vez das antigas.

Requisitos do novo mapa:

1. Corredor desenhado nas proporções reais (largura ~4m, y de -2 a 2)
2. As 4 salas (A, B, C, D) posicionadas exatamente onde estão em ROOMS
3. Um marcador representando o robô, na posição atual
4. O marcador deve se atualizar automaticamente, buscando
   GET http://localhost:5000/api/robot/status a cada 1-2 segundos,
   refletindo a odometria real do robô (não mais uma posição simulada)
5. Destacar visualmente qual sala está mais próxima do robô no momento
   (campo "sala_mais_proxima" da resposta da API)

Mantenha esse novo mapa no mesmo local da área de admin/desenvolvedor
onde estava o antigo — é uma substituição, não uma página nova.
Antes de mudar qualquer coisa, procure e leia o componente do mapa
fictício atual pra entender como ele está estruturado, e siga o mesmo
padrão de organização do restante do frontend.