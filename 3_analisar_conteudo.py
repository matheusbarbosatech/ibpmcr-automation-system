"""
======================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 3: MINERAÇÃO PLN (STRICT GROUNDING)
======================================================================

Script de execução exclusiva da ETAPA 3.
Roda a análise de Processamento de Linguagem Natural (PLN) e Teológica EXCLUSIVAMENTE
sobre os textos transcritos salvos no SQLite, identificando trechos de Shorts 9:16,
passagens bíblicas reais, timeline da liturgia, e-books e score viral.

Uso:
  python 3_analisar_conteudo.py
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

# Garante importação do diretório raiz
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DB_PATH
from src.core.state_manager import MasterPlanManager
from src.discovery.content_analyzer import ContentAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa3_AnalisePLN")


def main():
    print("\n" + "="*75)
    print(" [IBPM CR] AUTOMATION SYSTEM - ETAPA 3: MINERAÇÃO PLN (STRICT GROUNDING)")
    print("   Canal: @ibpmcr7976 | Análise dos 25 Pilares sobre Textos Transcritos")
    print("="*75 + "\n")

    # 1. Inicializa Gerenciadores
    state_mgr = MasterPlanManager()
    analyzer = ContentAnalyzer()

    # 2. Busca vídeos transcritos que aguardam mineração PLN
    pending_analysis = state_mgr.get_pending_analysis()
    total_pending = len(pending_analysis)

    if total_pending == 0:
        print("✅ Nenhuma análise pendente! Todos os cultos transcritos já foram minerados pelo PLN.")
        print("\n👉 PRÓXIMO PASSO: Execute 'python 4_gerar_relatorio.py' para exportar os relatórios finais!\n")
        return

    print(f"[INFO] Total de {total_pending} cultos transcritos aguardando mineração PLN de 25 Pilares!")

    # 3. Executa mineração PLN Strict Grounding
    processed_count = 0

    with tqdm(total=total_pending, desc="Mineração PLN 25 Pilares", unit="culto") as pbar:
        for vid in pending_analysis:
            v_id = vid["video_id"]
            idx = vid.get("indice_sequencial", 0)

            pbar.set_postfix_str(f"[{idx:03d}] Minerando {v_id}...")

            # Executa a análise PLN sobre o registro gravado no SQLite
            analysis_res = analyzer.analyze_db_record(vid)

            # Persiste os resultados no SQLite
            state_mgr.save_pln_analysis(v_id, analysis_res, metadata=vid)

            processed_count += 1
            pbar.update(1)

    print("\n" + "="*75)
    print(" 🎉 [ETAPA 3 CONCLUÍDA COM SUCESSO!]")
    print(f"   - Cultos Minerados nesta Rodada: {processed_count}")
    print(f"   - Banco SQLite Local:            {DB_PATH}")
    print("="*75)
    print("\n👉 PRÓXIMO PASSO: Execute 'python 4_gerar_relatorio.py' para gerar o Plano Mestre em JSON e PDF!\n")


if __name__ == "__main__":
    main()
