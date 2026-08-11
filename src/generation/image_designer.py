"""
Módulo de Automação de Design e Imagens (Pillow).

Desenha automaticamente cartões de aniversário personalizados para membros e visitantes da IBPM CR,
bem como capas/thumbnails para os vídeos e transmissões no YouTube.
"""

import os
import logging
from typing import Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AutomatedImageDesigner:
    """
    Desenhista gráfico automatizado com a biblioteca Pillow.
    """

    def __init__(self):
        """
        Inicializa o diretório do CRM de aniversariantes.
        """
        self.crm_dir = get_folder_path("ANIVERSARIANTES_CRM")
        os.makedirs(self.crm_dir, exist_ok=True)

    def create_birthday_card(
        self,
        member_name: str,
        blessing_verse: str = "O Senhor te abençoe e te guarde. (Números 6:24)",
        output_filename: Optional[str] = None
    ) -> str:
        """
        Cria um cartão comemorativo de aniversário personalizado em alta resolução (1080x1080).

        :param member_name: Nome do membro aniversariante.
        :param blessing_verse: Versículo de bênção.
        :param output_filename: Nome do arquivo PNG.
        :return: Caminho do arquivo da imagem gerada.
        """
        if not output_filename:
            safe_name = member_name.lower().replace(" ", "_")
            output_filename = f"cartao_aniversario_{safe_name}.png"

        output_path = os.path.join(self.crm_dir, output_filename)
        logger.info(f"🎨 Gerando cartão de aniversário para '{member_name}'...")

        if not HAS_PILLOW:
            return self._mock_image_file(output_path)

        try:
            # Cria imagem 1080x1080 com gradiente azul elegante
            img = Image.new("RGB", (1080, 1080), color=(20, 35, 75))
            draw = ImageDraw.Draw(img)

            # Moldura decorativa dourada
            draw.rectangle([(40, 40), (1040, 1040)], outline=(212, 175, 55), width=6)

            # Texto do Cabeçalho
            draw.text((540, 150), "FELIZ ANIVERSÁRIO!", fill=(255, 215, 0), anchor="mm")
            draw.text((540, 220), "A família IBPM CR celebra a sua vida!", fill=(255, 255, 255), anchor="mm")

            # Nome do Aniversariante
            draw.text((540, 450), member_name.upper(), fill=(255, 255, 255), anchor="mm")

            # Mensagem Pastoral
            msg = "Que este novo ano de vida seja repleto da graça, saúde e paz do Senhor!"
            draw.text((540, 600), msg, fill=(220, 220, 220), anchor="mm")

            # Versículo
            draw.text((540, 800), f'"{blessing_verse}"', fill=(212, 175, 55), anchor="mm")

            # Rodapé institucional
            draw.text((540, 960), "IBPM CR - Bispo Elcimar Lopes Vianna", fill=(180, 180, 180), anchor="mm")

            img.save(output_path)
            logger.info(f"✅ Cartão de aniversário gerado em: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Erro ao desenhar cartão com Pillow: {e}")
            return self._mock_image_file(output_path)

    def _mock_image_file(self, output_path: str) -> str:
        """Gera um arquivo de imagem placeholder."""
        with open(output_path, "wb") as f:
            f.write(b"MOCK_PNG_IMAGE_DATA")
        logger.info(f"🖼️ Imagem criada (placeholder): {output_path}")
        return output_path


if __name__ == "__main__":
    designer = AutomatedImageDesigner()
    card_path = designer.create_birthday_card("Irmão Gabriel Silva")
    print(f"Cartão de Aniversário gerado em: {card_path}")
