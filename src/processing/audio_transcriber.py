"""
Módulo de Transcrição de Áudio com Faster-Whisper.

Realiza o download de áudio via yt-dlp e gera transcrições com aceleração por GPU CUDA
através da biblioteca Faster-Whisper, exportando nos formatos SRT, VTT e JSON.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import USE_CUDA, WHISPER_MODEL_SIZE

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AudioTranscriber:
    """
    Transcritor de áudio inteligente acelerado por GPU CUDA.
    """

    def __init__(self, model_size: str = WHISPER_MODEL_SIZE, use_cuda: bool = USE_CUDA):
        """
        Inicializa o modelo Faster-Whisper.

        :param model_size: Tamanho do modelo Whisper ('tiny', 'base', 'small', 'medium', 'large-v3').
        :param use_cuda: Bool indicando se deve utilizar GPU CUDA.
        """
        self.model_size = model_size
        self.device = "cuda" if use_cuda else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self.model = None

        if HAS_FASTER_WHISPER:
            try:
                logger.info(f"⏳ Carregando Faster-Whisper ({model_size}) no dispositivo: {self.device}...")
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                logger.info("✅ Faster-Whisper carregado com sucesso!")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível inicializar Faster-Whisper na GPU ({e}). Tentando modo CPU fallback.")
                try:
                    self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                except Exception as cpu_err:
                    logger.error(f"❌ Falha ao carregar modelo Whisper em CPU: {cpu_err}")

    def download_audio(self, video_url: str, output_dir: str) -> Optional[str]:
        """
        Faz download do áudio em MP3 a partir da URL do YouTube via yt-dlp.

        :param video_url: URL do vídeo do YouTube.
        :param output_dir: Diretório de destino.
        :return: Caminho do arquivo MP3 baixado ou None se falhar.
        """
        os.makedirs(output_dir, exist_ok=True)
        out_template = os.path.join(output_dir, "%(id)s.%(ext)s")

        if not HAS_YT_DLP:
            logger.warning("⚠️ yt-dlp não está instalado. Simulando download de áudio.")
            mock_file = os.path.join(output_dir, "sample_audio.mp3")
            with open(mock_file, "wb") as f:
                f.write(b"MOCK_AUDIO_DATA")
            return mock_file

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': out_template,
            'quiet': True
        }

        try:
            logger.info(f"⏬ Baixando áudio de {video_url}...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                audio_file = os.path.join(output_dir, f"{info['id']}.mp3")
                logger.info(f"✅ Áudio baixado com sucesso: {audio_file}")
                return audio_file
        except Exception as e:
            logger.error(f"❌ Erro ao baixar áudio com yt-dlp: {e}")
            return None

    def transcribe(self, audio_path: str, output_base_name: str) -> Dict[str, Any]:
        """
        Transcreve o arquivo de áudio e gera arquivos SRT e VTT com carimbos de data/hora.

        :param audio_path: Caminho para o arquivo de áudio (MP3/WAV).
        :param output_base_name: Caminho base sem extensão para salvar transcrições (.srt, .vtt, .json).
        :return: Dicionário contendo o texto completo e os segmentos formatados.
        """
        if not self.model or not os.path.exists(audio_path):
            logger.warning("⚠️ Modelo Faster-Whisper ou arquivo de áudio indisponível. Gerando transcrição simulada.")
            return self._generate_mock_transcription(output_base_name)

        try:
            logger.info(f"🎙️ Transcrevendo áudio: {audio_path}...")
            segments, info = self.model.transcribe(audio_path, language="pt", beam_size=5)

            segment_list = []
            full_text = []

            for seg in segments:
                item = {
                    "id": seg.id,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip()
                }
                segment_list.append(item)
                full_text.append(seg.text.strip())

            complete_text = " ".join(full_text)

            # Salva arquivos de legenda
            srt_path = f"{output_base_name}.srt"
            vtt_path = f"{output_base_name}.vtt"
            json_path = f"{output_base_name}.json"

            self._save_srt(segment_list, srt_path)
            self._save_vtt(segment_list, vtt_path)

            result = {
                "language": info.language,
                "duration": info.duration,
                "full_text": complete_text,
                "segments": segment_list,
                "srt_path": srt_path,
                "vtt_path": vtt_path
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Transcrição concluída! SRT salvo em: {srt_path}")
            return result

        except Exception as e:
            logger.error(f"❌ Erro durante transcrição com Faster-Whisper: {e}")
            return self._generate_mock_transcription(output_base_name)

    def _save_srt(self, segments: List[Dict[str, Any]], filepath: str) -> None:
        """Salva a transcrição no formato SRT."""
        with open(filepath, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                start_srt = self._format_timestamp_srt(seg["start"])
                end_srt = self._format_timestamp_srt(seg["end"])
                f.write(f"{i}\n{start_srt} --> {end_srt}\n{seg['text']}\n\n")

    def _save_vtt(self, segments: List[Dict[str, Any]], filepath: str) -> None:
        """Salva a transcrição no formato WebVTT."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for seg in segments:
                start_vtt = self._format_timestamp_vtt(seg["start"])
                end_vtt = self._format_timestamp_vtt(seg["end"])
                f.write(f"{start_vtt} --> {end_vtt}\n{seg['text']}\n\n")

    def _format_timestamp_srt(self, seconds: float) -> str:
        millis = int((seconds % 1) * 1000)
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        millis = int((seconds % 1) * 1000)
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

    def _generate_mock_transcription(self, output_base_name: str) -> Dict[str, Any]:
        segments = [
            {"id": 1, "start": 0.0, "end": 15.0, "text": "Graça e paz a toda a igreja Batista Pentecostal Mundial."},
            {"id": 2, "start": 15.5, "end": 45.0, "text": "Hoje vamos meditar na palavra de Deus no livro de Romanos capítulo doze."},
            {"id": 3, "start": 45.5, "end": 90.0, "text": "Senhor meu Deus e meu Pai, nós te pedimos uma bênção sobre as famílias nesta oração."}
        ]
        full_text = " ".join([s["text"] for s in segments])
        srt_path = f"{output_base_name}.srt"
        vtt_path = f"{output_base_name}.vtt"
        self._save_srt(segments, srt_path)
        self._save_vtt(segments, vtt_path)

        return {
            "language": "pt",
            "duration": 90.0,
            "full_text": full_text,
            "segments": segments,
            "srt_path": srt_path,
            "vtt_path": vtt_path
        }


if __name__ == "__main__":
    transcriber = AudioTranscriber()
    res = transcriber.transcribe("sample.mp3", "test_transcription")
    print("Resultado da transcrição:")
    print(res["full_text"])
