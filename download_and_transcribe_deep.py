"""
Script de Ingestão Profunda de Áudio MP3 Real & Transcrição por IA.

Baixa o arquivo .mp3 de 64kbps dos cultos selecionados para data/audio_podcasts/,
executa a transcrição palavra por palavra no Faster-Whisper CPU e salva os timestamps reais.
"""

import os
import json
import logging
from pathlib import Path
from tqdm import tqdm

from config.settings import DB_PATH, AUDIO_DIR
from src.core.state_manager import MasterPlanManager
from src.discovery.channel_sweeper import ChannelSweeper
from src.discovery.transcriber_batch import BatchTranscriber
from src.discovery.content_analyzer import ContentAnalyzer
from generate_readable_pdf import build_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info(f"[INFO] Iniciando Ingestão Profunda de Áudios MP3 Reais na pasta: {AUDIO_DIR}")

    sweeper = ChannelSweeper()
    transcriber = BatchTranscriber()
    analyzer = ContentAnalyzer()
    state_mgr = MasterPlanManager()

    # Varre acervo e seleciona cultos para transcrição profunda com MP3
    catalog = sweeper.sweep_channel_metadata(limit=5)

    print(f"\n[INFO] Áudios serão salvos em: {AUDIO_DIR}")
    print("[INFO] Cultos selecionados para download de MP3 e transcrição real:\n")

    for vid in catalog:
        v_id = vid["video_id"]
        url = vid["url"]
        titulo = vid["titulo_original"]
        data_str = vid.get("data_publicacao", "")[:10]

        print(f"  -> Baixando MP3 e transcrevendo: {titulo} ({v_id})...")
        
        # Força download do MP3 real e transcrição via Faster-Whisper
        trans_res = transcriber.get_video_transcription(v_id, url, fast_sweep=False)
        analysis_res = analyzer.analyze_transcript(trans_res, metadata=vid)

        # Salva no SQLite e JSON Mestre
        state_mgr.update_video_analysis(v_id, vid, analysis_res, export_json=False)

        # Verifica se o MP3 foi salvo na pasta
        mp3_path = os.path.join(AUDIO_DIR, f"{v_id}.mp3")
        if os.path.exists(mp3_path):
            size_mb = round(os.path.getsize(mp3_path) / (1024 * 1024), 2)
            print(f"     [OK] MP3 Baixado em {mp3_path} ({size_mb} MB)")
            print(f"     [TEXTO REAL] \"{trans_res.get('texto_completo', '')[:120]}...\"\n")

    state_mgr.export_master_json()
    build_pdf()
    logger.info("[SUCESSO] INGESTÃO PROFUNDA DE ÁUDIO E TRANSCRIÇÃO CONCLUÍDAS COM SUCESSO!")


if __name__ == "__main__":
    main()
