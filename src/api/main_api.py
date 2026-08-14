"""
Backend Server FastAPI - IBPM CR AUTOMATION SYSTEM.

Fornece endpoints RESTful para ingestão por link do YouTube, mineração teológica via Gemini API,
listagem do acervo de cultos e orquestração de renderização de vídeos (Shorts 9:16 e Mid-Form 16:9).

Execução no Terminal:
    uvicorn src.api.main_api:app --reload --port 8000
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.core.logger import get_logger
from src.core.state_manager import MasterPlanManager
from src.infrastructure.gemini_client import TheologyMinerClient
from src.services.video_pipeline import VideoPipelineService
from baixar_culto import download_single_sermon_mp3

logger = get_logger("FastAPIBackend")

app = FastAPI(
    title="IBPM CR Automation System API",
    description="Backend de Automação de Produção Audiovisual e Mineração Teológica para a Igreja Batista Pentecostal Mundial.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory="data"), name="media")


class IngestRequest(BaseModel):
    youtube_url: str = Field(description="URL ou ID do vídeo do YouTube para ingestão do áudio MP3.")


class ProcessGeminiRequest(BaseModel):
    audio_file_path: str = Field(description="Caminho relativo ou absoluto do arquivo de áudio local.")
    video_id: Optional[str] = Field(default="IBPM_CULTO", description="ID do vídeo de origem.")


class RenderRequest(BaseModel):
    cut_id: str = Field(description="Identificador único do corte.")
    video_url: str = Field(description="URL do vídeo no YouTube para corte cirúrgico.")
    cut_payload: Dict[str, Any] = Field(description="Payload estruturado do corte.")
    format_type: str = Field(default="9:16", description="Formato do vídeo: '9:16' (Shorts/Reels) ou '16:9' (YouTube Mid-Form).")
    start_sec: float = Field(default=0.0, description="Segundo inicial do trecho.")
    end_sec: float = Field(default=45.0, description="Segundo final do trecho.")


@app.get("/")
def read_root():
    return {
        "system": "IBPM CR AUTOMATION SYSTEM",
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.post("/api/v1/ingest")
def api_ingest_youtube_audio(req: IngestRequest):
    logger.info("Solicitação de Ingestão via API recebida", url=req.youtube_url)
    try:
        audio_path = download_single_sermon_mp3(req.youtube_url)
        if not audio_path or not audio_path.exists():
            raise HTTPException(status_code=500, detail="Falha ao efetuar o download do áudio do YouTube.")

        return {
            "status": "success",
            "message": "Áudio baixado e cadastrado no sistema com sucesso!",
            "file_name": audio_path.name,
            "file_path": str(audio_path),
            "size_mb": round(audio_path.stat().st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error("Erro no endpoint /api/v1/ingest", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/process-gemini")
def api_process_gemini_audio(req: ProcessGeminiRequest):
    audio_path = Path(req.audio_file_path)
    logger.info("Solicitação de Mineração via Gemini API recebida", audio=str(audio_path))

    if not audio_path.exists():
        candidate = Path("data/audio_podcasts") / audio_path.name
        if candidate.exists():
            audio_path = candidate
        else:
            raise HTTPException(status_code=404, detail=f"Arquivo de áudio não encontrado: {req.audio_file_path}")

    try:
        miner_client = TheologyMinerClient()
        v_id = req.video_id or audio_path.stem
        
        mining_payload = miner_client.analyze_audio_file(
            audio_file_path=audio_path,
            source_video_id=v_id,
            job_id=f"job_api_{v_id}"
        )

        insights_dir = Path("data/audio_podcasts/conteudos_fase3")
        insights_dir.mkdir(parents=True, exist_ok=True)
        insight_path = insights_dir / f"{audio_path.stem}.insights.json"
        
        raw_json_str = mining_payload.model_dump_json(indent=2)
        with open(insight_path, "w", encoding="utf-8") as f:
            f.write(raw_json_str)

        state_mgr = MasterPlanManager()
        state_mgr.save_insights_fase3(
            video_id=v_id,
            idx=1,
            title=audio_path.stem,
            insights_dict=mining_payload.model_dump(),
            raw_json=raw_json_str
        )

        return {
            "status": "success",
            "message": "Mineração teológica concluída via Gemini 1.5 Flash File API!",
            "insights_file": insight_path.name,
            "payload": mining_payload.model_dump()
        }
    except Exception as e:
        logger.error("Erro no endpoint /api/v1/process-gemini", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/cultos")
def api_list_cultos():
    state_mgr = MasterPlanManager()
    videos = state_mgr.get_all_videos()

    audio_dir = Path("data/audio_podcasts")
    insights_dir = Path("data/audio_podcasts/conteudos_fase3")

    results = []
    local_audios = {f.name: f for f in audio_dir.glob("*") if f.suffix.lower() in [".mp3", ".m4a", ".webm"]}

    if videos:
        for v in videos:
            v_dict = dict(v)
            fn = v_dict.get("nome_arquivo_mp3", "")
            ins_fn = f"{Path(fn).stem}.insights.json" if fn else ""
            
            v_dict["has_audio_file"] = os.path.exists(os.path.join(audio_dir, fn)) if fn else False
            v_dict["has_insights_file"] = os.path.exists(os.path.join(insights_dir, ins_fn)) if ins_fn else False
            results.append(v_dict)
    else:
        for fname, fpath in local_audios.items():
            ins_fn = f"{fpath.stem}.insights.json"
            results.append({
                "video_id": fpath.stem.split("_")[2] if len(fpath.stem.split("_")) > 2 else fpath.stem,
                "titulo_original": fpath.stem,
                "nome_arquivo_mp3": fname,
                "has_audio_file": True,
                "has_insights_file": (insights_dir / ins_fn).exists()
            })

    return {
        "status": "success",
        "total": len(results),
        "cultos": results
    }


@app.post("/api/v1/render")
def api_render_cut(req: RenderRequest):
    logger.info("Solicitação de Renderização recebida", cut_id=req.cut_id, format=req.format_type)
    try:
        pipeline = VideoPipelineService()
        if req.format_type == "16:9":
            result = pipeline.execute_mid_cut_pipeline(
                video_url=req.video_url,
                cut_payload=req.cut_payload,
                start_sec=req.start_sec,
                end_sec=req.end_sec,
                publish_to_social=False,
                job_id=f"job_render_mid_{req.cut_id}"
            )
        else:
            result = pipeline.execute_short_cut_pipeline(
                video_url=req.video_url,
                cut_payload=req.cut_payload,
                start_sec=req.start_sec,
                end_sec=req.end_sec,
                publish_to_social=False,
                job_id=f"job_render_short_{req.cut_id}"
            )

        return {
            "status": "success",
            "message": f"Renderização {req.format_type} concluída com sucesso!",
            "cut_id": req.cut_id,
            "format": req.format_type,
            "final_video_path": result.get("final_video_path"),
            "formatted_description": result.get("formatted_description", "")
        }
    except Exception as e:
        logger.error("Erro no endpoint /api/v1/render", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
