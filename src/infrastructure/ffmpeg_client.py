"""
Cliente de Infraestrutura FFmpeg / FFprobe - IBPM CR Automation System.

Encapsula chamadas de subprocesso para processamento audiovisual de alta performance,
executando corte frame-accurate (CFR 30fps), conversão vertical 9:16 (Crop + Scale),
queima de legendas animadas (.ASS), e normalização EBU R128 (-16 LUFS) com Auto-Ducking.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("FFmpegClient")


class FFmpegClient:
    """
    Wrapper robusto para manipulação de mídia via subprocessos FFmpeg e FFprobe.
    """

    def __init__(self, ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None):
        self.ffmpeg_binary = ffmpeg_path or settings.FFMPEG_BINARY_PATH
        self.ffprobe_binary = ffprobe_path or settings.FFPROBE_BINARY_PATH

    def get_media_metadata(self, media_path: Path) -> Dict[str, Any]:
        """
        Extrai metadados do arquivo de vídeo/áudio usando FFprobe em formato JSON.
        """
        if not media_path.exists():
            raise FileNotFoundError(f"Arquivo de mídia não encontrado: {media_path}")

        cmd = [
            self.ffprobe_binary,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(media_path)
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0.0))
            
            logger.info("Metadados extraídos com sucesso", media_path=str(media_path), duration_sec=duration)
            return data
        except subprocess.CalledProcessError as e:
            logger.error("Falha ao executar FFprobe", error=e.stderr, media_path=str(media_path))
            raise RuntimeError(f"Erro no FFprobe: {e.stderr}")
        except Exception as e:
            logger.error("Erro inesperado ao ler metadados via FFprobe", error=str(e))
            raise

    def analyze_audio_loudness(self, audio_path: Path) -> Dict[str, str]:
        """
        Executa a Passagem 1 da normalização EBU R128 para extrair métricas de sonoridade (LUFS/TP).
        """
        cmd = [
            self.ffmpeg_binary,
            "-hide_banner",
            "-i", str(audio_path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f", "null",
            "-"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            stderr_out = res.stderr

            # Extrai o bloco JSON impresso no stderr pelo loudnorm
            json_match = re.search(r"\{[\s\S]*\"input_i\"[\s\S]*\}", stderr_out)
            if json_match:
                loudness_data = json.loads(json_match.group(0))
                logger.info("Análise de Loudness EBU R128 concluída", metrics=loudness_data)
                return loudness_data

            # Métricas padrão em caso de fallback
            return {
                "input_i": "-24.0",
                "input_tp": "-2.0",
                "input_lra": "11.0",
                "input_thresh": "-34.0",
                "target_offset": "0.0"
            }
        except Exception as e:
            logger.warning("Falha na análise de Loudness EBU R128. Usando valores default.", error=str(e))
            return {
                "input_i": "-24.0",
                "input_tp": "-2.0",
                "input_lra": "11.0",
                "input_thresh": "-34.0",
                "target_offset": "0.0"
            }

    def render_short_form(
        self,
        video_input: Path,
        output_path: Path,
        start_sec: float,
        end_sec: float,
        ass_subtitle_path: Optional[Path] = None,
        bg_music_input: Optional[Path] = None,
        target_width: int = 1080,
        target_height: int = 1920,
        enable_ducking: bool = True,
        ducking_db: float = -22.0,
        job_id: str = "job_short_render"
    ) -> Path:
        """
        Renderiza um corte Short-Form (9:16) com corte frame-accurate, recomposição visual,
        legenda animada .ASS e mixagem de áudio EBU R128 com sidechain ducking.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_sec = max(1.0, end_sec - start_sec)

        # Trata o caminho do arquivo de legenda .ASS para ser aceito pelo filtro do FFmpeg no Windows
        ass_filter_str = ""
        if ass_subtitle_path and ass_subtitle_path.exists():
            clean_ass_path = str(ass_subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")
            ass_filter_str = f",subtitles='{clean_ass_path}'"

        # Montagem do Filtergraph de Vídeo (Crop 9:16 + Scale 1080x1920 + ASS Subtitles + Drawbox Progress Bar)
        video_filter = (
            f"crop=ih*(9/16):ih,scale={target_width}:{target_height},"
            f"fps=30,format=yuv420p"
            f"{ass_filter_str},"
            f"drawbox=x=0:y=1890:w='iw*(t/{duration_sec:.2f})':h=30:color=Red@0.8:t=fill"
        )

        # Montagem dos argumentos base do FFmpeg
        cmd = [
            self.ffmpeg_binary,
            "-y",
            "-ss", f"{start_sec:.3f}",
            "-accurate_seek",
            "-i", str(video_input),
            "-to", f"{end_sec:.3f}"
        ]

        if bg_music_input and bg_music_input.exists() and enable_ducking:
            # Entrada de áudio secundário para mixagem com Auto-Ducking
            cmd.extend(["-i", str(bg_music_input)])
            audio_filter = (
                "[0:a]highpass=f=85:poles=2,loudnorm=I=-16:TP=-1.5:LRA=11:linear=true[voice_clean];"
                "[1:a]volume=0.25[bg_attenuated];"
                "[bg_attenuated][voice_clean]sidechaincompress=threshold=0.0316:ratio=5:attack=15:release=300[bg_ducked];"
                "[voice_clean][bg_ducked]amix=inputs=2:weights=1.0 0.8:mixformat=float[aout]"
            )
            cmd.extend([
                "-filter_complex", f"[0:v]{video_filter}[vout];{audio_filter}",
                "-map", "[vout]",
                "-map", "[aout]"
            ])
        else:
            # Apenas a trilha de voz principal com normalização EBU R128
            audio_filter = "highpass=f=85:poles=2,loudnorm=I=-16:TP=-1.5:LRA=11:linear=true"
            cmd.extend([
                "-vf", video_filter,
                "-af", audio_filter
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            str(output_path)
        ])

        logger.info(
            "Iniciando renderização de vídeo Short-Form no FFmpeg",
            job_id=job_id,
            start_sec=start_sec,
            end_sec=end_sec,
            output_file=output_path.name
        )

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Renderização concluída com sucesso", job_id=job_id, output_path=str(output_path))
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(
                "Falha na renderização do FFmpeg",
                job_id=job_id,
                exit_code=e.returncode,
                stderr=e.stderr[-1000:] if e.stderr else ""
            )
            raise RuntimeError(f"Erro no FFmpeg (code {e.returncode}): {e.stderr}")


import re
