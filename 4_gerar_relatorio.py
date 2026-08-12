"""
======================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 4: EXPORTAÇÃO DE JSON E RELATÓRIOS
======================================================================

Script de execução exclusiva da ETAPA 4.
Consolida todas as análises salvas no SQLite, exporta o plano_mestre_ibpmcr.json
e gera os relatórios executivos em HTML e PDF (relatorio_acervo_ibpmcr.pdf e PLANO_MESTRE_IBPMCR_COMPLETO.pdf).

Uso:
  python 4_gerar_relatorio.py
"""

import sys
import os
import logging
from pathlib import Path

# Garante importação do diretório raiz
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DB_PATH, JSON_MASTER_PATH, REPORTS_DIR, READABLE_PDF_PATH
from src.core.state_manager import MasterPlanManager
from src.discovery.generate_report import Phase1ReportGenerator
from generate_readable_pdf import build_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa4_Relatorios")


def main():
    print("\n" + "="*75)
    print(" [IBPM CR] AUTOMATION SYSTEM - ETAPA 4: EXPORTAÇÃO DE JSON & RELATÓRIOS")
    print("   Canal: @ibpmcr7976 | Consolidação do Acervo Histórico IBPM CR")
    print("="*75 + "\n")

    state_mgr = MasterPlanManager()
    report_gen = Phase1ReportGenerator()

    # 1. Exporta o Plano Mestre JSON consolidado
    logger.info("[PASSO 1] Exportando o banco de dados SQLite para o Plano Mestre JSON...")
    json_path = state_mgr.export_master_json()

    # 2. Gera Relatórios Diagnósticos Executivos (HTML e PDF)
    logger.info("[PASSO 2] Gerando relatórios executivos em HTML e PDF...")
    reports = report_gen.generate_diagnostic_reports()

    # 3. Gera o PDF Legível Completo
    logger.info("[PASSO 3] Compilando o PDF Legível Completo (PLANO_MESTRE_IBPMCR_COMPLETO.pdf)...")
    build_pdf()

    print("\n" + "="*75)
    print(" 🎉 [TODAS AS 4 ETAPAS DA FASE 1 CONCLUÍDAS COM SUCESSO!]")
    print(f"   - Plano Mestre JSON:    {json_path}")
    print(f"   - Relatório HTML:       {reports['html_path']}")
    print(f"   - Relatório PDF Exec:   {reports['pdf_path']}")
    print(f"   - PDF Legível Completo: {READABLE_PDF_PATH}")
    print(f"   - Banco SQLite Local:   {DB_PATH}")
    print("="*75 + "\n")


if __name__ == "__main__":
    main()
