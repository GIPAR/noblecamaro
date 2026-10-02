#!/bin/bash
# start_backend.sh — Inicia o servidor Flask com banco de dados SQLite e orquestrador LLM
cd "$(dirname "$0")"
export FLASK_DEBUG=false
if [ -f "backend/venv/bin/python3" ]; then
  backend/venv/bin/python3 backend/server.py
else
  python3 backend/server.py
fi
