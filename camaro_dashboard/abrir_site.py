#!/usr/bin/env python3
"""
abrir_site.py — Sobe tudo do Camaro Dashboard com UM comando.

Uso:
    python3 abrir_site.py
    # ou, apos dar permissao (chmod +x abrir_site.py):
    ./abrir_site.py

O que ele faz:
  1. Sobe o backend Flask (porta 5000) com o Python da venv, se ainda
     nao estiver no ar (log em /tmp/camaro_backend.log);
  2. Espera o servidor responder;
  3. Abre o site (frontend servido pelo proprio backend) no Google Chrome.

Para parar o backend depois: pkill -f "backend/server.py"
"""

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
SERVER_PY = os.path.join(BACKEND_DIR, "server.py")
VENV_PY = os.path.join(BACKEND_DIR, "venv", "bin", "python3")
LOG_FILE = "/tmp/camaro_backend.log"
URL = "http://localhost:5000"
TIMEOUT_S = 30


def porta_ocupada(porta: int) -> bool:
    """True se há alguém ouvindo na porta (mesmo com backlog cheio)."""
    for _ in range(3):
        try:
            with socket.create_connection(("127.0.0.1", porta), timeout=1):
                return True
        except socket.timeout:
            # Handshake não completou: backlog cheio = alguém ouvindo
            return True
        except OSError:
            time.sleep(0.2)
    return False


def site_responde() -> bool:
    try:
        with urllib.request.urlopen(URL + "/api/camera/status", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def checar_ambiente() -> str:
    """Valida tudo antes de subir. Retorna o Python a usar. Sai com erro claro."""
    if not os.path.isfile(SERVER_PY):
        print(f"[ERRO] Servidor nao encontrado: {SERVER_PY}")
        print("       Rode este script de dentro da pasta camaro_dashboard.")
        sys.exit(1)
    if os.path.isfile(VENV_PY):
        return VENV_PY
    print(f"[aviso] venv nao encontrada em {VENV_PY}; usando {sys.executable}")
    print("        (recomendado: cd backend && python3 -m venv venv && "
          "venv/bin/pip install -r ../requirements.txt roslibpy)")
    return sys.executable


def subir_backend() -> None:
    if site_responde():
        print("[ok] Backend ja esta no ar em", URL)
        return
    if porta_ocupada(5000):
        print("[ERRO] A porta 5000 esta ocupada por outro programa "
              "(e nao e o backend do Camaro).")
        print("       Descubra com: ss -tlnp | grep 5000")
        sys.exit(1)
    python = checar_ambiente()
    print(f"[..] Subindo backend com {python} ...")
    log = open(LOG_FILE, "a")
    proc = subprocess.Popen(
        [python, SERVER_PY],
        cwd=BACKEND_DIR,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,  # desgruda do terminal: pode fechar sem matar
    )
    time.sleep(1)
    if proc.poll() is not None:
        print(f"[ERRO] O backend morreu na largada (codigo {proc.returncode}).")
        mostrar_cauda_log()
        sys.exit(1)
    for _ in range(TIMEOUT_S * 2):
        if site_responde():
            print("[ok] Backend no ar em", URL)
            return
        if proc.poll() is not None:
            print(f"[ERRO] O backend morreu durante a subida (codigo {proc.returncode}).")
            mostrar_cauda_log()
            sys.exit(1)
        time.sleep(0.5)
    print(f"[ERRO] Backend nao respondeu em {TIMEOUT_S}s. Ultimas linhas do log:")
    mostrar_cauda_log()
    sys.exit(1)


def mostrar_cauda_log(n: int = 15) -> None:
    try:
        with open(LOG_FILE) as f:
            linhas = f.read().splitlines()[-n:]
        print("--- " + LOG_FILE + " ---")
        for linha in linhas:
            print("  " + linha)
    except OSError as e:
        print(f"  (nao consegui ler o log: {e})")


def abrir_chrome() -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chrome")
    if not chrome:
        print(f"[aviso] Chrome nao encontrado. Abra manualmente: {URL}")
        return
    print("[..] Abrindo o Chrome ...")
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    subprocess.Popen(
        [chrome, "--new-window", URL],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
    print("[ok] Site aberto no Chrome:", URL)


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    subir_backend()
    abrir_chrome()
    print("\nTudo funcional! Cliente: cliente/123 | Admin: admin/123")
