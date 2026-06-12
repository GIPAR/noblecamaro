import pygame
import sys
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from ackermann_msgs.msg import AckermannDrive
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

pygame.init()
rclpy.init()

class TeleopNode(Node):
    def __init__(self):
        super().__init__('camaro_controller')
        
        qos = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT, depth=10)
        
        self.pub = self.create_publisher(AckermannDrive, '/ackermann_cmd', 10)
        self.pub_twist = self.create_publisher(Twist, '/cmd_vel', 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos)
        
        self.scan_ranges = []
        self.scan_angle_min = 0
        self.scan_angle_inc = 0
        self.obstacle_dist = float('inf')
        
        # Para análise de obstáculo mais próximo (apenas na frente)
        self.front_obstacle_dist = float('inf')
        
    def scan_callback(self, msg):
        self.scan_ranges = msg.ranges
        self.scan_angle_min = msg.angle_min
        self.scan_angle_inc = msg.angle_increment
        
        # Analisa apenas obstáculos à FRENTE do robô (ângulo entre -30° e 30°)
        front_distances = []
        num_pontos = len(msg.ranges)
        
        for i, dist in enumerate(msg.ranges):
            angulo = msg.angle_min + (i * msg.angle_inc)
            # Considera apenas pontos na frente (ângulo entre -30 e 30 graus)
            if abs(angulo) < 0.52:  # 0.52 rad = ~30 graus
                if not math.isnan(dist) and dist > 0:
                    front_distances.append(dist)
        
        if front_distances:
            self.front_obstacle_dist = min(front_distances)
        else:
            self.front_obstacle_dist = float('inf')
        
        # Mantém o geral também
        valid = [r for r in msg.ranges if not math.isnan(r) and r > 0]
        self.obstacle_dist = min(valid) if valid else float('inf')

node = TeleopNode()

# === JOYSTICK ===
pygame.joystick.init()
joy = None
if pygame.joystick.get_count() > 0:
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"✅ Joystick detectado: {joy.get_name()}")
else:
    print("⚠️ Nenhum joystick detectado. Use teclado (WASD).")

# === TELA ===
LARGURA = 1024
ALTURA = 640
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Smart Camaro - Controlador Ackerman")

fonte_titulo = pygame.font.SysFont("monospace", 42, bold=True)
fonte_sub = pygame.font.SysFont("monospace", 16, bold=True)
fonte = pygame.font.SysFont("monospace", 20, bold=True)
fonte_desc = pygame.font.SysFont("monospace", 13, bold=True)
fonte_tecla = pygame.font.SysFont("monospace", 24, bold=True)
fonte_peq = pygame.font.SysFont("monospace", 11, bold=True)

clock = pygame.time.Clock()

# === CORES ===
CAMARO_YELLOW = (255, 234, 23)
CAMARO_YELLOW_DIM = (200, 180, 20)
CAMARO_YELLOW_LIGHT = (255, 255, 150)
VERDE = (0, 200, 100)
VERMELHO = (255, 50, 50)
VERMELHO_ESCURO = (180, 20, 20)
LARANJA = (255, 150, 0)
AZUL = (0, 150, 255)

# === CONFIGURAÇÕES DE SEGURANÇA (LÓGICA QUE VOCÊ PEDIU) ===
# Só freia quando está VERMELHO (< 0.8m)
DISTANCIA_VERDE = 1.5      # > 1.5m -> livre
DISTANCIA_LARANJA = 0.8    # 0.8 - 1.5m -> alerta, NÃO freia
DISTANCIA_VERMELHO = 0.4   # < 0.4m -> para total

# Velocidades seguras
VEL_MAX_NORMAL = 5.0       # velocidade máxima
VEL_VERMELHO = 0.5         # velocidade quando está vermelho (0.4-0.8m)
VEL_VERMELHO_ESCURO = 0.0  # para quando < 0.4m

