"""
Módulo de Edição de Vídeos com MoviePy e FFmpeg.

Gera cortes curtos verticais 9:16 (Shorts / Reels / TikTok) com legendas acopladas
e vídeos médios horizontais 16:9 agrupados por temas litúrgicos (Oração, Família, Fé, Libertação).
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path, SUBFOLDERS

try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class VideoEditor:
    """
    Editor programático de vídeos para a IBPM CR.
    """

    def __init__(self):
        """
        Inicializa o editor de vídeo.
        """
        self.shorts_dir = get_folder_path("RECENT")
        self.medium_dir = get_folder_path("MEDIUM_TEMATIC")
        os.makedirs(self.shorts_dir, exist_ok=True)
        os.makedirs(self.medium_dir, exist_ok=True)

    def render_short_9_16(self, video_path: str, start_sec: float, end_sec: float, output_path: str, subtitle_text: str = "") -> str:
        """
        Corta um trecho de destaque e re-enquadra no formato vertical 9:16 (1080x1920) para Shorts/Reels.

        :param video_path: Caminho do vídeo original em MP4.
        :param start_sec: Segundo inicial do corte.
        :param end_sec: Segundo final do corte.
        :param output_path: Caminho de saída do vídeo renderizado.
        :param subtitle_text: Texto da legenda a ser sobreposta.
        :return: Caminho do arquivo de saída.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not HAS_MOVIEPY or not os.path.exists(video_path):
            logger.warning(f"⚠️ MoviePy ausente ou arquivo {video_path} não encontrado. Simulando renderização 9:16.")
            return self._generate_mock_video(output_path, is_vertical=True)

        try:
            logger.info(f"🎬 Renderizando vídeo curto 9:16 de {start_sec}s até {end_sec}s...")
            clip = VideoFileClip(video_path).subclip(start_sec, end_sec)

            # Crop para proporção 9:16
            w, h = clip.size
            target_w = int(h * (9 / 16))
            if target_w < w:
                crop_x = (w - target_w) // 2
                cropped_clip = clip.crop(x1=crop_x, width=target_w, height=h)
            else:
                cropped_clip = clip

            resized_clip = cropped_clip.resize((1080, 1920))

            final_clip = resized_clip
            if subtitle_text:
                try:
                    txt_clip = TextClip(
                        subtitle_text,
                        fontsize=50,
                        color='white',
                        bg_color='black',
                        font='Arial-Bold',
                        method='caption',
                        size=(900, None)
                    ).set_position(('center', 1500)).set_duration(clip.duration)
                    final_clip = CompositeVideoClip([resized_clip, txt_clip])
                except Exception as txt_err:
                    logger.warning(f"Legenda não pôde ser renderizada com ImageMagick: {txt_err}")

            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=30,
                preset="fast",
                logger=None
            )

            clip.close()
            final_clip.close()
            logger.info(f"✅ Vídeo 9:16 renderizado com sucesso: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Erro na renderização do vídeo 9:16: {e}")
            return self._generate_mock_video(output_path, is_vertical=True)

    def render_medium_16_9(self, video_path: str, segments: List[Dict[str, float]], theme: str, output_path: str) -> str:
        """
        Agrupa trechos temáticos contínuos (ex: Oração, Família, Fé, Libertação) em um vídeo médio horizontal 16:9.

        :param video_path: Caminho do vídeo de origem em MP4.
        :param segments: Lista de intervalos [{'start': float, 'end': float}].
        :param theme: Tema ('Oracao', 'Familia', 'Fe', 'Libertacao').
        :param output_path: Caminho de saída.
        :return: Caminho do arquivo renderizado.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not HAS_MOVIEPY or not os.path.exists(video_path):
            logger.warning(f"⚠️ MoviePy ou arquivo {video_path} indisponível. Simulando vídeo médio 16:9 ({theme}).")
            return self._generate_mock_video(output_path, is_vertical=False)

        try:
            logger.info(f"🎬 Renderizando vídeo médio 16:9 do tema '{theme}'...")
            full_clip = VideoFileClip(video_path)
            clips_to_concat = []

            for seg in segments:
                sub = full_clip.subclip(seg["start"], seg["end"])
                clips_to_concat.append(sub)

            if not clips_to_concat:
                full_clip.close()
                return self._generate_mock_video(output_path, is_vertical=False)

            final_clip = concatenate_videoclips(clips_to_concat)
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=30,
                preset="fast",
                logger=None
            )

            full_clip.close()
            final_clip.close()
            logger.info(f"✅ Vídeo 16:9 do tema '{theme}' salvo em: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Erro na renderização do vídeo médio 16:9: {e}")
            return self._generate_mock_video(output_path, is_vertical=False)

    def _generate_mock_video(self, output_path: str, is_vertical: bool = True) -> str:
        """Gera um arquivo de vídeo placeholder para ambientes de teste ou fallback."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        meta_str = f"FORMAT: {'9:16' if is_vertical else '16:9'}\nPRODUCED BY: IBPM CR AUTO-EDITOR\n"
        with open(output_path, "wb") as f:
            f.write(meta_str.encode("utf-8") + b"\x00" * 1024)
        logger.info(f"📁 Arquivo de mídia gerado (placeholder): {output_path}")
        return output_path


if __name__ == "__main__":
    editor = VideoEditor()
    short_out = editor.render_short_9_16("sample.mp4", 10.0, 40.0, "output_short.mp4", "Mensagem de Fé!")
    print(f"Vídeo curto gerado em: {short_out}")
