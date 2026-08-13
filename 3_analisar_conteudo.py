"""
Script Principal da Etapa 3 / Fase 3: Análise de PLN e Mineração Inteligente via Gemini LLM.

Execução independente e idempotente.
Processa a fila de cultos transcritos (.txt e .json), submete ao Google Gemini LLM
e grava os insights na pasta data/insights_fase3/ e na tabela acervo_insights do SQLite.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import DB_PATH, INSIGHTS_DIR, AUDIO_DIR
from 3_mineracao_fase3 import main as run_fase3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa3_AnalisarConteudo")


if __name__ == "__main__":
    run_fase3()
