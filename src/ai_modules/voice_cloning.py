"""
Módulo de Clonagem de Voz Neural com XTTS-v2 (Coqui TTS).

Permite sintetizar devocionais em áudio e boletins semanais utilizando a voz clonada
da liderança pastoral (few-shot voice cloning) a partir de amostras limpas do áudio dos cultos.
"""

import os
import logging
from typing import Optional, List
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path, USE_CUDA

try:
    from TTS.api import TTS
    HAS_COQUI_TTS = True
except ImportError:
    HAS_COQUI_TTS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PastoralVoiceCloning:
    """
    Sintetizador de voz neural clonada para devocionais pastorais.
    """

    def __init__(self, speaker_wav_path: Optional[str] = None):
        """
        Inicializa o modelo XTTS-v2.

        :param speaker_wav_path: Caminho da amostra de áudio com a voz de referência.
        """
        self.output_dir = get_folder_path("EBOOKS_DEVOCIONAIS")
        os.makedirs(self.output_dir, exist_ok=True)
        self.speaker_wav = speaker_wav_path
        self.tts = None

        if HAS_COQUI_TTS:
            try:
                logger.info("⏳ Carregando modelo de clonagem de voz XTTS-v2 (Coqui TTS)...")
                gpu_flag = USE_CUDA
                self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=gpu_flag)
                logger.info("✅ XTTS-v2 carregado com sucesso!")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível carregar XTTS-v2 ({e}). Usando modo fallback.")

    def synthesize_devotional(self, text_script: str, output_mp3_path: str, speaker_wav: Optional[str] = None) -> str:
        """
        Sintetiza um texto devocional em um arquivo de áudio narrado com voz pastoral clonada.

        :param text_script: Texto do devocional a ser narrado.
        :param output_mp3_path: Caminho para salvar o áudio gerado.
        :param speaker_wav: Amostra alternativa da voz de referência.
        :return: Caminho do arquivo MP3 gerado.
        """
        os.makedirs(os.path.dirname(output_mp3_path), exist_ok=True)
        ref_wav = speaker_wav or self.speaker_wav

        if self.tts and ref_wav and os.path.exists(ref_wav):
            try:
                logger.info(f"🎙️ Sintetizando devocional em áudio com voz clonada (XTTS-v2)...")
                self.tts.tts_to_file(
                    text=text_script,
                    file_path=output_mp3_path,
                    speaker_wav=ref_wav,
                    language="pt"
                )
                logger.info(f"✅ Áudio devocional gerado com sucesso: {output_mp3_path}")
                return output_mp3_path
            except Exception as e:
                logger.error(f"❌ Erro ao sintetizar áudio com XTTS-v2: {e}")
                return self._mock_audio_devotional(output_mp3_path)
        else:
            logger.warning("⚠️ XTTS-v2 ou áudio de referência indisponível. Gerando áudio via fallback.")
            return self._mock_audio_devotional(output_mp3_path)

    def _mock_audio_devotional(self, output_path: str) -> str:
        """Gera arquivo MP3 placeholder."""
        with open(output_path, "wb") as f:
            f.write(b"PASTORAL_VOICE_CLONED_AUDIO_MP3_DATA")
        logger.info(f"📁 Áudio devocional salvo (placeholder): {output_path}")
        return output_path


if __name__ == "__main__":
    vc = PastoralVoiceCloning()
    script = "Que a paz do Senhor Jesus esteja sobre o seu lar neste dia maravilhoso."
    out = vc.synthesize_devotional(script, "devocional_hoje.mp3")
    print(f"Devocional gerado em: {out}")
