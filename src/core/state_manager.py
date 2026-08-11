"""
Gestor de Estado & Deduplicação (estado_videos.json).

Garante a idempotência do sistema, prevenindo re-transcrições ou re-renderizações
desnecessárias e gerenciando as 3 filas dinâmicas de prioridade:
1. Mais Recentes (últimas 48h)
2. Mais Vistos (com deduplicação em <1s via cópia de MP4 existente)
3. Acervo Histórico (1º ao 440º vídeo)
"""

import os
import json
import shutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import OUTPUT_BASE_DIR, SUBFOLDERS, get_folder_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class StateManager:
    """
    Gerenciador centralizado de estado idempotente do ecossistema IBPM CR.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa o gerenciador de estado.

        :param db_path: Caminho customizado para o estado_videos.json, se houver.
        """
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = os.path.join(OUTPUT_BASE_DIR, SUBFOLDERS["STATE"])

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """
        Carrega o estado a partir do arquivo JSON no Google Drive ou local.
        """
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao ler {self.db_path}: {e}. Criando novo estado.")
                return self._default_state()
        return self._default_state()

    def _default_state(self) -> Dict[str, Any]:
        """
        Estrutura padrão do estado inicial.
        """
        return {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "channel_handle": "@ibpmcr7976",
            "videos": {},  # video_id -> metadata & status dict
            "queues": {
                "recent_48h": [],
                "most_viewed": [],
                "historical": []
            }
        }

    def save_state(self) -> None:
        """
        Persiste o estado atualizado no arquivo JSON.
        """
        try:
            self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            logger.info("💾 estado_videos.json atualizado com sucesso.")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estado_videos.json: {e}")

    def register_video(self, video_id: str, title: str, published_at: str, view_count: int, duration_sec: int = 0) -> Dict[str, Any]:
        """
        Registra ou atualiza metadados de um vídeo no estado.

        :param video_id: ID do vídeo no YouTube.
        :param title: Título da transmissão/vídeo.
        :param published_at: Data de publicação no formato ISO format.
        :param view_count: Contagem atual de visualizações.
        :param duration_sec: Duração em segundos.
        :return: Registro do vídeo no dicionário de estado.
        """
        if video_id not in self.state["videos"]:
            self.state["videos"][video_id] = {
                "video_id": video_id,
                "title": title,
                "published_at": published_at,
                "view_count": view_count,
                "duration_sec": duration_sec,
                "transcribed": False,
                "transcription_path": None,
                "edited_short_9_16": False,
                "short_video_path": None,
                "edited_medium_16_9": False,
                "medium_video_path": None,
                "theme_category": None,
                "praise_mapped": False,
                "rag_indexed": False,
                "processed_queues": []
            }
        else:
            # Atualiza visualizações e metadados sem sobrescrever status de IA
            self.state["videos"][video_id]["view_count"] = view_count
            self.state["videos"][video_id]["title"] = title

        self.save_state()
        return self.state["videos"][video_id]

    def update_queues(self, recent_ids: List[str], most_viewed_ids: List[str], historical_ids: List[str]) -> None:
        """
        Atualiza as 3 filas de prioridade dinâmica.

        :param recent_ids: IDs dos vídeos das últimas 48h.
        :param most_viewed_ids: IDs dos vídeos mais vistos ordenados por viewCount.
        :param historical_ids: IDs de todo o acervo ordenados do 1º ao 440º.
        """
        self.state["queues"]["recent_48h"] = recent_ids
        self.state["queues"]["most_viewed"] = most_viewed_ids
        self.state["queues"]["historical"] = historical_ids
        self.save_state()
        logger.info(f"Filas atualizadas -> Recentes: {len(recent_ids)}, Mais Vistos: {len(most_viewed_ids)}, Histórico: {len(historical_ids)}")

    def is_already_processed(self, video_id: str, task: str) -> bool:
        """
        Verifica se determinada tarefa (transcribed, edited_short_9_16, edited_medium_16_9, rag_indexed)
        já foi concluída para o vídeo especificado.

        :param video_id: ID do vídeo.
        :param task: Nome da flag de tarefa.
        :return: Bool indicando se a tarefa já foi realizada.
        """
        video_data = self.state["videos"].get(video_id)
        if not video_data:
            return False
        return video_data.get(task, False)

    def mark_task_complete(self, video_id: str, task: str, file_path: Optional[str] = None, extra_meta: Optional[Dict[str, Any]] = None) -> None:
        """
        Marca uma tarefa como concluída para o vídeo no banco de estado.

        :param video_id: ID do vídeo.
        :param task: Nome da flag da tarefa (ex: 'transcribed').
        :param file_path: Caminho do arquivo gerado.
        :param extra_meta: Dicionário complementar de metadados.
        """
        if video_id in self.state["videos"]:
            self.state["videos"][video_id][task] = True
            if file_path:
                path_key = f"{task}_path" if not task.endswith("_path") else task
                self.state["videos"][video_id][path_key] = file_path
            if extra_meta:
                self.state["videos"][video_id].update(extra_meta)
            self.save_state()

    def check_and_deduplicate(self, video_id: str, destination_folder: str, file_prefix: str = "short") -> Optional[str]:
        """
        Deduplicação rápida (<1s): Se o vídeo já foi renderizado em outra fila,
        efetua apenas a cópia do arquivo .mp4 já existente para a nova pasta de destino.

        :param video_id: ID do vídeo.
        :param destination_folder: Caminho da pasta de destino.
        :param file_prefix: Prefixo do arquivo ('short' ou 'medium').
        :return: Caminho do arquivo copiado ou None se não existir edição prévia.
        """
        video_data = self.state["videos"].get(video_id)
        if not video_data:
            return None

        existing_path = None
        if file_prefix == "short" and video_data.get("edited_short_9_16"):
            existing_path = video_data.get("short_video_path")
        elif file_prefix == "medium" and video_data.get("edited_medium_16_9"):
            existing_path = video_data.get("medium_video_path")

        if existing_path and os.path.exists(existing_path):
            os.makedirs(destination_folder, exist_ok=True)
            target_path = os.path.join(destination_folder, os.path.basename(existing_path))
            if existing_path != target_path:
                logger.info(f"⚡ Deduplicação rápida (<1s): Copiando {existing_path} para {target_path}")
                shutil.copy2(existing_path, target_path)
            return target_path

        return None

    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna um resumo estatístico do estado do sistema.
        """
        total_registered = len(self.state["videos"])
        transcribed = sum(1 for v in self.state["videos"].values() if v.get("transcribed"))
        edited_shorts = sum(1 for v in self.state["videos"].values() if v.get("edited_short_9_16"))
        edited_mediums = sum(1 for v in self.state["videos"].values() if v.get("edited_medium_16_9"))

        return {
            "total_registered": total_registered,
            "transcribed_count": transcribed,
            "edited_shorts_count": edited_shorts,
            "edited_mediums_count": edited_mediums,
            "queue_sizes": {
                "recent_48h": len(self.state["queues"]["recent_48h"]),
                "most_viewed": len(self.state["queues"]["most_viewed"]),
                "historical": len(self.state["queues"]["historical"])
            }
        }


if __name__ == "__main__":
    sm = StateManager()
    print("Estado inicial carregado com sucesso:")
    print(sm.get_summary())
