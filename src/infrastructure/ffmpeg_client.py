"""
Cliente de Infraestrutura FFmpeg / FFprobe - IBPM CR Automation System.

Encapsula chamadas de subprocesso para processamento audiovisual de alta performance,
executando corte frame-accurate (CFR 30fps), conversão vertical 9:16 (Crop + Scale)
e conversão horizontal 16:9 (Mid-Form YouTube), queima de legendas animadas (.ASS)
e normalização EBU R128 (-16 LUFS) com Auto-Ducking.
"""

import sys
import os
import re
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
        """Extrai metadados do arquivo de vídeo/áudio usando FFprobe em formato JSON."""
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
        job_id: str = "job_short_render"
    ) -> Path:
        """
        Renderiza um corte Short-Form (9:16) com corte frame-accurate, recomposição visual,
        legenda animada .ASS e mixagem de áudio EBU R128 com sidechain ducking.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_sec = max(1.0, end_sec - start_sec)

        ass_filter_str = ""
        if ass_subtitle_path and ass_subtitle_path.exists():
            clean_ass_path = str(ass_subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")
            ass_filter_str = f",subtitles='{clean_ass_path}'"

        video_filter = (
            f"crop=ih*(9/16):ih,scale={target_width}:{target_height},"
            f"fps=30,format=yuv420p"
            f"{ass_filter_str},"
            f"drawbox=x=0:y=1890:w='iw*(t/{duration_sec:.2f})':h=30:color=Red@0.8:t=fill"
        )

        cmd = [
            self.ffmpeg_binary,
            "-y",
            "-ss", f"{start_sec:.3f}",
            "-accurate_seek",
            "-i", str(video_input),
            "-to", f"{end_sec:.3f}"
        ]

        if bg_music_input and bg_music_input.exists() and enable_ducking:
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

        logger.info("Iniciando renderização Short-Form (9:16)", job_id=job_id, output=output_path.name)
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Renderização Short-Form (9:16) concluída", job_id=job_id, file=str(output_path))
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error("Falha no FFmpeg Short-Form", job_id=job_id, stderr=e.stderr)
            raise RuntimeError(f"Erro no FFmpeg: {e.stderr}")

    def render_mid_form(
        self,
        video_input: Path,
        output_path: Path,
        start_sec: float,
        end_sec: float,
        target_width: int = 1920,
        target_height: int = 1080,
        job_id: str = "job_mid_render"
    ) -> Path:
        """
        Renderiza um corte Horizontal Mid-Form (16:9) focado em exegese e estudos teológicos
        para o YouTube, com qualidade HD/4K e áudio normalizado Broadcast EBU R128 (-14 LUFS).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        video_filter = f"scale={target_width}:{target_height},fps=30,format=yuv420p"
        audio_filter = "highpass=f=85:poles=2,loudnorm=I=-14:TP=-1.0:LRA=12:linear=true"

        cmd = [
            self.ffmpeg_binary,
            "-y",
            "-ss", f"{start_sec:.3f}",
            "-accurate_seek",
            "-i", str(video_input),
            "-to", f"{end_sec:.3f}",
            "-vf", video_filter,
            "-af", audio_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "17",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            str(output_path)
        ]

        logger.info("Iniciando renderização Horizontal Mid-Form (16:9)", job_id=job_id, output=output_path.name)
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Renderização Mid-Form (16:9) concluída com sucesso", job_id=job_id, file=str(output_path))
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error("Falha no FFmpeg Mid-Form (16:9)", job_id=job_id, stderr=e.stderr)
            raise RuntimeError(f"Erro no FFmpeg Mid-Form: {e.stderr}")
