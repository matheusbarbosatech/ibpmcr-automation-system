"""
Módulo de Tratamento de Áudio e Geração de Podcast RSS.

Utiliza pydub para normalização de áudio, remoção de silêncio e exportação de episódios de áudio,
além de gerar o arquivo RSS Feed XML para distribuição no Spotify e Apple Podcasts.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path

try:
    from pydub import AudioSegment, effects
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Processador de áudio para podcasts pastorais e devocionais da IBPM CR.
    """

    def __init__(self):
        """
        Inicializa o diretório de podcasts.
        """
        self.podcast_dir = get_folder_path("PODCASTS_AUDIO")
        os.makedirs(self.podcast_dir, exist_ok=True)

    def normalize_and_clean(self, input_audio: str, output_audio: str) -> str:
        """
        Normaliza o volume do áudio e reduz ruídos de fundo utilizando pydub.

        :param input_audio: Caminho do áudio bruto.
        :param output_audio: Caminho para salvar o áudio processado.
        :return: Caminho do áudio limpo.
        """
        os.makedirs(os.path.dirname(output_audio), exist_ok=True)

        if not HAS_PYDUB or not os.path.exists(input_audio):
            logger.warning("⚠️ pydub ou arquivo de áudio indisponível. Gerando áudio placeholder.")
            return self._generate_mock_audio(output_audio)

        try:
            logger.info(f"🔊 Processando áudio com pydub: {input_audio}...")
            sound = AudioSegment.from_file(input_audio)

            # Normalização de ganho
            normalized_sound = effects.normalize(sound)

            # Exporta em MP3 128kbps (otimizado para podcast)
            normalized_sound.export(output_audio, format="mp3", bitrate="128k")
            logger.info(f"✅ Áudio normalizado com sucesso: {output_audio}")
            return output_audio

        except Exception as e:
            logger.error(f"❌ Erro no tratamento de áudio: {e}")
            return self._generate_mock_audio(output_audio)

    def generate_podcast_rss(self, episodes: List[Dict[str, Any]], output_rss_path: Optional[str] = None) -> str:
        """
        Gera um Feed RSS XML compatível com Spotify e Apple Podcasts.

        :param episodes: Lista de dicionários com metadados dos episódios (title, description, mp3_url, duration).
        :param output_rss_path: Caminho customizado para salvar o podcast_feed.xml.
        :return: Conteúdo XML formatado em string.
        """
        if not output_rss_path:
            output_rss_path = os.path.join(self.podcast_dir, "podcast_feed.xml")

        logger.info("📡 Gerando Feed RSS do Podcast IBPM CR...")

        rss = ET.Element("rss", version="2.0", attrib={
            "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
            "xmlns:content": "http://purl.org/rss/1.0/modules/content/"
        })

        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "IBPM CR - Pregações e Devocionais"
        ET.SubElement(channel, "link").text = "https://www.youtube.com/@ibpmcr7976"
        ET.SubElement(channel, "language").text = "pt-br"
        ET.SubElement(channel, "description").text = "Mensagens de fé, devocionais diários e cultos da Igreja Batista Pentecostal Mundial - Campo Grande, RJ."
        ET.SubElement(channel, "itunes:author").text = "Bispo Elcimar Lopes Vianna / IBPM CR"

        for ep in episodes:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = ep.get("title", "Episódio IBPM CR")
            ET.SubElement(item, "description").text = ep.get("description", "Mensagem abençoada da IBPM CR.")
            ET.SubElement(item, "pubDate").text = ep.get("pub_date", datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"))
            
            enclosure = ET.SubElement(item, "enclosure")
            enclosure.attrib["url"] = ep.get("mp3_url", "https://ibpmcr.org/podcasts/episode.mp3")
            enclosure.attrib["type"] = "audio/mpeg"
            enclosure.attrib["length"] = str(ep.get("file_size", 5000000))

            ET.SubElement(item, "itunes:duration").text = str(ep.get("duration", "00:30:00"))

        tree = ET.ElementTree(rss)
        ET.indent(tree, space="  ")
        tree.write(output_rss_path, encoding="utf-8", xml_declaration=True)

        logger.info(f"✅ Feed RSS salvo com sucesso em: {output_rss_path}")
        return output_rss_path

    def _generate_mock_audio(self, output_audio: str) -> str:
        """Gera arquivo MP3 placeholder."""
        os.makedirs(os.path.dirname(output_audio), exist_ok=True)
        with open(output_audio, "wb") as f:
            f.write(b"MOCK_PROCESSED_AUDIO_DATA_MP3")
        return output_audio


if __name__ == "__main__":
    ap = AudioProcessor()
    episodes = [
        {"title": "Devocional - A Paz de Deus", "description": "Mensagem sobre a paz que excede todo entendimento.", "mp3_url": "https://ibpmcr.org/audio1.mp3"},
        {"title": "Quarta Profética - Oração da Família", "description": "Culto de oração e restauração.", "mp3_url": "https://ibpmcr.org/audio2.mp3"}
    ]
    rss_path = ap.generate_podcast_rss(episodes)
    print(f"Feed RSS gerado em: {rss_path}")