def calcular_velocidade_segura(velocidade_desejada, distancia_obstaculo, max_speed):
    """
    Retorna a velocidade segura baseada na distância do obstáculo à frente.
    Só freia se estiver VERMELHO (< 0.8m)
    """
    # Se não tem obstáculo ou está longe (ZONA VERDE)
    if distancia_obstaculo >= DISTANCIA_LARANJA:
        return velocidade_desejada
    
    # ZONA LARANJA (0.8 - 1.5m) - só alerta, NÃO FREIA
    elif distancia_obstaculo >= DISTANCIA_VERMELHO:
        # Mantém velocidade, mas com aviso visual
        return velocidade_desejada
    
    # ZONA VERMELHA (< 0.4m) - PARA TOTAL
    elif distancia_obstaculo <= DISTANCIA_VERMELHO:
        return 0.0
    
    # ZONA VERMELHA (0.4 - 0.8m) - reduz progressivamente
    else:
        # Interpolação linear entre VEL_VERMELHO e 0
        fator = (distancia_obstaculo - DISTANCIA_VERMELHO) / (DISTANCIA_LARANJA - DISTANCIA_VERMELHO)
        velocidade_max = VEL_VERMELHO + fator * (max_speed - VEL_VERMELHO)
        return min(velocidade_desejada, velocidade_max)

# === VARIÁVEIS ACKERMAN ===
current_speed = 0.0
current_steering = 0.0
acceleration_rate = 0.08
steering_rate = 0.04
max_speed = 5.0
max_steering = 0.6
min_speed_reverse = -2.0

rastro = []
modo = "JOYSTICK"

# === MODOS DE VELOCIDADE ===
modo_velocidade = "Normal"
modos = ["Suave", "Normal", "Rápido", "Segurança", "Economia"]
menu_modos_aberto = False

VELOCIDADES = {
    "Suave":     {"max_speed": 2.0, "max_steering": 0.4, "accel": 0.04, "steer_rate": 0.03},
    "Normal":    {"max_speed": 4.0, "max_steering": 0.5, "accel": 0.06, "steer_rate": 0.04},
    "Rápido":    {"max_speed": 6.0, "max_steering": 0.6, "accel": 0.08, "steer_rate": 0.05},
    "Segurança": {"max_speed": 1.5, "max_steering": 0.3, "accel": 0.03, "steer_rate": 0.02},
    "Economia":  {"max_speed": 3.0, "max_steering": 0.4, "accel": 0.05, "steer_rate": 0.03},
}

def aplicar_limite_esterco(velocidade, angulo_volante, max_steering_base):
    abs_speed = abs(velocidade)
    
    if abs_speed > 3.0:
        fator = 0.4
    elif abs_speed > 2.0:
        fator = 0.6
    elif abs_speed > 1.0:
        fator = 0.8
    else:
        fator = 1.0
    
    if velocidade < 0:
        fator *= 0.5
    
    max_allowed = max_steering_base * fator
    return max(-max_allowed, min(max_allowed, angulo_volante))

def desenhar_tecla(tela, letra, x, y, pressionada):
    cor = CAMARO_YELLOW if pressionada else (50, 50, 50)
    pygame.draw.rect(tela, cor, (x, y, 50, 50), border_radius=8)
    txt = fonte_tecla.render(letra, True, (0, 0, 0) if pressionada else (200, 200, 200))
    tela.blit(txt, (x + 15, y + 12))

