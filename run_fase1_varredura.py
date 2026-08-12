"""
Script Principal de Orquestração da FASE 1 - IBPM CR Automation System.

Executa o mapeamento e transcrição profunda das LIVES do acervo da IBPM CR
(do 1º culto em 02/10/2022 até hoje), baixando os áudios MP3/M4A leves para data/audio_podcasts/,
transcrevendo via Faster-Whisper CPU e minerando os 25 pilares com timestamps reais por segundo.

Uso:
  python run_fase1_varredura.py [--limit 500] [--batch 10]
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
from config.settings import DB_PATH, JSON_MASTER_PATH, REPORTS_DIR, AUDIO_DIR
from src.core.state_manager import MasterPlanManager
from src.discovery.channel_sweeper import ChannelSweeper
from src.discovery.transcriber_batch import BatchTranscriber
from src.discovery.content_analyzer import ContentAnalyzer
from src.discovery.generate_report import Phase1ReportGenerator
from generate_readable_pdf import build_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("IBPMCR_FASE1")


def main():
    parser = argparse.ArgumentParser(description="Varredura e Ingestão Profunda de Áudio - FASE 1 IBPM CR")
    parser.add_argument("--limit", type=int, default=500, help="Limite máximo de cultos a varrer (padrão: 500)")
    parser.add_argument("--batch", type=int, default=0, help="Número de cultos a transcrever nesta rodada (0 = todos)")
    parser.add_argument("--fast", action="store_true", default=False, help="Modo varredura rápida apenas de metadados")
    args = parser.parse_args()

    fast_mode = args.fast

    print("\n" + "="*70)
    print(" [IBPM CR] AUTOMATION SYSTEM - FASE 1: INGESTÃO PROFUNDA DE ÁUDIO & IA")
    print("   Canal: @ibpmcr7976 | Acervo Histórico: 02/10/2022 até Hoje")
    print(f"   Modo de Análise: {'Varredura Rápida de Metadados' if fast_mode else 'Transcrição Profunda de Áudio (Faster-Whisper CPU)'}")
    print(f"   Pasta de Áudios: {AUDIO_DIR}")
    print("="*70 + "\n")

    # 1. Inicializa Gerenciador de Estado no SQLite
    state_mgr = MasterPlanManager()
    sweeper = ChannelSweeper()
    transcriber = BatchTranscriber()
    analyzer = ContentAnalyzer()
    report_gen = Phase1ReportGenerator()

    # 2. Mapeia a aba de LIVES (/streams + Uploads UU...)
    logger.info("[STEP 1] Varrendo a aba de LIVES (/streams) do canal @ibpmcr7976...")
    catalog = sweeper.sweep_channel_metadata(limit=args.limit)

    if not catalog:
        logger.error("[ERRO] Nenhum vídeo encontrado na varredura. Verifique a conexão com o YouTube.")
        sys.exit(1)

    print(f"\n[INFO] Total de {len(catalog)} cultos mapeados no acervo!")
    print(f"[INFO] 1º Culto Histórico: {catalog[0].get('titulo_original')} ({catalog[0].get('data_publicacao')[:10]})")
    print(f"[INFO] Culto Mais Recente: {catalog[-1].get('titulo_original')} ({catalog[-1].get('data_publicacao')[:10]})\n")

    # 3. Processa transcrição de áudio MP3/M4A e mineração profunda de forma resumível
    logger.info("[STEP 2] Baixando áudios reais, transcrevendo e minerando os 25 Pilares...")
    
    processed_count = 0

    with tqdm(total=len(catalog), desc="Ingestão de Áudio & IA", unit="culto") as pbar:
        for i, vid in enumerate(catalog, 1):
            v_id = vid["video_id"]
            titulo = vid["titulo_original"]
            data_str = vid.get("data_publicacao", "")[:10]

            # Checagem de Idempotência: verifica se já foi transcrito com áudio real / legenda oficial
            if state_mgr.is_video_processed(v_id, require_real_audio=not fast_mode):
                pbar.set_postfix_str(f"Já transcrito: {v_id}")
                pbar.update(1)
                continue

            # Se especificou um limite de lote por rodada
            if args.batch > 0 and processed_count >= args.batch:
                logger.info(f"🛑 Lote de {args.batch} cultos concluído nesta rodada. Pausando para retomada posterior...")
                break

            # Obtenção de Transcrição de Áudio Real e Mineração dos 25 Pilares
            trans_res = transcriber.get_video_transcription(v_id, vid["url"], fast_sweep=fast_mode)
            analysis_res = analyzer.analyze_transcript(trans_res, metadata=vid)

            # Persistência idempotente no SQLite + JSON Mestre
            tipo_trans = trans_res.get("tipo_transcricao", "audio_real")
            state_mgr.update_video_analysis(v_id, vid, analysis_res, tipo_transcricao=tipo_trans, export_json=False)

            processed_count += 1
            pbar.set_postfix_str(f"OK ({tipo_trans}): {v_id} ({data_str})")
            pbar.update(1)

    # 4. Sincroniza o JSON Mestre final
    state_mgr.export_master_json()

    # 5. Geração dos Relatórios Executivos (HTML & PDF)
    print("\n[STEP 3] Gerando Relatórios Diagnósticos Executivos (PDF & HTML)...")
    reports = report_gen.generate_diagnostic_reports()
    build_pdf()

    print("\n" + "="*70)
    print(" [SUCESSO] INGESTÃO PROFUNDA DE ÁUDIO CONCLUÍDA / ATUALIZADA!")
    print(f"   - Cultos processados nesta rodada: {processed_count}")
    print(f"   - Pasta de Áudios MP3/M4A:         {AUDIO_DIR}")
    print(f"   - Banco SQLite Local:              {DB_PATH}")
    print(f"   - Plano Mestre JSON:               {JSON_MASTER_PATH}")
    print(f"   - Relatório PDF Legível:           PLANO_MESTRE_IBPMCR_COMPLETO.pdf")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
