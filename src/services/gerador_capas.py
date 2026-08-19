"""
Gerador de Capas e Thumbnails Automático (100% Grátis & Local em Python) - IBPM CR Automation System.

Utiliza OpenCV para extrair o melhor frame do pregador e Pillow (PIL) para desenhar
design gráfico de alto impacto: vinheta de degradê, tipografia viral com sombra projetada,
badge de categoria e branding da igreja (@ibpmcr).
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger

logger = get_logger("CoverGenerator")


class CoverGenerator:
    """
    Gerador Gráfico Local de Capas para Redes Sociais.
    """

    def __init__(self, target_w_vert: int = 1080, target_h_vert: int = 1920):
        self.target_w_vert = target_w_vert
        self.target_h_vert = target_h_vert
        logger.info("🎨 inicializado Gerador Gráfico de Capas 100% Local (Pillow/OpenCV).")

    def extract_best_frame(self, video_path: Path, timestamp_sec: float) -> np.ndarray:
        """
        Extrai o frame mais límpido da mídia no timestamp especificado.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Vídeo de origem não encontrado: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        target_frame = int(timestamp_sec * fps)

        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            # Fallback para o primeiro frame se o timestamp falhar
            cap = cv2.VideoCapture(str(video_path))
            ret, frame = cap.read()
            cap.release()

        if not ret or frame is None:
            raise RuntimeError(f"Não foi possível extrair nenhum frame de {video_path}")

        return frame

    def create_gradient_vignette(self, width: int, height: int) -> Image.Image:
        """
        Cria uma máscara de degradê escuro (vignette) nas bordas superior e inferior.
        """
        mask = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(mask)

        # Gradiente Superior
        top_h = int(height * 0.35)
        for y in range(top_h):
            alpha = int(220 * (1 - (y / top_h) ** 1.5))
            draw.line([(0, y), (width, y)], fill=(10, 10, 25, alpha))

        # Gradiente Inferior
        bot_h = int(height * 0.40)
        bot_start = height - bot_h
        for y in range(bot_start, height):
            progress = (y - bot_start) / bot_h
            alpha = int(235 * (progress ** 1.3))
            draw.line([(0, y), (width, y)], fill=(10, 10, 25, alpha))

        return mask

    def generate_cover(
        self,
        video_path: Path,
        timestamp_sec: float,
        titulo: str,
        categoria: str,
        output_jpg: Path,
        is_vertical: bool = True
    ) -> Path:
        """
        Gera a arte da capa em formato JPG em alta resolução.
        """
        output_jpg.parent.mkdir(parents=True, exist_ok=True)
        frame_bgr = self.extract_best_frame(video_path, timestamp_sec)

        # Converte BGR (OpenCV) -> RGB (PIL)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        target_w = self.target_w_vert if is_vertical else 1920
        target_h = self.target_h_vert if is_vertical else 1080

        # Redimensiona mantendo proporção e corta o centro
        img_w, img_h = img.size
        ratio = max(target_w / img_w, target_h / img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))

        # Aplica o degradê de contraste
        vignette = self.create_gradient_vignette(target_w, target_h)
        img.paste(vignette, (0, 0), vignette)

        draw = ImageDraw.Draw(img)

        # Tenta carregar fontes nativas ou fallback do PIL
        try:
            font_title = ImageFont.truetype("arial.ttf", 62 if is_vertical else 52)
            font_badge = ImageFont.truetype("arial.ttf", 36 if is_vertical else 30)
            font_brand = ImageFont.truetype("arialbd.ttf", 40 if is_vertical else 34)
        except Exception:
            font_title = ImageFont.load_default()
            font_badge = ImageFont.load_default()
            font_brand = ImageFont.load_default()

        # 1. Desenha Badge de Categoria no Topo
        badge_text = f"  🔥 {categoria.upper()} | IBPM CR  "
        badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
        bw = badge_bbox[2] - badge_bbox[0]
        bh = badge_bbox[3] - badge_bbox[1]

        bx = (target_w - bw) // 2
        by = int(target_h * 0.12)

        # Fundo do Badge (Pill)
        pad_x, pad_y = 18, 10
        draw.rounded_rectangle(
            [bx - pad_x, by - pad_y, bx + bw + pad_x, by + bh + pad_y],
            radius=16,
            fill=(220, 38, 38, 230),  # Vermelho vibrante
            outline=(255, 255, 255, 255),
            width=2
        )
        draw.text((bx, by), badge_text, fill=(255, 255, 255), font=font_badge)

        # 2. Desenha Título Viral com Quebra de Linha e Sombra
        max_title_w = target_w - 120
        words = titulo.upper().split()
        lines = []
        curr_line = []

        for w in words:
            curr_line.append(w)
            line_str = " ".join(curr_line)
            bbox = draw.textbbox((0, 0), line_str, font=font_title)
            if bbox[2] - bbox[0] > max_title_w:
                curr_line.pop()
                if curr_line:
                    lines.append(" ".join(curr_line))
                curr_line = [w]
        if curr_line:
            lines.append(" ".join(curr_line))

        # Renderiza texto centralizado com Sombra Projetada
        line_height = 75 if is_vertical else 60
        total_title_h = len(lines) * line_height
        start_y = int(target_h * 0.65) if is_vertical else int(target_h * 0.55)

        for i, line in enumerate(lines[:3]):  # No máximo 3 linhas
            line_bbox = draw.textbbox((0, 0), line, font=font_title)
            lw = line_bbox[2] - line_bbox[0]
            lx = (target_w - lw) // 2
            ly = start_y + (i * line_height)

            # Sombra Projetada (Drop Shadow)
            shadow_offsets = [(3, 3), (-2, 2), (2, -2), (-2, -2)]
            for sx, sy in shadow_offsets:
                draw.text((lx + sx, ly + sy), line, fill=(0, 0, 0, 240), font=font_title)

            # Texto Principal Amarelo/Branco Vibrante
            draw.text((lx, ly), line, fill=(255, 230, 0) if i == 0 else (255, 255, 255), font=font_title)

        # 3. Branding do Canal no Rodapé
        brand_text = "📖 @ibpmcr • Mensagem Edificante"
        b_bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
        br_w = b_bbox[2] - b_bbox[0]
        br_x = (target_w - br_w) // 2
        br_y = target_h - int(target_h * 0.08)

        # Sombra do Branding
        draw.text((br_x + 2, br_y + 2), brand_text, fill=(0, 0, 0, 220), font=font_brand)
        draw.text((br_x, br_y), brand_text, fill=(255, 255, 255), font=font_brand)

        # Salva o arquivo JPG final da Capa
        img.convert("RGB").save(output_jpg, "JPEG", quality=95)
        logger.info(f"✅ Capa criada com sucesso: {output_jpg.name} ({target_w}x{target_h})")
        return output_jpg
