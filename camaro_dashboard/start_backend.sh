#!/bin/bash
# start_backend.sh — Inicia o servidor Flask com banco de dados SQLite e orquestrador LLM
cd "$(dirname "$0")"
export FLASK_DEBUG=false
python3 backend/server.py
