"""
Serviço de Mineração Teológica Desacoplada (Fase 2 + Fase 3) - IBPM CR Automation System.

Orquestra a Transcrição Leve (Fase 2 via Groq Whisper API / FFmpeg Compression)
e a Mineração Cognitiva de Texto (Fase 3 via Gemini 1.5 Flash Text API).
Garante zero falhas de upload de áudio, 100% de estabilidade e máxima velocidade.
"""

from pathlib import Path
from typing import Dict, Any, Optional

from src.core.logger import get_logger
from src.core.state_manager import MasterPlanManager
from src.domain.schemas import SermonMiningResponse
from src.infrastructure.groq_client import GroqWhisperClient
from src.infrastructure.gemini_client import TheologyMinerClient

logger = get_logger("DecoupledTheologyMinerService")


class DecoupledTheologyMinerService:
    """
    Serviço orquestrador das Fases 2 e 3 desacopladas.
    """

    def __init__(
        self,
        groq_client: Optional[GroqWhisperClient] = None,
        gemini_client: Optional[TheologyMinerClient] = None
    ):
        self.groq = groq_client or GroqWhisperClient()
        self.gemini = gemini_client or TheologyMinerClient()
        self.state_mgr = MasterPlanManager()

    def execute_decoupled_pipeline(
        self,
        audio_file_path: Path,
        source_video_id: str = "IBPM_CULTO",
        job_id: str = "job_decoupled_mining"
    ) -> Dict[str, Any]:
        """
        Executa a pipeline desacoplada:
        1. Transcreve o MP3 compactado via Groq Whisper Large V3 (Fase 2) em segundos.
        2. Lê o arquivo .txt gerado e dispara a mineração teológica no Gemini 1.5 Flash via Texto (Fase 3).
        """
        if not audio_file_path.exists():
            raise FileNotFoundError(f"Áudio local não encontrado: {audio_file_path}")

        logger.info(
            "🚀 Iniciando Pipeline Desacoplada (Groq Transcrição ➔ Gemini Texto)",
            job_id=job_id,
            audio=audio_file_path.name
        )

        trans_dir = Path("data/audio_podcasts/transcricoes_fase2")
        trans_dir.mkdir(parents=True, exist_ok=True)

        txt_path = trans_dir / f"{audio_file_path.stem}.txt"
        transcript_text = ""

        # STEP 1 (FASE 2): Transcrição se o arquivo .txt ainda não existir
        if txt_path.exists() and txt_path.stat().st_size > 50:
            logger.info("📄 Transcrição .txt já existente encontrada no disco. Pulando Groq API.", file=txt_path.name)
            with open(txt_path, "r", encoding="utf-8") as f:
                transcript_text = f.read()
        else:
            if not self.groq.client:
                raise ValueError("GROQ_API_KEY necessária para transcrição da Fase 2.")
            
            trans_res = self.groq.transcribe_audio(audio_file_path, job_id=f"{job_id}_groq")
            transcript_text = trans_res.get("text", "")

        if not transcript_text or len(transcript_text.strip()) < 50:
            raise ValueError("Texto da transcrição retornado é inválido ou insuficiente.")

        # STEP 2 (FASE 3): Mineração Cognitiva via Texto no Gemini 1.5 Flash
        logger.info("🧠 Disparando Mineração Teológica no Gemini 1.5 Flash via Texto", job_id=job_id)
        mining_payload: SermonMiningResponse = self.gemini.analyze_transcript(
            transcript_text=transcript_text,
            source_video_id=source_video_id,
            job_id=f"{job_id}_gemini"
        )

        # Salva Payload de Insights em disco (.insights.json)
        insights_dir = Path("data/audio_podcasts/conteudos_fase3")
        insights_dir.mkdir(parents=True, exist_ok=True)
        insight_path = insights_dir / f"{audio_file_path.stem}.insights.json"

        raw_json = mining_payload.model_dump_json(indent=2)
        with open(insight_path, "w", encoding="utf-8") as f:
            f.write(raw_json)

        # Atualiza SQLite Master Plan State
        self.state_mgr.save_insights_fase3(
            video_id=source_video_id,
            idx=1,
            title=audio_file_path.stem,
            insights_dict=mining_payload.model_dump(),
            raw_json=raw_json
        )

        logger.info(
            "🎉 Pipeline Desacoplada (Fase 2 + Fase 3) concluída com 100% de sucesso!",
            job_id=job_id,
            short_cuts=len(mining_payload.short_form_cuts),
            mid_cuts=len(mining_payload.mid_form_cuts)
        )

        return {
            "status": "success",
            "message": "Mineração Teológica Desacoplada (Groq + Gemini) concluída!",
            "insights_file": insight_path.name,
            "short_cuts_count": len(mining_payload.short_form_cuts),
            "mid_cuts_count": len(mining_payload.mid_form_cuts),
            "payload": mining_payload.model_dump()
        }
