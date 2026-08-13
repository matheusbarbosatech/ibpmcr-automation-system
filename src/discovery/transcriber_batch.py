"""
Módulo de Transcrição Sequencial de Alta Fidelidade (Etapa 2 - IBPM CR).

Executa a transcrição integral palavra por palavra via Faster-Whisper
no modelo de alta precisão (Large-v3 / Medium) com beam_size=5 e word_timestamps.

Requisitos Atendidos:
1. Gera e salva arquivos .txt e .json na MESMA PASTA do áudio (data/audio_podcasts/ ou Drive).
2. Sincroniza e grava a transcrição completa e os segmentos no SQLite local.
3. Transcrição Integral e Fiel (Strict Grounding Teológico).
4. Idempotência e Resiliência.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from tqdm import tqdm

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config.settings import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, AUDIO_DIR
from src.core.state_manager import MasterPlanManager

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TranscriberBatch")


class BatchTranscriber:
    """
    Transcritor de alta precisão que gera .txt, .json e atualiza o SQLite.
    """

    def __init__(self, model_size: str = "large-v3"):
        self.model_size = model_size
        self.device = WHISPER_DEVICE
        self.compute_type = WHISPER_COMPUTE_TYPE
        self.model = None
        self.state_mgr = MasterPlanManager()

        if HAS_FASTER_WHISPER:
            try:
                logger.info(f"⚡ Inicializando Faster-Whisper (Modelo: '{self.model_size}' | Device: '{self.device}' | Compute: '{self.compute_type}')...")
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                logger.info(f"✅ Faster-Whisper '{self.model_size}' de alta acurácia carregado com sucesso.")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar Faster-Whisper ({self.model_size}): {e}. Tentando modelo fallback 'medium'...")
                try:
                    self.model_size = "medium"
                    self.model = WhisperModel("medium", device=self.device, compute_type=self.compute_type)
                    logger.info("✅ Faster-Whisper 'medium' carregado com sucesso.")
                except Exception as ex:
                    logger.warning(f"⚠️ Erro ao carregar modelo fallback: {ex}")

    def process_pending_queue(self, max_items: int = 10, force: bool = False) -> int:
        all_videos = self.state_mgr.get_all_videos_chronological()
        
        processed = 0
        skipped = 0

        pending_list = []
        for v in all_videos:
            v_id = v["video_id"]
            
            audio_path = self._find_audio_file_on_disk(v_id)
            if not audio_path:
                continue

            base_path = os.path.splitext(audio_path)[0]
            txt_path = base_path + ".txt"
            json_path = base_path + ".json"

            already_done = (
                not force and
                self.state_mgr.is_transcribed(v_id) and
                os.path.exists(txt_path) and os.path.getsize(txt_path) > 100
            )

            if already_done:
                skipped += 1
            else:
                v["audio_path_real"] = audio_path
                v["txt_path_target"] = txt_path
                v["json_path_target"] = json_path
                pending_list.append(v)

        logger.info(f"📋 Fila de Transcrição Integral: {len(pending_list)} cultos pendentes (Ignorados já concluídos: {skipped}).")

        if not pending_list:
            logger.info("🎉 Todos os cultos da fila já possuem transcrição integral pronta!")
            return 0

        items_to_process = pending_list[:max_items]
        pbar = tqdm(items_to_process, desc="Transcrevendo Cultos (Alta Precisão)", unit="áudio")

        for item in pbar:
            v_id = item["video_id"]
            idx = item.get("indice_sequencial", 1)
            date_str = str(item.get("data_publicacao", ""))[:10]
            title = item.get("titulo_sanitizado", "culto")
            audio_path = item["audio_path_real"]

            display_name = f"[{idx:03d}/{len(all_videos):03d}] {idx:03d}_{date_str}_{v_id}_{title[:25]}"
            pbar.set_postfix_str(display_name)

            try:
                res = self.transcribe_single_audio(audio_path, video_id=v_id, item_meta=item)
                if res and res.get("texto_completo"):
                    processed += 1
            except Exception as e:
                logger.warning(f"⚠️ Erro ao transcrever culto {v_id}: {e}")

        return processed

    def transcribe_single_audio(self, audio_path: str, video_id: str, item_meta: Dict[str, Any]) -> Dict[str, Any]:
        base_path = os.path.splitext(audio_path)[0]
        txt_path = base_path + ".txt"
        json_path = base_path + ".json"

        if self.model and os.path.exists(audio_path) and os.path.getsize(audio_path) > 10000:
            size_mb = round(os.path.getsize(audio_path) / (1024 * 1024), 1)
            file_name = os.path.basename(audio_path)
            logger.info(f"\n🎙️ Transcrevendo com Alta Precisão ({self.model_size}): {file_name} ({size_mb} MB)...")

            segments, info = self.model.transcribe(
                audio_path,
                language="pt",
                beam_size=5,
                vad_filter=True,
                word_timestamps=True
            )

            segments_data = []
            full_text_parts = []

            for seg in segments:
                item = {
                    "segment_id": seg.id,
                    "start_sec": round(seg.start, 2),
                    "end_sec": round(seg.end, 2),
                    "text": seg.text.strip()
                }
                segments_data.append(item)
                full_text_parts.append(seg.text.strip())

            full_text = " ".join(full_text_parts)
            segments_json_str = json.dumps(segments_data, ensure_ascii=False, indent=2)

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            logger.info(f"📄 Transcrição integral .txt salva: {txt_path}")

            with open(json_path, "w", encoding="utf-8") as f:
                f.write(segments_json_str)
            logger.info(f"📊 Segmentos detalhados .json salvos: {json_path}")

            self.state_mgr.save_transcription_result(
                video_id=video_id,
                full_text=full_text,
                segments_json=segments_json_str,
                tipo_transcricao=f"whisper_{self.model_size}_full_accuracy"
            )
            logger.info(f"💾 Transcrição sincronizada no SQLite para o vídeo {video_id}.")

            return {
                "language": info.language,
                "duration_sec": round(info.duration, 2),
                "texto_completo": full_text,
                "segmentos_timestamps": segments_data,
                "txt_path": txt_path,
                "json_path": json_path
            }

        else:
            logger.warning(f"⚠️ Áudio não encontrado ou inválido: {audio_path}")
            return {}

    def _find_audio_file_on_disk(self, video_id: str) -> Optional[str]:
        if not os.path.exists(AUDIO_DIR):
            return None

        for fname in os.listdir(AUDIO_DIR):
            if video_id in fname and not fname.endswith(".txt") and not fname.endswith(".json") and not fname.endswith(".part") and not fname.endswith(".ytdl"):
                full_p = os.path.join(AUDIO_DIR, fname)
                if os.path.getsize(full_p) > 10000:
                    return full_p
        return None


if __name__ == "__main__":
    bt = BatchTranscriber()
    print("TranscriberBatch inicializado no modelo de alta acurácia!")
