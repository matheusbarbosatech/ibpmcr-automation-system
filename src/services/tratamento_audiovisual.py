"""
Módulo de Tratamento Audiovisual Automático & Enquadramento Inteligente - IBPM CR Automation System.

Executa:
1. Enquadramento Inteligente (Smart Auto-Framing 9:16 com rastreamento de movimento/rosto do pregador no palco).
2. Tratamento Automático de Áudio (Filtro Anti-Ruído Highpass 80Hz, Equalizador de Presença Vocal 3kHz, Compressor Dinâmico e Normalização EBU R128).
3. Tratamento Automático de Vídeo (Realce de Cor, Contraste das luzes da igreja e Nitidez Unsharp Masking de Alta Definição).
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.reframe_engine import SmoothAutoReframe

from src.services.gerador_capas import CoverGenerator

logger = get_logger("AutoAudiovisualEnhancer")


class AutoAudiovisualEnhancer:
    """
    Motor de Tratamento Audiovisual Automático Studio Pro.
    """

    def __init__(self, ffmpeg_bin: Optional[str] = None):
        self.ffmpeg_bin = ffmpeg_bin or settings.FFMPEG_BINARY_PATH or "ffmpeg"
        self.reframe_engine = SmoothAutoReframe()
        self.cover_generator = CoverGenerator()
        logger.info("🎨 inicializado Motor de Tratamento Audiovisual Automático Studio Pro + Gerador de Capas.")

    def build_audio_enhancement_filter(self, target_lufs: float = -16.0) -> str:
        """
        Cadeia de Filtros de Áudio Profissional para Pregadores:
        1. highpass=f=80 (corta ruído elétrico/hum de ar condicionado/microfone)
        2. equalizer=f=3000:g=2.5 (realce de presença e inteligibilidade da voz)
        3. acompressor (equaliza trechos suaves vs fala exaltada)
        4. loudnorm (normalização broadcast EBU R128 no padrão Reels/Shorts)
        """
        return (
            f"aresample=async=1,"
            f"highpass=f=80:poles=2,"
            f"equalizer=f=3000:width_type=h:width=1500:g=2.5,"
            f"acompressor=threshold=-18dB:ratio=3:attack=10:release=100:makeup=2,"
            f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:linear=true"
        )


    def build_video_enhancement_filter(self, crop_expr: str = "crop=ih*(9/16):ih:(iw-ow)/2:0", is_vertical: bool = True) -> str:
        """
        Cadeia de Filtros de Vídeo Profissional:
        1. Enquadramento 9:16 (Smart Auto-Framing ou crop 16:9)
        2. Realce de Cor/Contraste (`eq`)
        3. Nitidez Profissional (`unsharp`)
        """
        filters = []
        if is_vertical:
            filters.append(crop_expr)
            filters.append("scale=1080:1920:flags=lanczos:force_original_aspect_ratio=increase")
            filters.append("crop=1080:1920")

        # Realce de Cores da Igreja & Contraste
        filters.append("eq=contrast=1.06:brightness=0.01:saturation=1.12")
        # Nitidez de Alta Definição (Unsharp Masking)
        filters.append("unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=0.9")


        filters.append("fps=30")
        filters.append("format=yuv420p")

        return ",".join(filters)

    def embed_cover_in_mp4(self, video_path: Path, cover_jpg: Path, output_video: Path) -> Path:
        """
        Embute a imagem JPG de capa diretamente na stream de vídeo do MP4 via FFmpeg (-disposition:v:1 attached_pic).
        """
        temp_out = output_video.with_name(f"temp_cover_{output_video.name}")
        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", str(video_path),
            "-i", str(cover_jpg),
            "-map", "0",
            "-map", "1",
            "-c:v:0", "copy",
            "-c:a", "copy",
            "-c:v:1", "mjpeg",
            "-disposition:v:1", "attached_pic",
            str(temp_out)
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            if temp_out.exists():
                if output_video.exists():
                    output_video.unlink()
                temp_out.rename(output_video)
                logger.info(f"🖼️ Capa embutida com sucesso no arquivo MP4: {output_video.name}")
                return output_video
        except Exception as e:
            logger.warning(f"Não foi possível embutir a capa no MP4: {e}")
            if temp_out.exists():
                temp_out.unlink()
        return video_path

    def enhance_clip(
        self,
        input_video: Path,
        output_video: Path,
        start_sec: float,
        end_sec: float,
        titulo: str = "Mensagem Edificante",
        categoria: str = "Pregação",
        is_vertical: bool = True,
        job_id: str = "auto_enhance"
    ) -> Path:
        """
        Executa o render completo com Enquadramento Inteligente, Tratamento Audiovisual,
        Geração da Imagem de Capa e Embutimento da Capa no Vídeo MP4.
        """
        output_video.parent.mkdir(parents=True, exist_ok=True)
        duration_sec = max(1.0, end_sec - start_sec)

        # 1. Calcula o Enquadramento Inteligente com Rastreamento do Pregador
        if is_vertical:
            logger.info("🔍 Analisando movimentação do pregador para Enquadramento Inteligente...", job_id=job_id)
            crop_expr = self.reframe_engine.analyze_video_smart_crop(
                video_path=str(input_video),
                start_sec=start_sec,
                duration_sec=duration_sec
            )
        else:
            crop_expr = "scale=1920:1080"

        # 2. Constrói Filtros de Áudio e Vídeo
        af_chain = self.build_audio_enhancement_filter(target_lufs=-16.0 if is_vertical else -14.0)
        vf_chain = self.build_video_enhancement_filter(crop_expr=crop_expr, is_vertical=is_vertical)

        cmd = [
            self.ffmpeg_bin, "-y",
            "-ss", f"{start_sec:.3f}",
            "-accurate_seek",
            "-i", str(input_video),
            "-t", f"{duration_sec:.3f}",
            "-vf", vf_chain,
            "-af", af_chain,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "17",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            str(output_video)
        ]

        logger.info(f"⚡ Executando Tratamento Audiovisual Studio Pro: {output_video.name}", job_id=job_id)

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"✅ Tratamento Audiovisual concluído com sucesso: {output_video.name}", job_id=job_id)

            # 3. Gerar Capa JPG Local e Embutir no MP4
            try:
                cover_jpg = output_video.with_name(f"{output_video.stem}_capa.jpg")
                mid_point_sec = start_sec + (duration_sec * 0.3)
                self.cover_generator.generate_cover(
                    video_path=input_video,
                    timestamp_sec=mid_point_sec,
                    titulo=titulo,
                    categoria=categoria,
                    output_jpg=cover_jpg,
                    is_vertical=is_vertical
                )
                self.embed_cover_in_mp4(output_video, cover_jpg, output_video)
            except Exception as e_cover:
                logger.warning(f"Aviso ao gerar capa: {e_cover}")

            return output_video

        except subprocess.CalledProcessError as e:
            logger.error(f"Falha no Tratamento Audiovisual: {e.stderr}", job_id=job_id)
            raise RuntimeError(f"Erro no FFmpeg: {e.stderr}")

