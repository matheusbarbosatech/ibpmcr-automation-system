"""
Script de Re-análise Dinâmica dos 447 Cultos (Super Rápido).

Limpa o banco local SQLite e executa a mineração com o novo motor de PLN
DINÂMICO E ÚNICO (ContentAnalyzer) garantindo que cada um dos 447 cultos
tenha metadados, passagens bíblicas, frases e resumos 100% específicos.
"""

import sqlite3
import logging
from pathlib import Path
from tqdm import tqdm

from config.settings import DB_PATH
from src.core.state_manager import MasterPlanManager
from src.discovery.channel_sweeper import ChannelSweeper
from src.discovery.transcriber_batch import BatchTranscriber
from src.discovery.content_analyzer import ContentAnalyzer
from src.discovery.generate_report import Phase1ReportGenerator
from generate_readable_pdf import build_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("⚡ Iniciando Re-análise Dinâmica dos 447 Cultos...")

    # 1. Reset da tabela videos no SQLite para forçar re-análise
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM videos;")
    conn.execute("DELETE FROM rag_chunks;")
    conn.commit()
    conn.close()

    state_mgr = MasterPlanManager()
    sweeper = ChannelSweeper()
    transcriber = BatchTranscriber()
    analyzer = ContentAnalyzer()

    # 2. Varrer acervo completo (447 cultos)
    catalog = sweeper.sweep_channel_metadata(limit=600)
    logger.info(f"Re-analisando {len(catalog)} cultos com o motor dinâmico...")

    for vid in tqdm(catalog, desc="Re-analisando Cultos IBPM CR"):
        v_id = vid["video_id"]
        trans_res = transcriber.get_video_transcription(v_id, vid["url"], fast_sweep=True)
        analysis_res = analyzer.analyze_transcript(trans_res, metadata=vid)
        state_mgr.update_video_analysis(v_id, vid, analysis_res, export_json=False)

    # 3. Exporta JSON Mestre uma única vez no final
    state_mgr.export_master_json()

    # 4. Regenerar Relatórios e PDF Legível
    logger.info("📊 Gerando novos relatórios e PDF legível...")
    Phase1ReportGenerator().generate_diagnostic_reports()
    build_pdf()
    logger.info("🎉 RE-ANÁLISE DINÂMICA CONCLUÍDA COM SUCESSO!")


if __name__ == "__main__":
    main()
