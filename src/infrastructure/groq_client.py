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


from dotenv import load_dotenv
load_dotenv(override=True)

class GroqWhisperClient:
    """
    Cliente para transcrição de alta velocidade via Groq Whisper API (Whisper Large V3).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
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
            "-threads", "1",
            "-i", str(input_audio),
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "16k",
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

    def analyze_transcript_with_groq(
        self,
        transcript_text: str,
        source_video_id: str = "IBPM_CULTO",
        job_id: str = "job_groq_llama_mining"
    ) -> Dict[str, Any]:
        """
        Executa a mineração teológica (Fase 2 Mineração) via Groq API usando Llama 3.3 70B com 14.400 req/dia.
        Retorna o dicionário serializável do SermonMiningResponse.
        """
        if not self.client:
            raise ValueError("GROQ_API_KEY necessária para mineração via Llama 3.3.")

        from src.infrastructure.gemini_client import SYSTEM_PROMPT_PENTECOSTAL

        MAX_CHARS = 32000
        if len(transcript_text) > MAX_CHARS:
            transcript_text = transcript_text[:MAX_CHARS]

        prompt_user = f"ID do Vídeo: {source_video_id}\n\nTRANSCRIÇÃO DO CULTO:\n{transcript_text}"

        logger.info("🧠 Disparando Mineração Teológica no Groq (Llama 3.3 70B)", job_id=job_id, text_len=len(transcript_text))

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_PENTECOSTAL},
                    {"role": "user", "content": prompt_user}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            res_text = response.choices[0].message.content
            if not res_text:
                raise RuntimeError("Resposta vazia da API do Groq Llama.")

            data = json.loads(res_text)

            # Normalização de Chaves (Short-Form vs Mid-Form)
            short_cuts = data.get("short_form_cuts", [])
            mid_cuts = data.get("mid_form_cuts", [])

            if not short_cuts and not mid_cuts and "cortes" in data:
                for c in data["cortes"]:
                    fmt = str(c.get("formato", "")).lower()
                    cut_obj = {
                        "cut_id": f"short_{len(short_cuts)+1:03d}" if "short" in fmt else f"mid_{len(mid_cuts)+1:03d}",
                        "title_hook_a": c.get("titulo", c.get("title_hook_a", "Corte Minerado")),
                        "title_hook_b": c.get("subtitulo", c.get("title_hook_b", "Mensagem de Impacto")),
                        "start_anchor_7_words": c.get("start_anchor_7_words", ""),
                        "end_anchor_7_words": c.get("end_anchor_7_words", ""),
                        "category": c.get("categoria", "Exegese"),
                        "emotional_tone": c.get("tom", "Inspirador")
                    }
                    if "short" in fmt:
                        short_cuts.append(cut_obj)
                    else:
                        mid_cuts.append(cut_obj)

            formatted_payload = {
                "job_id": job_id,
                "source_video_id": source_video_id,
                "sermon_title": data.get("sermon_title", f"Culto IBPM CR {source_video_id}"),
                "preacher_name": data.get("preacher_name", "Pastor IBPM CR"),
                "short_form_cuts": short_cuts,
                "mid_form_cuts": mid_cuts
            }

            return formatted_payload

        except Exception as e:
            logger.error("Falha na mineração teológica Groq Llama 3.3", job_id=job_id, error=str(e))
            raise RuntimeError(f"Erro na API do Groq Llama 3.3: {str(e)}")

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
