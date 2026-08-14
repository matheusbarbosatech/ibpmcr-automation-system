"""
Cliente de Transcrição Groq Whisper (Fase 2) - IBPM CR Automation System.

Compacta áudios brutos de cultos usando FFmpeg (mono, 16kHz, baixo bitrate) para gerar
arquivos levíssimos (~8MB - 14MB), contornando o limite de 25MB da cota gratuita da Groq API.
Retorna texto corrido (.txt) e timestamps de palavras (.words.json) em segundos.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from groq import Groq
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("GroqWhisperClient")


class GroqWhisperClient:
    """
    Cliente para transcrição de alta velocidade via Groq Whisper API (Whisper Large V3).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key or len(self.api_key.strip()) < 10:
            logger.warning("GROQ_API_KEY não encontrada no ambiente. Algumas rotas podem falhar.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key.strip())
            logger.info("Cliente GroqWhisperClient inicializado com sucesso.")

    def compress_audio_for_groq(self, input_audio: Path, output_audio: Path) -> Path:
        """
        Compacta o áudio original de 250MB para ~10MB (Mono, 16kHz, 32k bitrate) usando FFmpeg.
        Garante que o arquivo entre com folga na cota de 25MB da Groq.
        """
        output_audio.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = settings.FFMPEG_BINARY_PATH or "ffmpeg"

        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_audio),
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "32k",
            str(output_audio)
        ]

        logger.info(
            "🗜️ Compactando áudio para limite da Groq (16kHz mono)",
            input=input_audio.name,
            output=output_audio.name
        )

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            new_size_mb = round(output_audio.stat().st_size / (1024 * 1024), 2)
            logger.info("✅ Compactação concluída com sucesso", new_size_mb=new_size_mb)
            return output_audio
        except subprocess.CalledProcessError as e:
            logger.error("Falha na compactação do áudio via FFmpeg", error=e.stderr)
            raise RuntimeError(f"Erro no FFmpeg: {e.stderr}")

    def transcribe_audio(
        self,
        audio_file_path: Path,
        job_id: str = "job_groq_transcribe"
    ) -> Dict[str, Any]:
        """
        Transcreve o áudio compactado usando a API do Groq (Whisper Large V3 Turbo).
        Retorna o texto corrido e os timestamps de cada palavra.
        """
        if not self.client:
            raise ValueError("GROQ_API_KEY não foi configurada no arquivo .env.")

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_file_path}")

        # Se o áudio for maior que 20MB, compacta primeiro
        target_audio = audio_file_path
        if audio_file_path.stat().st_size > (20 * 1024 * 1024):
            cache_compressed = Path("data/cache") / f"compressed_{audio_file_path.stem}.mp3"
            target_audio = self.compress_audio_for_groq(audio_file_path, cache_compressed)

        logger.info(
            "⚡ Enviando áudio leve para a Groq Whisper API (Whisper Large V3)",
            job_id=job_id,
            file=target_audio.name,
            size_mb=round(target_audio.stat().st_size / (1024 * 1024), 2)
        )

        with open(target_audio, "rb") as file_obj:
            transcription = self.client.audio.transcriptions.create(
                file=(target_audio.name, file_obj.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                language="pt",
                temperature=0.0
            )

        full_text = transcription.text if hasattr(transcription, "text") else str(transcription)
        raw_dict = transcription.model_dump() if hasattr(transcription, "model_dump") else {}

        # Salva em arquivos locais da Fase 2
        trans_dir = Path("data/audio_podcasts/transcricoes_fase2")
        trans_dir.mkdir(parents=True, exist_ok=True)

        txt_file = trans_dir / f"{audio_file_path.stem}.txt"
        words_file = trans_dir / f"{audio_file_path.stem}.words.json"

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(full_text)

        words_data = raw_dict.get("words", raw_dict.get("segments", []))
        with open(words_file, "w", encoding="utf-8") as f:
            json.dump(words_data, f, ensure_ascii=False, indent=2)

        logger.info(
            "🎉 Transcrição Fase 2 concluída via Groq Whisper!",
            job_id=job_id,
            txt_saved=txt_file.name,
            words_count=len(words_data)
        )

        return {
            "status": "success",
            "text": full_text,
            "txt_path": str(txt_file),
            "words_path": str(words_file),
            "words_count": len(words_data)
        }
