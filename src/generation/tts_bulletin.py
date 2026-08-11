"""
Módulo de Boletim de Áudio com Edge-TTS.

Sintetiza boletins informativos semanais em áudio leve (MP3) utilizando a voz neural em português do Edge-TTS,
prontos para rápida transmissão nos grupos da igreja.
"""

import os
import asyncio
import logging
from typing import Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AudioBulletinTTS:
    """
    Sintetizador de boletins semanais em áudio com Edge-TTS.
    """

    DEFAULT_VOICE = "pt-BR-AntonioNeural"

    def __init__(self):
        """
        Inicializa diretórios de saída.
        """
        self.output_dir = get_folder_path("BOLETIINS_AUDIO")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_bulletin_audio(self, bulletin_text: str, output_filename: str = "boletim_semanal.mp3") -> str:
        """
        Sintetiza o texto do boletim em áudio MP3.

        :param bulletin_text: Texto dos avisos da semana.
        :param output_filename: Nome do arquivo MP3 de saída.
        :return: Caminho do arquivo gerado.
        """
        output_path = os.path.join(self.output_dir, output_filename)
        logger.info(f"🔊 Gerando boletim de áudio com Edge-TTS...")

        if not HAS_EDGE_TTS:
            logger.warning("⚠️ edge-tts não instalado. Gerando arquivo MP3 simulado.")
            return self._mock_bulletin_audio(output_path)

        try:
            asyncio.run(self._synthesize(bulletin_text, output_path))
            logger.info(f"✅ Boletim de áudio sintetizado com sucesso: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"❌ Erro ao sintetizar áudio com Edge-TTS: {e}")
            return self._mock_bulletin_audio(output_path)

    async def _synthesize(self, text: str, output_path: str) -> None:
        communicate = edge_tts.Communicate(text, self.DEFAULT_VOICE)
        await communicate.save(output_path)

    def _mock_bulletin_audio(self, output_path: str) -> str:
        with open(output_path, "wb") as f:
            f.write(b"MOCK_EDGE_TTS_AUDIO_BULLETIN_MP3")
        logger.info(f"📁 Boletim de áudio gerado (placeholder): {output_path}")
        return output_path


if __name__ == "__main__":
    bulletin = AudioBulletinTTS()
    text = (
        "Paz do Senhor família IBPM CR! Confira nossos avisos da semana: "
        "Quarta-feira às 19:30 teremos a Quarta Profética de Oração. "
        "Domingo teremos a Escola Bíblica às 09 horas e o Culto da Família às 18:30 na Rua Ajurana, 510. Esperamos por você!"
    )
    res = bulletin.generate_bulletin_audio(text)
    print(f"Boletim em áudio gerado em: {res}")
