import pygame
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

pygame.init()
rclpy.init()
node = Node('nara_controller')
pub = node.create_publisher(Twist, '/cmd_vel', 10)

# === ALTERAÇÃO 1: JOYSTICK OPCIONAL ===
pygame.joystick.init()
joy = None
if pygame.joystick.get_count() > 0:
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"✅ Joystick detectado: {joy.get_name()}")
else:
    print("⚠️ Nenhum joystick detectado. Use teclado (WASD).")
# =======================================

tela = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Smart Camaro - Controlador")

fonte_titulo = pygame.font.SysFont("monospace", 42, bold=True)
fonte_sub = pygame.font.SysFont("monospace", 16, bold=True)
fonte = pygame.font.SysFont("monospace", 20, bold=True)
fonte_desc = pygame.font.SysFont("monospace", 13, bold=True)
fonte_tecla = pygame.font.SysFont("monospace", 24, bold=True)

clock = pygame.time.Clock()

# === CORES DO TEMA CAMARO ===
CAMARO_YELLOW = (255, 234, 23)
CAMARO_YELLOW_DIM = (200, 180, 20)
CAMARO_YELLOW_LIGHT = (255, 255, 150)

current_linear = 0.0
current_angular = 0.0
acceleration_rate = 0.06
deceleration_rate = 0.20
linear_speed = 3.0
angular_speed = 0.6
rastro = []
modo = "JOYSTICK"

# === MODOS DE VELOCIDADE ===
modo_velocidade = "Normal"
modos = ["Suave", "Normal", "Rápido", "Segurança", "Economia"]
menu_modos_aberto = False

# === ALTERAÇÃO 2: CONFIGURAÇÕES DOS MODOS ===
VELOCIDADES = {
    "Suave":     {"linear": 1.5, "angular": 0.3, "accel": 0.03, "decel": 0.10},
    "Normal":    {"linear": 3.0, "angular": 0.6, "accel": 0.06, "decel": 0.20},
    "Rápido":    {"linear": 5.0, "angular": 1.0, "accel": 0.10, "decel": 0.30},
    "Segurança": {"linear": 1.0, "angular": 0.2, "accel": 0.02, "decel": 0.08},
    "Economia":  {"linear": 2.0, "angular": 0.4, "accel": 0.04, "decel": 0.15},
}
# ===========================================

def desenhar_tecla(tela, letra, x, y, pressionada):
    cor = CAMARO_YELLOW if pressionada else (50, 50, 50)
    pygame.draw.rect(tela, cor, (x, y, 50, 50), border_radius=8)
    txt = fonte_tecla.render(letra, True, (0, 0, 0) if pressionada else (200, 200, 200))
    tela.blit(txt, (x + 15, y + 12))

