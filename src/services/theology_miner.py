"""
Serviço de Mineração Teológica Desacoplada (Fase 2 + Fase 3) - IBPM CR Automation System.

Orquestra a Transcrição Leve (Fase 2 via Groq Whisper API / FFmpeg Compression)
e a Mineração Cognitiva de Texto (Fase 3 via Gemini 1.5 Flash Text API).
Garante zero falhas de upload de áudio, 100% de estabilidade e máxima velocidade.
"""

import json
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

        trans_dir1 = Path("data/audio_podcasts/transcricoes")
        trans_dir2 = Path("data/audio_podcasts/transcricoes_fase2")
        trans_dir1.mkdir(parents=True, exist_ok=True)
        trans_dir2.mkdir(parents=True, exist_ok=True)

        txt_path1 = trans_dir1 / f"{audio_file_path.stem}.txt"
        txt_path2 = trans_dir2 / f"{audio_file_path.stem}.txt"
        srt_path = trans_dir2 / f"{audio_file_path.stem}.srt"
        transcript_text = ""

        # STEP 1 (FASE 2): Verifica se a transcrição local (.txt ou .srt) existe nas pastas do acervo
        if txt_path1.exists() and txt_path1.stat().st_size > 50:
            logger.info("📄 Transcrição .txt encontrada em data/audio_podcasts/transcricoes. Usando texto off-line.", file=txt_path1.name)
            with open(txt_path1, "r", encoding="utf-8", errors="ignore") as f:
                transcript_text = f.read()
        elif txt_path2.exists() and txt_path2.stat().st_size > 50:
            logger.info("📄 Transcrição .txt encontrada em data/audio_podcasts/transcricoes_fase2. Usando texto off-line.", file=txt_path2.name)
            with open(txt_path2, "r", encoding="utf-8", errors="ignore") as f:
                transcript_text = f.read()
        elif srt_path.exists() and srt_path.stat().st_size > 50:
            logger.info("📄 Transcrição .srt local (Whisper Desktop) encontrada. Extraindo texto.", file=srt_path.name)
            with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_lines = f.readlines()
                text_lines = [l.strip() for l in raw_lines if l.strip() and not l.strip().isdigit() and "-->" not in l]
                transcript_text = " ".join(text_lines)
        else:
            if not self.groq.client:
                raise ValueError("Nenhuma transcrição local (.txt / .srt) encontrada e GROQ_API_KEY não configurada no .env.")
            
            trans_res = self.groq.transcribe_audio(audio_file_path, job_id=f"{job_id}_groq")
            transcript_text = trans_res.get("text", "")

        if not transcript_text or len(transcript_text.strip()) < 50:
            raise ValueError("Texto da transcrição retornado é inválido ou insuficiente.")

        # STEP 2 (FASE 3): Mineração Teológica Cognitiva (Gemini ➔ Fallback Groq Llama 3.3)
        logger.info("🧠 Disparando Mineração Teológica no Gemini 1.5 Flash via Texto", job_id=job_id)
        
        mining_payload_dict = None
        try:
            mining_payload: SermonMiningResponse = self.gemini.analyze_transcript(
                transcript_text=transcript_text,
                source_video_id=source_video_id,
                job_id=f"{job_id}_gemini"
            )
            mining_payload_dict = mining_payload.model_dump()
        except Exception as gemini_err:
            logger.warning(f"⚠️ Gemini indisponível/cota excedida ({gemini_err}). Alternando automaticamente para Groq Llama 3.3 70B...", job_id=job_id)
            if not self.groq.client:
                raise RuntimeError(f"Gemini falhou ({gemini_err}) e GROQ_API_KEY não está disponível para o fallback.")
            
            mining_payload_dict = self.groq.analyze_transcript_with_groq(
                transcript_text=transcript_text,
                source_video_id=source_video_id,
                job_id=f"{job_id}_groq_llama"
            )

        # STEP 3: Persiste o JSON dos insights minerados na pasta da Fase 3
        insights_dir = Path("data/audio_podcasts/conteudos_fase3")
        insights_dir.mkdir(parents=True, exist_ok=True)
        out_file = insights_dir / f"{audio_file_path.stem}.insights.json"

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(mining_payload_dict, f, ensure_ascii=False, indent=2)

        logger.info("✅ Mineração Teológica Desacoplada Concluída com Sucesso", job_id=job_id, insights_file=out_file.name)

        short_cuts = mining_payload_dict.get("short_form_cuts", [])
        mid_cuts = mining_payload_dict.get("mid_form_cuts", [])

        # Atualiza SQLite Master Plan State
        self.state_mgr.save_insights_fase3(
            video_id=source_video_id,
            idx=1,
            title=audio_file_path.stem,
            insights_dict=mining_payload_dict,
            raw_json=json.dumps(mining_payload_dict)
        )

        return {
            "job_id": job_id,
            "status": "SUCCESS",
            "audio_name": audio_file_path.name,
            "transcript_words_count": len(transcript_text.split()),
            "short_cuts_count": len(short_cuts),
            "mid_cuts_count": len(mid_cuts),
            "insights_file": str(out_file),
            "payload": mining_payload_dict
        }
