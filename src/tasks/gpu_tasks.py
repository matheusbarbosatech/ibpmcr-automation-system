"""
Tarefas do Celery para Fila de GPU (gpu_queue) - IBPM CR Automation System.

Executa tarefas pesadas de inferência de IA (Whisper, Gemini LLM Content Mining),
aplicando a política anti-OOM, alocação exclusiva na gpu_queue e retentativa com Exponential Backoff e Jitter.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from src.tasks.celery_app import celery_app
from src.core.logger import get_logger
from src.discovery.content_miner_llm import ContentMinerLLM
from src.core.state_manager import MasterPlanManager

logger = get_logger("GpuTasks")


@celery_app.task(
    bind=True,
    name="src.tasks.gpu_tasks.task_mine_sermon_content",
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_jitter=True,
    max_retries=3,
    acks_late=True
)
def task_mine_sermon_content(self, transcript_json_path: str, title: str = "") -> Dict[str, Any]:
    """
    Task de IA / GPU: Submete a transcrição do culto ao Gemini 1.5 Flash para mineração teológica
    e enriquecimento determinístico de timestamps via âncoras nominais de 7 palavras.
    """
    job_id = self.request.id or "task_mine_gpu"
    logger.info("Iniciando mineração de conteúdo via Gemini LLM na GPU/IA", job_id=job_id, path=transcript_json_path)

    path_obj = Path(transcript_json_path)
    if not path_obj.exists():
        logger.error("Arquivo de transcrição não encontrado", job_id=job_id, path=transcript_json_path)
        raise FileNotFoundError(f"Arquivo não encontrado: {transcript_json_path}")

    # Lê o conteúdo do texto (.txt) e dos segmentos (.json)
    txt_path = path_obj.with_suffix(".txt")
    text_content = ""
    if txt_path.exists():
        with open(txt_path, "r", encoding="utf-8") as f:
            text_content = f.read()

    segments_data = None
    if path_obj.suffix.lower() == ".json":
        with open(path_obj, "r", encoding="utf-8") as f:
            segments_data = json.load(f)

    # Executa a mineração com a classe ContentMinerLLM
    miner = ContentMinerLLM()
    sermon_title = title or path_obj.stem
    insights_dict = miner.mine_transcription(
        text_content=text_content,
        segments_data=segments_data,
        title=sermon_title
    )

    # Salva os resultados no banco SQLite e em arquivo .insights.json
    state_mgr = MasterPlanManager()
    v_id = sermon_title.split("_")[2] if len(sermon_title.split("_")) > 2 else sermon_title

    out_insights_dir = path_obj.parent.parent / "conteudos_fase3"
    out_insights_dir.mkdir(parents=True, exist_ok=True)
    out_json_file = out_insights_dir / f"{sermon_title}.insights.json"

    raw_json_str = json.dumps(insights_dict, ensure_ascii=False, indent=2)
    with open(out_json_file, "w", encoding="utf-8") as f:
        f.write(raw_json_str)

    state_mgr.save_insights_fase3(
        video_id=v_id,
        idx=1,
        title=sermon_title,
        insights_dict=insights_dict,
        raw_json=raw_json_str
    )

    logger.info("Mineração de conteúdo concluída com sucesso", job_id=job_id, output_json=out_json_file.name)
    return insights_dict