while True:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.MOUSEBUTTONDOWN:
            if 320 <= evento.pos[0] <= 480 and 540 <= evento.pos[1] <= 575:
                modo = "TECLADO" if modo == "JOYSTICK" else "JOYSTICK"

            if 650 <= evento.pos[0] <= 780 and 15 <= evento.pos[1] <= 45:
                menu_modos_aberto = not menu_modos_aberto

            if menu_modos_aberto:
                for i, nome_modo in enumerate(modos):
                    y = 60 + i * 30
                    if 650 <= evento.pos[0] <= 780 and y <= evento.pos[1] <= y + 28:
                        modo_velocidade = nome_modo
                        menu_modos_aberto = False

    # === ALTERAÇÃO 2 (CONT.): APLICAR CONFIG DO MODO SELECIONADO ===
    config = VELOCIDADES[modo_velocidade]
    linear_speed = config["linear"]
    angular_speed = config["angular"]
    acceleration_rate = config["accel"]
    deceleration_rate = config["decel"]
    # =============================================================

    # === LEITURA DE ENTRADA (COM VERIFICAÇÃO DE JOYSTICK) ===
    if modo == "JOYSTICK" and joy is not None:
        try:
            eixo_linear = -joy.get_axis(1)
            eixo_angular = joy.get_axis(0)
            if abs(eixo_linear) < 0.1:
                eixo_linear = 0.0
            if abs(eixo_angular) < 0.1:
                eixo_angular = 0.0
        except:
            modo = "TECLADO"
            eixo_linear, eixo_angular = 0.0, 0.0
    else:
        teclas = pygame.key.get_pressed()
        eixo_linear = 0.0
        eixo_angular = 0.0
        if teclas[pygame.K_w]:
            eixo_linear = 1.0
        if teclas[pygame.K_s]:
            eixo_linear = -1.0
        if teclas[pygame.K_a]:
            eixo_angular = 1.0
        if teclas[pygame.K_d]:
            eixo_angular = -1.0
    # =========================================================

    target_linear = eixo_linear * linear_speed
    target_angular = eixo_angular * angular_speed

    if target_linear > current_linear:
        current_linear += acceleration_rate
        current_linear = min(target_linear, current_linear)
    elif target_linear < current_linear:
        current_linear -= acceleration_rate
        current_linear = max(target_linear, current_linear)

    if target_angular > current_angular:
        current_angular += acceleration_rate
        current_angular = min(target_angular, current_angular)
    elif target_angular < current_angular:
        current_angular -= acceleration_rate
        current_angular = max(target_angular, current_angular)

    linear = current_linear
    angular = current_angular

    tela.fill((0, 0, 0))

    # ── HEADER ──
    titulo = fonte_titulo.render("SMART CAMARO", True, CAMARO_YELLOW)
    subtitulo = fonte_sub.render("CONTROLADOR DE VELOCIDADE - GAZEBO HARMONIC", True, CAMARO_YELLOW)
    descricao = fonte_desc.render("Escolha o modo que deseja teclado ou joystick! :)", True, (180, 180, 180))
    tela.blit(titulo, (400 - titulo.get_width()//2, 10))
    tela.blit(subtitulo, (400 - subtitulo.get_width()//2, 58))
    tela.blit(descricao, (400 - descricao.get_width()//2, 80))

    # ── STATUS ──
    status = fonte.render(f"Linear: {linear:.2f} Angular: {angular:.2f}", True, (255, 255, 255))
    tela.blit(status, (400 - status.get_width()//2, 105))

    # ── BARRA ──
    largura_barra = int(abs(linear) / linear_speed * 400)
    barra_x = 400 - 200
    cor_barra = (255, 50, 50) if linear < 0 else CAMARO_YELLOW
    pygame.draw.rect(tela, (30, 30, 30), (barra_x, 140, 400, 20), border_radius=6)
    pygame.draw.rect(tela, cor_barra, (barra_x, 140, largura_barra, 20), border_radius=6)
    lbl_barra = fonte_desc.render("VELOCIDADE LINEAR", True, (100, 100, 100))
    tela.blit(lbl_barra, (400 - lbl_barra.get_width()//2, 163))

    # ── TECLADO (esquerda) ──
    teclas_vis = pygame.key.get_pressed()
    tx = 100
    if modo == "TECLADO":
        desenhar_tecla(tela, "W", tx + 30, 310, teclas_vis[pygame.K_w])
        desenhar_tecla(tela, "A", tx - 30, 370, teclas_vis[pygame.K_a])
        desenhar_tecla(tela, "S", tx + 30, 370, teclas_vis[pygame.K_s])
        desenhar_tecla(tela, "D", tx + 90, 370, teclas_vis[pygame.K_d])
    else:
        desenhar_tecla(tela, "W", tx + 30, 310, False)
        desenhar_tecla(tela, "A", tx - 30, 370, False)
        desenhar_tecla(tela, "S", tx + 30, 370, False)
        desenhar_tecla(tela, "D", tx + 90, 370, False)

    label_teclado = fonte_desc.render("TECLADO", True, (150, 150, 150))
    tela.blit(label_teclado, (tx + 30 - label_teclado.get_width()//2 + 25, 430))

    # ── JOYSTICK (direita) ──
    jx, jy = 620, 370
    pygame.draw.circle(tela, (40, 40, 40), (jx, jy), 70)
    pygame.draw.circle(tela, (80, 80, 80), (jx, jy), 70, 2)

    if modo == "JOYSTICK":
        joy_x = jx + int((angular / angular_speed) * 50)
        joy_y = jy - int((linear / linear_speed) * 50)
    else:
        joy_x, joy_y = jx, jy

    rastro.append((joy_x, joy_y))
    if len(rastro) > 10:
        rastro.pop(0)
    for i, pos in enumerate(rastro):
        raio = int(10 * i / len(rastro))
        pygame.draw.circle(tela, CAMARO_YELLOW, pos, raio)

    pygame.draw.circle(tela, CAMARO_YELLOW, (joy_x, joy_y), 22)

    label_joy = fonte_desc.render("JOYSTICK", True, (150, 150, 150))
    tela.blit(label_joy, (jx - label_joy.get_width()//2, jy + 82))

    # ── BOTÃO MODO (centro baixo) ──
    cor_btn = CAMARO_YELLOW if modo == "JOYSTICK" else CAMARO_YELLOW_DIM
    pygame.draw.rect(tela, cor_btn, (320, 540, 160, 40), border_radius=10)
    txt_btn = fonte_desc.render(f"MODO: {modo}", True, (0, 0, 0))
    tela.blit(txt_btn, (400 - txt_btn.get_width()//2, 553))

    # === BOTÃO MODOS NO CANTINHO ===
    pygame.draw.rect(tela, (30, 30, 30), (650, 15, 120, 30), border_radius=5)
    pygame.draw.rect(tela, (70, 70, 70), (650, 15, 120, 30), border_radius=5, width=2)
    txt_modos = fonte_desc.render("MODOS ▼", True, (200, 200, 200))
    tela.blit(txt_modos, (710 - txt_modos.get_width()//2, 21))

    # === MENU PRETO NO CANTINHO ===
    if menu_modos_aberto:
        pygame.draw.rect(tela, (0, 0, 0), (650, 50, 130, 190), border_radius=6)
        pygame.draw.rect(tela, CAMARO_YELLOW, (650, 50, 130, 190), border_radius=6, width=2)
        
        for i, nome_modo in enumerate(modos):
            y = 60 + i * 30
            cor = CAMARO_YELLOW_LIGHT if nome_modo == modo_velocidade else (200, 200, 200)
            pygame.draw.rect(tela, (20, 20, 20), (655, y, 120, 26), border_radius=4)
            txt = fonte_desc.render(nome_modo, True, cor)
            tela.blit(txt, (715 - txt.get_width()//2, y + 6))

    # === PUBLICAÇÃO ===
    msg = Twist()
    msg.linear.x = float(linear)
    msg.angular.z = float(angular)
    pub.publish(msg)
    rclpy.spin_once(node, timeout_sec=0)

    pygame.display.flip()
    clock.tick(30)