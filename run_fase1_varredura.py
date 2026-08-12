"""
Script Principal de Orquestração da FASE 1 - IBPM CR Automation System.

Executa o mapeamento sequencial de 100% das LIVES e cultos do acervo da IBPM CR
(do 1º culto em 02/10/2022 até hoje), minerando os 25 pilares de insights teológicos,
litúrgicos, homiléticos e de mídia social com barra de progresso tqdm e salvando no SQLite/JSON.

Uso:
  python run_fase1_varredura.py [--limit 500] [--fast]
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Adiciona diretório raiz ao PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from tqdm import tqdm
from config.settings import DB_PATH, JSON_MASTER_PATH, REPORTS_DIR
from src.core.state_manager import MasterPlanManager
from src.discovery.channel_sweeper import ChannelSweeper
from src.discovery.transcriber_batch import BatchTranscriber
from src.discovery.content_analyzer import ContentAnalyzer
from src.discovery.generate_report import Phase1ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("IBPMCR_FASE1")


def main():
    parser = argparse.ArgumentParser(description="Varredura e Plano Mestre FASE 1 - IBPM CR")
    parser.add_argument("--limit", type=int, default=500, help="Limite máximo de cultos a varrer (padrão: 500)")
    parser.add_argument("--fast", action="store_true", default=True, help="Modo varredura rápida de Fase 1 (sem travar em downloads pesados)")
    args = parser.parse_args()

    print("\n" + "="*70)
    print(" [IBPM CR] AUTOMATION SYSTEM - FASE 1: VARREDURA DE LIVES & PLANO MESTRE")
    print("   Canal: @ibpmcr7976 | Acervo Histórico: 02/10/2022 até Hoje")
    print("   Modo de Análise: 25 Pilares Integrados (Homilética, Liturgia, Mídia & RAG)")
    print("="*70 + "\n")

    # 1. Inicializa o Gerenciador de Estado no SQLite
    state_mgr = MasterPlanManager()
    sweeper = ChannelSweeper()
    transcriber = BatchTranscriber()
    analyzer = ContentAnalyzer()
    report_gen = Phase1ReportGenerator()

    # 2. Mapeia a aba de LIVES (/streams + API v3)
    logger.info("[STEP 1] Varrendo a aba de LIVES (/streams) do canal @ibpmcr7976...")
    catalog = sweeper.sweep_channel_metadata(limit=args.limit)

    if not catalog:
        logger.error("[ERRO] Nenhum vídeo encontrado na varredura. Verifique a conexão com o YouTube.")
        sys.exit(1)

    print(f"\n[INFO] Total de {len(catalog)} cultos e transmissões mapeados no acervo!")
    print(f"[INFO] 1º Culto Histórico (Mais Antigo): {catalog[0].get('titulo_original')} ({catalog[0].get('data_publicacao')[:10]})")
    print(f"[INFO] Culto Mais Recente: {catalog[-1].get('titulo_original')} ({catalog[-1].get('data_publicacao')[:10]})\n")

    # 3. Processa cada culto em ordem cronológica com barra de progresso tqdm
    logger.info("[STEP 2] Processando a transcrição e minerando os 25 Pilares de Insights...")
    
    with tqdm(total=len(catalog), desc="Mapeando Cultos IBPM CR", unit="culto") as pbar:
        for i, vid in enumerate(catalog, 1):
            v_id = vid["video_id"]
            titulo = vid["titulo_original"]
            data_str = vid.get("data_publicacao", "")[:10]

            # Checagem de Idempotência
            if state_mgr.is_video_processed(v_id):
                pbar.set_postfix_str(f"Já catalogado: {v_id}")
                pbar.update(1)
                continue

            # Obtenção de Transcrição e Mineração dos 25 Pilares
            trans_res = transcriber.get_video_transcription(v_id, vid["url"], fast_sweep=args.fast)
            analysis_res = analyzer.analyze_transcript(trans_res, metadata=vid)

            # Persistência idempotente no SQLite + JSON Mestre
            state_mgr.update_video_analysis(v_id, vid, analysis_res)

            pbar.set_postfix_str(f"OK: {v_id} ({data_str})")
            pbar.update(1)

    # 4. Geração dos Relatórios Executivos (HTML & PDF)
    print("\n[STEP 3] Gerando Relatórios Diagnósticos Executivos (PDF & HTML)...")
    reports = report_gen.generate_diagnostic_reports()

    print("\n" + "="*70)
    print(" [SUCESSO] FASE 1 CONCLUÍDA COM SUCESSO ABSOLUTO!")
    print(f"   - Banco SQLite Local: {DB_PATH}")
    print(f"   - Plano Mestre JSON:  {JSON_MASTER_PATH}")
    print(f"   - Relatório HTML:     {reports['html_path']}")
    print(f"   - Relatório PDF:      {reports['pdf_path']}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