def desenhar_lidar(tela, x, y, tamanho):
    pygame.draw.rect(tela, (20, 20, 25), (x, y, tamanho, tamanho), border_radius=8)
    pygame.draw.rect(tela, CAMARO_YELLOW_DIM, (x, y, tamanho, tamanho), 2, border_radius=8)
    
    titulo = fonte_sub.render("LIDAR VIEW", True, CAMARO_YELLOW)
    tela.blit(titulo, (x + tamanho//2 - titulo.get_width()//2, y + 10))
    
    cx = x + tamanho // 2
    cy = y + tamanho // 2 + 5
    raio_max = tamanho // 2 - 25
    
    for r in [raio_max//3, 2*raio_max//3, raio_max]:
        pygame.draw.circle(tela, (50, 50, 50), (cx, cy), r, 1)
    
    if node.scan_ranges:
        for i, distancia in enumerate(node.scan_ranges):
            if 0.2 < distancia < 4.0:
                angulo = node.scan_angle_min + (i * node.scan_angle_inc)
                
                # CORES REAIS DO LIDAR
                if distancia < 0.4:
                    cor = VERMELHO_ESCURO
                    raio_ponto = 5
                elif distancia < 0.8:
                    cor = VERMELHO
                    raio_ponto = 4
                elif distancia < 1.5:
                    cor = LARANJA
                    raio_ponto = 3
                else:
                    cor = VERDE
                    raio_ponto = 2
                
                escala = raio_max / 3.5
                px = cx + int(distancia * escala * math.cos(angulo))
                py = cy + int(distancia * escala * math.sin(angulo))
                
                if x < px < x + tamanho and y < py < y + tamanho:
                    pygame.draw.circle(tela, cor, (px, py), raio_ponto)
    
    # Robô
    pygame.draw.circle(tela, CAMARO_YELLOW, (cx, cy), 10)
    pygame.draw.circle(tela, (0, 0, 0), (cx, cy), 5)
    
    # Rodas dianteiras
    angulo_roda = current_steering
    ex1 = cx + int(8 * math.cos(angulo_roda)) - int(6 * math.sin(angulo_roda))
    ey1 = cy - 10 + int(8 * math.sin(angulo_roda)) + int(6 * math.cos(angulo_roda))
    ex2 = cx + int(8 * math.cos(angulo_roda)) + int(6 * math.sin(angulo_roda))
    ey2 = cy + 10 + int(8 * math.sin(angulo_roda)) - int(6 * math.cos(angulo_roda))
    
    pygame.draw.line(tela, AZUL, (cx, cy - 10), (ex1, ey1), 3)
    pygame.draw.line(tela, AZUL, (cx, cy + 10), (ex2, ey2), 3)
    
    seta_x = cx + int(15 * math.cos(0))
    seta_y = cy + int(15 * math.sin(0))
    pygame.draw.line(tela, CAMARO_YELLOW, (cx, cy), (seta_x, seta_y), 3)
    
    # Legenda
    leg_y = y + tamanho - 18
    pygame.draw.circle(tela, VERDE, (x + 15, leg_y), 3)
    leg1 = fonte_peq.render(">1.5m", True, (150, 150, 150))
    tela.blit(leg1, (x + 25, leg_y - 4))
    
    pygame.draw.circle(tela, LARANJA, (x + 70, leg_y), 3)
    leg2 = fonte_peq.render("0.8-1.5m", True, (150, 150, 150))
    tela.blit(leg2, (x + 80, leg_y - 4))
    
    pygame.draw.circle(tela, VERMELHO, (x + 135, leg_y), 3)
    leg3 = fonte_peq.render("<0.8m", True, (150, 150, 150))
    tela.blit(leg3, (x + 145, leg_y - 4))
    
    pygame.draw.circle(tela, VERMELHO_ESCURO, (x + 200, leg_y), 3)
    leg4 = fonte_peq.render("<0.4m", True, (150, 150, 150))
    tela.blit(leg4, (x + 210, leg_y - 4))

def desenhar_volante(tela, x, y, angulo):
    raio = 45
    
    pygame.draw.circle(tela, (40, 40, 40), (x, y), raio)
    pygame.draw.circle(tela, (80, 80, 80), (x, y), raio, 2)
    
    for i in range(4):
        ang = math.radians(i * 90)
        px = x + int(35 * math.cos(ang))
        py = y + int(35 * math.sin(ang))
        pygame.draw.line(tela, (60, 60, 60), (x, y), (px, py), 2)
    
    ang_rad = angulo
    mao_x = x + int(38 * math.cos(ang_rad))
    mao_y = y + int(38 * math.sin(ang_rad))
    pygame.draw.circle(tela, CAMARO_YELLOW, (mao_x, mao_y), 12)
    pygame.draw.circle(tela, (0, 0, 0), (mao_x, mao_y), 5)
    
    pygame.draw.circle(tela, CAMARO_YELLOW_DIM, (x, y), 8)
    
    ang_graus = math.degrees(angulo)
    ang_text = fonte_peq.render(f"{ang_graus:.0f}°", True, CAMARO_YELLOW)
    tela.blit(ang_text, (x - ang_text.get_width()//2, y + raio + 5))

window_active = True

while True:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        
        if evento.type == pygame.ACTIVEEVENT:
            if evento.gain == 1:
                window_active = True
            elif evento.gain == 0:
                window_active = False

        if evento.type == pygame.MOUSEBUTTONDOWN:
            if window_active:
                if 412 <= evento.pos[0] <= 612 and 550 <= evento.pos[1] <= 590:
                    modo = "TECLADO" if modo == "JOYSTICK" else "JOYSTICK"

                if 880 <= evento.pos[0] <= 1000 and 15 <= evento.pos[1] <= 45:
                    menu_modos_aberto = not menu_modos_aberto

                if menu_modos_aberto:
                    for i, nome_modo in enumerate(modos):
                        y = 60 + i * 30
                        if 880 <= evento.pos[0] <= 1000 and y <= evento.pos[1] <= y + 28:
                            modo_velocidade = nome_modo
                            menu_modos_aberto = False

    config = VELOCIDADES[modo_velocidade]
    max_speed = config["max_speed"]
    max_steering = config["max_steering"]
    acceleration_rate = config["accel"]
    steering_rate = config["steer_rate"]
    min_speed_reverse = -max_speed * 0.4

    # === LEITURA DE ENTRADA ===
    if window_active:
        if modo == "JOYSTICK" and joy is not None:
            try:
                eixo_speed = -joy.get_axis(1)
                eixo_steering = joy.get_axis(0)
                if abs(eixo_speed) < 0.1: eixo_speed = 0.0
                if abs(eixo_steering) < 0.1: eixo_steering = 0.0
            except:
                modo = "TECLADO"
                eixo_speed, eixo_steering = 0.0, 0.0
        else:
            teclas = pygame.key.get_pressed()
            eixo_speed = 0.0
            eixo_steering = 0.0
            if teclas[pygame.K_w]: eixo_speed = 1.0
            if teclas[pygame.K_s]: eixo_speed = -1.0
            if teclas[pygame.K_a]: eixo_steering = 1.0
            if teclas[pygame.K_d]: eixo_steering = -1.0
    else:
        eixo_speed = 0.0
        eixo_steering = 0.0

    # Velocidade desejada pelo usuário
    if eixo_speed > 0:
        target_speed_desejada = eixo_speed * max_speed
    else:
        target_speed_desejada = eixo_speed * abs(min_speed_reverse)
    
    # === SEGURANÇA: aplica limite baseado no LiDAR (SÓ FREIA NO VERMELHO) ===
    target_speed = calcular_velocidade_segura(target_speed_desejada, node.front_obstacle_dist, max_speed)
    
    # Ângulo do volante
    target_steering = eixo_steering * max_steering
    target_steering = aplicar_limite_esterco(current_speed, target_steering, max_steering)
    
    # Suavização
    if target_speed > current_speed:
        current_speed += acceleration_rate
        current_speed = min(target_speed, current_speed)
    elif target_speed < current_speed:
        current_speed -= acceleration_rate
        current_speed = max(target_speed, current_speed)
    
    if target_steering > current_steering:
        current_steering += steering_rate
        current_steering = min(target_steering, current_steering)
    elif target_steering < current_steering:
        current_steering -= steering_rate
        current_steering = max(target_steering, current_steering)
    
    speed = current_speed
    steering = current_steering

    # Desenho da tela
    tela.fill((0, 0, 0))

    # HEADER
    titulo = fonte_titulo.render("SMART CAMARO", True, CAMARO_YELLOW)
    subtitulo = fonte_sub.render("CONTROLADOR ACKERMAN - GAZEBO HARMONIC", True, CAMARO_YELLOW)
    
    # Determina estado de segurança
    dist = node.front_obstacle_dist
    if dist < 0.4:
        estado_seguranca = "⚠️ EMERGENCIA! PARANDO ⚠️"
        cor_estado = VERMELHO_ESCURO
    elif dist < 0.8:
        estado_seguranca = f"⚠️ PERIGO! {dist:.1f}m - REDUZINDO VELOCIDADE"
        cor_estado = VERMELHO
    elif dist < 1.5:
        estado_seguranca = f"⚠️ ALERTA! {dist:.1f}m - MANTENDO VELOCIDADE"
        cor_estado = LARANJA
    else:
        estado_seguranca = "✓ SEGURO"
        cor_estado = VERDE
    
    if window_active:
        descricao = fonte_desc.render("WASD | Joystick | Clique aqui para controlar", True, (180, 180, 180))
    else:
        descricao = fonte_desc.render("⚠️ Janela sem foco - Clique para controlar o robô", True, VERMELHO)
    
    tela.blit(titulo, (LARGURA//2 - titulo.get_width()//2, 10))
    tela.blit(subtitulo, (LARGURA//2 - subtitulo.get_width()//2, 58))
    tela.blit(descricao, (LARGURA//2 - descricao.get_width()//2, 80))
    
    # Estado de segurança
    estado_surf = fonte_desc.render(estado_seguranca, True, cor_estado)
    tela.blit(estado_surf, (LARGURA//2 - estado_surf.get_width()//2, 100))

    # STATUS
    angulo_graus = math.degrees(steering)
    status = fonte.render(f"Speed: {speed:.2f} m/s  |  Steering: {angulo_graus:.1f}°  |  Obst: {dist:.2f}m", True, (255, 255, 255))
    tela.blit(status, (LARGURA//2 - status.get_width()//2, 125))
    
    # Barras
    largura_barra = int(abs(speed) / max_speed * 400) if max_speed > 0 else 0
    barra_x = LARGURA//2 - 200
    cor_barra = (255, 50, 50) if speed < 0 else CAMARO_YELLOW
    pygame.draw.rect(tela, (30, 30, 30), (barra_x, 145, 400, 15), border_radius=5)
    pygame.draw.rect(tela, cor_barra, (barra_x, 145, largura_barra, 15), border_radius=5)
    
    # Barra de esterço
    largura_steer = int((steering / max_steering) * 200) if max_steering > 0 else 0
    steer_bar_x = LARGURA//2 - 100
    pygame.draw.rect(tela, (30, 30, 30), (steer_bar_x, 170, 200, 10), border_radius=3)
    if steering > 0:
        pygame.draw.rect(tela, AZUL, (steer_bar_x + 100, 170, largura_steer, 10), border_radius=3)
    else:
        pygame.draw.rect(tela, AZUL, (steer_bar_x + 100 + largura_steer, 170, -largura_steer, 10), border_radius=3)
    pygame.draw.line(tela, CAMARO_YELLOW, (steer_bar_x + 100, 170), (steer_bar_x + 100, 180), 2)

    # LAYOUT PRINCIPAL
    # ESQUERDA - TECLADO
    tx = 80
    teclas_vis = pygame.key.get_pressed()
    desenhar_tecla(tela, "W", tx + 30, 280, teclas_vis[pygame.K_w])
    desenhar_tecla(tela, "A", tx - 30, 340, teclas_vis[pygame.K_a])
    desenhar_tecla(tela, "S", tx + 30, 340, teclas_vis[pygame.K_s])
    desenhar_tecla(tela, "D", tx + 90, 340, teclas_vis[pygame.K_d])
    
    instr1 = fonte_peq.render("W/S = Acelerar/Re", True, (150, 150, 150))
    instr2 = fonte_peq.render("A/D = Virar volante", True, (150, 150, 150))
    tela.blit(instr1, (tx - 10, 410))
    tela.blit(instr2, (tx - 10, 430))
    
    label_teclado = fonte_desc.render("TECLADO", True, CAMARO_YELLOW if modo == "TECLADO" else (150, 150, 150))
    tela.blit(label_teclado, (tx + 30 - label_teclado.get_width()//2 + 25, 460))

    # CENTRO - LIDAR
    desenhar_lidar(tela, LARGURA//2 - 160, 200, 320)

    # DIREITA - VOLANTE
    jx, jy = 880, 320
    desenhar_volante(tela, jx, jy - 50, steering)
    
    # Joystick
    pygame.draw.circle(tela, (40, 40, 40), (jx, jy + 50), 55)
    pygame.draw.circle(tela, (80, 80, 80), (jx, jy + 50), 55, 2)
    
    if modo == "JOYSTICK" and window_active:
        joy_x = jx + int((steering / max_steering) * 40) if max_steering > 0 else jx
        joy_y = (jy + 50) - int((speed / max_speed) * 40) if max_speed > 0 else (jy + 50)
    else:
        joy_x, joy_y = jx, jy + 50
    
    dx, dy = joy_x - jx, joy_y - (jy + 50)
    dist_joy = math.hypot(dx, dy)
    if dist_joy > 45:
        joy_x = jx + int(dx * 45 / dist_joy)
        joy_y = (jy + 50) + int(dy * 45 / dist_joy)
    
    rastro.append((joy_x, joy_y))
    if len(rastro) > 10:
        rastro.pop(0)
    for i, pos in enumerate(rastro):
        raio = int(10 * i / len(rastro)) if len(rastro) > 0 else 0
        pygame.draw.circle(tela, CAMARO_YELLOW, pos, raio)
    
    pygame.draw.circle(tela, CAMARO_YELLOW, (joy_x, joy_y), 20)
    pygame.draw.circle(tela, (0, 0, 0), (joy_x, joy_y), 8)
    
    label_joy = fonte_desc.render("JOYSTICK", True, CAMARO_YELLOW if modo == "JOYSTICK" else (150, 150, 150))
    tela.blit(label_joy, (jx - label_joy.get_width()//2, (jy + 50) + 70))
    
    if joy is None:
        no_joy = fonte_peq.render("(nenhum joystick)", True, (100, 50, 50))
        tela.blit(no_joy, (jx - no_joy.get_width()//2, (jy + 50) + 90))

    # BOTÃO MODO
    cor_btn = (0, 150, 100) if modo == "JOYSTICK" else (150, 60, 60)
    pygame.draw.rect(tela, cor_btn, (412, 570, 200, 40), border_radius=10)
    txt_btn = fonte_desc.render(f"MODO: {modo}", True, (255, 255, 255))
    tela.blit(txt_btn, (512 - txt_btn.get_width()//2, 583))

    # BOTÃO MODOS
    pygame.draw.rect(tela, (30, 30, 30), (880, 15, 120, 30), border_radius=5)
    pygame.draw.rect(tela, (70, 70, 70), (880, 15, 120, 30), border_radius=5, width=2)
    txt_modos = fonte_desc.render(f"{modo_velocidade} ▼", True, CAMARO_YELLOW)
    tela.blit(txt_modos, (940 - txt_modos.get_width()//2, 21))

    # MENU DE MODOS
    if menu_modos_aberto:
        pygame.draw.rect(tela, (0, 0, 0), (880, 50, 130, 190), border_radius=6)
        pygame.draw.rect(tela, CAMARO_YELLOW, (880, 50, 130, 190), border_radius=6, width=2)
        
        for i, nome_modo in enumerate(modos):
            y = 60 + i * 30
            cor = CAMARO_YELLOW_LIGHT if nome_modo == modo_velocidade else (200, 200, 200)
            pygame.draw.rect(tela, (20, 20, 20), (885, y, 120, 26), border_radius=4)
            txt = fonte_desc.render(nome_modo, True, cor)
            tela.blit(txt, (945 - txt.get_width()//2, y + 6))

    # PUBLICAÇÃO ROS2
    msg_ack = AckermannDrive()
    msg_ack.speed = float(speed)
    msg_ack.steering_angle = float(steering)
    node.pub.publish(msg_ack)
    
    msg_twist = Twist()
    msg_twist.linear.x = float(speed)
    msg_twist.angular.z = float(steering * 1.5)
    node.pub_twist.publish(msg_twist)
    
    rclpy.spin_once(node, timeout_sec=0)

    pygame.display.flip()
    clock.tick(30)