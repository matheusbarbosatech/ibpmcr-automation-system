"""
Preparador de Áudio Inteligente (Pré-Processamento da Fase 2) - IBPM CR System.

Estratégia de Otimização Acústica:
1. Corta a introdução de louvor/música (~35 a 45 min de áudio contínuo).
2. Extrai apenas a fatia da pregação real em .mp3 mono 16kHz / 32kbps (~10MB a 12MB).
3. Reduz o volume total de processamento em 60% e acelera a transcrição em 3x!

Uso:
    python -m src.services.preparador_audio_sermon "data/audio_podcasts/seu_audio.webm"
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("PreparadorAudioSermon")


class SermonAudioPreparer:
    """
    Filtro Acústico para remoção de louvor inicial e extração rápida da pregação.
    """

    def __init__(self):
        self.ffmpeg_bin = settings.FFMPEG_BINARY_PATH or "ffmpeg"
        logger.info("🎙️ Inicializado Preparador de Áudio de Pregações.")

    def get_audio_duration_seconds(self, audio_file: Path) -> float:
        """Obtém a duração total do áudio em segundos via ffprobe."""
        ffprobe_bin = settings.FFPROBE_BINARY_PATH or "ffprobe"
        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_file)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            return 7200.0  # Fallback: 2 horas

    def extrair_apenas_pregacao(
        self,
        input_audio: Path,
        output_audio: Path,
        worship_offset_minutes: float = 35.0
    ) -> Path:
        """
        Corta o louvor inicial e exporta um MP3 mono ultra-leve (~10MB) contendo a pregação.
        """
        output_audio.parent.mkdir(parents=True, exist_ok=True)
        total_duration_sec = self.get_audio_duration_seconds(input_audio)
        start_sec = worship_offset_minutes * 60.0

        # Se o áudio for menor que o offset, começa do início
        if start_sec >= total_duration_sec:
            start_sec = 0.0

        dur_sec = max(1800.0, total_duration_sec - start_sec)

        cmd = [
            self.ffmpeg_bin, "-y",
            "-threads", "1",
            "-ss", str(start_sec),
            "-i", str(input_audio),
            "-t", str(dur_sec),
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "32k",
            str(output_audio)
        ]

        logger.info(
            "✂️ Limpando áudio: removendo louvor e extraindo pregação",
            input=input_audio.name,
            corte_inicio=f"{worship_offset_minutes} min",
            saida=output_audio.name
        )

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            size_mb = round(output_audio.stat().st_size / (1024 * 1024), 2)
            logger.info(f"✅ Pregação extraída com sucesso ({size_mb} MB): {output_audio.name}")
            return output_audio
        except subprocess.CalledProcessError as e:
            logger.error("Falha ao extrair fatia da pregação via FFmpeg", error=e.stderr)
            return input_audio


def main():
    parser = argparse.ArgumentParser(description="Remoção de louvor e extração rápida da pregação")
    parser.add_argument("audio_path", help="Caminho do áudio do culto")
    parser.add_argument("--offset", type=float, default=35.0, help="Minutos de louvor a ignorar no início (padrão: 35 min)")

    args = parser.parse_args()
    inp = Path(args.audio_path)
    out = Path("data/audio_podcasts/pregacoes_limpas") / f"{inp.stem}_pregacao.mp3"

    preparer = SermonAudioPreparer()
    preparer.extrair_apenas_pregacao(inp, out, worship_offset_minutes=args.offset)


if __name__ == "__main__":
    main()
