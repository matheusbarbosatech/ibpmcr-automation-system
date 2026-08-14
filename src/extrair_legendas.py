"""
Módulo de Extração Automática de Legendas / Transcrições via yt-dlp (Fase 1/2) - IBPM CR.

Baixa legendas automáticas (.vtt/.srt/.json) diretamente do YouTube SEM baixar o arquivo de vídeo pesado (--skip-download).

Uso:
    python -m src.extrair_legendas "URL_DA_PLAYLIST_OU_CANAL"
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Suporte UTF-8 no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger

logger = get_logger("ExtrairLegendasYTDLP")


def baixar_legendas_youtube(target_url: str, output_dir: Path) -> bool:
    """
    Executa o yt-dlp com as flags --write-auto-sub --skip-download --sub-lang pt.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "pt,pt-BR",
        "--sub-format", "vtt/json3/best",
        "--skip-download",
        "-o", out_template,
        target_url
    ]

    logger.info("⚡ Baixando legendas/transcrições do YouTube sem baixar o vídeo...", url=target_url)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("✅ Legendas baixadas com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Falha ao baixar legendas com yt-dlp", error=e.stderr)
        return False
    except Exception as e:
        logger.error("Erro inesperado ao rodar yt-dlp", error=str(e))
        return False


def main():
    parser = argparse.ArgumentParser(description="Extração rápida de legendas do YouTube via yt-dlp")
    parser.add_argument("url", help="URL da playlist, canal ou vídeo do YouTube")
    parser.add_argument("--out", type=str, default="data/transcricoes", help="Pasta de destino das legendas")

    args = parser.parse_args()
    out_path = Path(args.out)
    baixar_legendas_youtube(args.url, out_path)


if __name__ == "__main__":
    main()
