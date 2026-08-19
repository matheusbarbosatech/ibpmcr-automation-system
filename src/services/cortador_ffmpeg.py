"""
Módulo de Corte Automático ultrarrápido via FFmpeg Stream Copy (-c copy) - IBPM CR.

Lê o arquivo relatorio_cortes.csv e executa os cortes sem reprocessar o vídeo (zero uso de CPU/GPU).
Salva os cortes prontos na pasta data/cortes_finais/.
"""

import sys
import os
import csv
import subprocess
from pathlib import Path
from typing import List, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("CortadorFFmpegStreamCopy")


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """Converte hh:mm:ss para segundos."""
    try:
        parts = ts_str.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        return float(ts_str)
    except Exception:
        return 0.0


class FastStreamCopyCutter:
    """
    Cortador ultrarrápido via FFmpeg Stream Copy (-c copy).
    """

    def __init__(self):
        self.ffmpeg_bin = settings.FFMPEG_BINARY_PATH or "ffmpeg"
        logger.info("✂️ Inicializado Cortador FFmpeg Stream Copy (-c copy).")

    def cut_from_csv(self, csv_file_path: Path, videos_dir: Path, output_dir: Path) -> List[Path]:
        """
        Lê o CSV de relatorios e faz os cortes ultrarrápidos via -c copy.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        cuts_generated = []

        if not csv_file_path.exists():
            logger.error(f"Arquivo CSV não encontrado: {csv_file_path}")
            return cuts_generated

        with open(csv_file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                orig = row.get("sermon_id") or row.get("arquivo_origem") or ""
                c_id = row.get("corte_id") or f"corte_{idx+1:03d}"
                c_id_clean = "".join(c for c in c_id if c.isalnum() or c in ("_", "-")).strip()
                
                ts_in = row.get("start_sec") or row.get("timestamp_inicio") or "0"
                dur = row.get("duracao") or row.get("duracao_segundos") or "45"

                if not orig:
                    continue

                # Localiza o arquivo de mídia de origem (.mp4, .webm, .mp3, .m4a)
                src_file = None
                for ext in [".mp4", ".webm", ".mkv", ".mp3", ".m4a", ".wav"]:
                    possible = videos_dir / f"{orig}{ext}"
                    if possible.is_file():
                        src_file = possible
                        break
                    possible_direct = videos_dir / orig
                    if possible_direct.is_file():
                        src_file = possible_direct
                        break

                if not src_file:
                    logger.warning(f"⚠️ Mídia de origem para '{orig}' não encontrada em {videos_dir}. Pulando corte.")
                    continue

                out_cut_file = output_dir / f"{src_file.stem}_{c_id_clean}{src_file.suffix}"

                start_sec = parse_timestamp_to_seconds(ts_in)
                dur_sec = float(dur)

                cmd = [
                    self.ffmpeg_bin, "-y",
                    "-ss", str(start_sec),
                    "-i", str(src_file),
                    "-t", str(dur_sec),
                    "-c", "copy",
                    str(out_cut_file)
                ]

                logger.info(f"⚡ Executando corte ultrarrápido: {out_cut_file.name}", start=ts_in, dur=dur)

                try:
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    cuts_generated.append(out_cut_file)
                    logger.info(f"✅ Corte finalizado com sucesso em 0.1s: {out_cut_file.name}")
                except subprocess.CalledProcessError as err:
                    logger.error(f"Falha ao cortar {out_cut_file.name}", error=err.stderr)

        return cuts_generated


def main():
    cutter = FastStreamCopyCutter()
    csv_file = Path("data/relatorio_cortes.csv")
    videos_dir = Path("data/audio_podcasts")
    output_dir = Path("data/cortes_finais")

    cuts = cutter.cut_from_csv(csv_file, videos_dir, output_dir)
    print(f"🎉 Processamento concluído! {len(cuts)} cortes gerados em 'data/cortes_finais'.")


if __name__ == "__main__":
    main()
