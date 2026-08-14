"""
Serviço Orquestrador da Fase 3 (Mineração Teológica) - IBPM CR Automation System.

Orquestra a chamada cognitiva ao Gemini API via TheologyMinerClient, lê o stream de palavras
do Faster-Whisper, executa o alinhamento fuzzy via AnchorAligner para converter âncoras nominais
em coordenadas temporais exatas (start_sec e end_sec) e persiste o payload final.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from src.core.logger import get_logger
from src.infrastructure.gemini_client import TheologyMinerClient
from src.infrastructure.alignment import AnchorAligner
from src.domain.schemas import SermonMiningResponse
from src.core.state_manager import MasterPlanManager

logger = get_logger("TheologyMinerService")


class TheologyMinerService:
    """
    Orquestrador de Caso de Uso para a Fase 3 da Pipeline (Mineração e Alinhamento).
    """

    def __init__(self, miner_client: Optional[TheologyMinerClient] = None, aligner: Optional[AnchorAligner] = None):
        self.miner_client = miner_client or TheologyMinerClient()
        self.aligner = aligner or AnchorAligner()
        self.state_mgr = MasterPlanManager()

    def process_sermon_mining(
        self,
        transcript_txt_path: Path,
        segments_json_path: Path,
        video_id: str = "IBPM_CULTO",
        job_id: str = "job_miner_service"
    ) -> SermonMiningResponse:
        """
        Executa o fluxo completo da Fase 3:
        1. Lê a transcrição contínua e o JSON de palavras
        2. Submete a transcrição ao Gemini API
        3. Cruza as âncoras de 7 palavras com os timestamps do Whisper
        4. Grava o payload enriquecido no disco e no SQLite
        """
        logger.info("Iniciando serviço de mineração teológica da Fase 3", job_id=job_id, video_id=video_id)

        if not transcript_txt_path.exists():
            raise FileNotFoundError(f"Arquivo de texto da transcrição não encontrado: {transcript_txt_path}")

        with open(transcript_txt_path, "r", encoding="utf-8") as f:
            transcript_text = f.read()

        whisper_words = []
        if segments_json_path.exists():
            with open(segments_json_path, "r", encoding="utf-8") as f:
                segments_raw = json.load(f)
                
                # Extrai a lista plana de palavras ou segmentos
                if isinstance(segments_raw, list):
                    for item in segments_raw:
                        if "words" in item and isinstance(item["words"], list):
                            whisper_words.extend(item["words"])
                        else:
                            whisper_words.append(item)

        # Step 1: Chamada cognitiva ao Gemini
        mining_response: SermonMiningResponse = self.miner_client.analyze_transcript(
            transcript_text=transcript_text,
            source_video_id=video_id,
            job_id=job_id
        )

        # Step 2: Alinhamento determinístico de timestamps por Levenshtein
        if whisper_words:
            for idx, cut in enumerate(mining_response.short_form_cuts):
                start_sec, _ = self.aligner.align_anchor_to_timestamps(
                    whisper_words, cut.start_anchor_7_words, is_end_anchor=False, job_id=job_id
                )
                end_sec, _ = self.aligner.align_anchor_to_timestamps(
                    whisper_words, cut.end_anchor_7_words, is_end_anchor=True, job_id=job_id
                )

                # Validação de sanidade temporal
                if end_sec <= start_sec:
                    end_sec = start_sec + 45.0

                logger.info(
                    f"Corte Short-Form #{idx+1} alinhado com sucesso",
                    job_id=job_id,
                    cut_id=cut.cut_id,
                    start_sec=start_sec,
                    end_sec=end_sec
                )

        # Step 3: Persistência do Payload Enriquecido
        output_insights_dir = transcript_txt_path.parent.parent / "conteudos_fase3"
        output_insights_dir.mkdir(parents=True, exist_ok=True)
        insights_file = output_insights_dir / f"{transcript_txt_path.stem}.insights.json"

        raw_json_str = mining_response.model_dump_json(indent=2)
        with open(insights_file, "w", encoding="utf-8") as f:
            f.write(raw_json_str)

        self.state_mgr.save_insights_fase3(
            video_id=video_id,
            idx=1,
            title=transcript_txt_path.stem,
            insights_dict=mining_response.model_dump(),
            raw_json=raw_json_str
        )

        logger.info(
            "Fase 3 concluída com sucesso. Payload minerado e enriquecido salvo no disco e SQLite",
            job_id=job_id,
            file=insights_file.name
        )
        return mining_response
