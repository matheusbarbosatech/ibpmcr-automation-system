"""
Script de Ingestão e Mineração Direta de Áudios Locais via Gemini 1.5 Flash File API.

Processa todos os 451 áudios MP3 já baixados localmente na pasta 'data/audio_podcasts',
enviando o arquivo diretamente do seu computador para a File API do Gemini (sem passar pelo Colab/Drive).
Realiza a transcrição e mineração teológica (Fases 2 e 3 integradas) em um único passo resiliente!

Uso no Terminal:
    python processar_audios_locais_gemini.py
    python processar_audios_locais_gemini.py --limit 10
"""

import sys
import os
import json
import time
import argparse
import logging
from pathlib import Path

# Suporte UTF-8 no console do Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.gemini_client import TheologyMinerClient
from src.core.state_manager import MasterPlanManager

logger = get_logger("ProcessadorLocalGemini")


def print_banner():
    banner = f"""
===========================================================================
 🚀 [IBPM CR] PROCESSADOR DE ÁUDIOS LOCAIS VIA GEMINI 1.5 FLASH (ROTA NATIVA)
   Acervo Local:       data/audio_podcasts (*.mp3, *.m4a, *.webm)
   Estratégia:         Upload Direto -> Gemini File API (Zero Uso de RAM/GPU do PC)
   Fases Integradas:   Fase 2 (Transcrição) + Fase 3 (Mineração Pydantic)
===========================================================================
    """
    print(banner)


def run_batch_audio_processing(limit: Optional[int] = None):
    print_banner()

    audio_dir = Path("data/audio_podcasts")
    insights_dir = Path("data/audio_podcasts/conteudos_fase3")
    trans_dir = Path("data/audio_podcasts/transcricoes")
    
    insights_dir.mkdir(parents=True, exist_ok=True)
    trans_dir.mkdir(parents=True, exist_ok=True)

    state_mgr = MasterPlanManager()
    miner_client = TheologyMinerClient()

    # Mapeia todos os arquivos de áudio válidos no disco
    audio_files = sorted([
        f for f in audio_dir.glob("*")
        if f.suffix.lower() in [".mp3", ".m4a", ".webm"] and not f.name.endswith(".part") and f.stat().st_size > 10000
    ])

    if not audio_files:
        logger.warning("Nenhum arquivo de áudio encontrado em data/audio_podcasts.")
        return

    # Filtra cultos que ainda não possuem .insights.json minerado
    pending_files = []
    for f in audio_files:
        insight_path = insights_dir / f"{f.stem}.insights.json"
        if not (insight_path.exists() and insight_path.stat().st_size > 100):
            pending_files.append(f)

    logger.info(f"📋 Cultos Mapeados: {len(audio_files)} | Pendentes de Mineração Direta: {len(pending_files)}")

    if not pending_files:
        logger.info("🎉 Todos os cultos locais já possuem relatórios minerados com sucesso!")
        return

    if limit and limit > 0:
        pending_files = pending_files[:limit]
        logger.info(f"⚙️ Limitando execução aos primeiros {limit} cultos pendentes.")

    success_count = 0

    for idx, audio_file in enumerate(pending_files, 1):
        v_name = audio_file.stem
        v_id = v_name.split("_")[2] if len(v_name.split("_")) > 2 else v_name
        
        logger.info(f"\n🎧 [{idx}/{len(pending_files)}] Processando Culto: {v_name}")

        try:
            # Envia o MP3 local diretamente para a Gemini File API
            mining_payload = miner_client.analyze_audio_file(
                audio_file_path=audio_file,
                source_video_id=v_id,
                job_id=f"job_audio_{v_id}"
            )

            # Persiste o arquivo .insights.json
            insight_path = insights_dir / f"{v_name}.insights.json"
            raw_json_str = mining_payload.model_dump_json(indent=2)
            
            with open(insight_path, "w", encoding="utf-8") as f:
                f.write(raw_json_str)

            # Atualiza o SQLite master
            state_mgr.save_insights_fase3(
                video_id=v_id,
                idx=idx,
                title=v_name,
                insights_dict=mining_payload.model_dump(),
                raw_json=raw_json_str
            )

            success_count += 1
            logger.info(f"✅ Culto {v_name} minerado e registrado no SQLite com sucesso!")

        except Exception as e:
            logger.error(f"⚠️ Erro ao processar áudio {v_name}: {e}")
            time.sleep(5)

    logger.info(f"\n🎉 Varredura concluída! {success_count} de {len(pending_files)} cultos processados com sucesso via Gemini File API.")


def main():
    parser = argparse.ArgumentParser(description="Processador Direto de Áudios Locais via Gemini 1.5 Flash File API (IBPM CR)")
    parser.add_argument("--limit", type=int, default=None, help="Limite de cultos a processar por lote")
    args = parser.parse_args()

    run_batch_audio_processing(limit=args.limit)


if __name__ == "__main__":
    main()
