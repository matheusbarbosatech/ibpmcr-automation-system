"""
Script de Inicialização e Montagem do Google Drive / Diretórios Locais.

Este script cria programmaticamente as 16 subpastas do ecossistema IBPM CR
no Google Drive (/content/drive/MyDrive/IBPM_CR_Cortes/) ou no armazenamento local.
"""

import os
import sys
import logging
from pathlib import Path

# Ajusta path para importar settings
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import OUTPUT_BASE_DIR, SUBFOLDERS, THEMATIC_SUBFOLDERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def setup_environment() -> None:
    """
    Inicializa a estrutura de diretórios no Google Drive ou armazenamento local.
    Garante a presença das 16 subpastas principais e subpastas temáticas.
    """
    logger.info(f"Iniciando configuração de diretórios em: {OUTPUT_BASE_DIR}")

    try:
        # Cria diretório raiz
        os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

        # Cria subpastas primárias
        for key, folder in SUBFOLDERS.items():
            if key == "STATE":
                continue  # O estado é um arquivo JSON, não pasta
            folder_path = os.path.join(OUTPUT_BASE_DIR, folder)
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"Pasta garantida: {folder}")

        # Cria subpastas temáticas em 04_Videos_Medios_Tematicos
        medium_tematic_path = os.path.join(OUTPUT_BASE_DIR, SUBFOLDERS["MEDIUM_TEMATIC"])
        for theme in THEMATIC_SUBFOLDERS:
            theme_path = os.path.join(medium_tematic_path, theme)
            os.makedirs(theme_path, exist_ok=True)
            logger.info(f"Subpasta temática garantida: {SUBFOLDERS['MEDIUM_TEMATIC']}/{theme}")

        logger.info("✅ Estrutura de diretórios inicializada com sucesso!")

    except Exception as e:
        logger.error(f"❌ Erro ao inicializar diretórios: {e}")
        raise e


if __name__ == "__main__":
    setup_environment()
