"""
Script Principal da Etapa 3: Análise de PLN e Mineração de Insights Homiléticos (Strict Grounding).

Execução independente e idempotente.
Processa EXCLUSIVAMENTE os vídeos com transcrição confirmada no SQLite (transcrito = 1 AND analisado_pln = 0),
minando citações 9:16 para Shorts, trechos para Vídeos Médios, referências bíblicas e RAG Chunks.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import DB_PATH
from src.discovery.content_analyzer import ContentAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa3_AnalisarConteudo")


def print_banner():
    banner = """
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 3: ANÁLISE DE PLN E MINERAÇÃO (STRICT GROUNDING)
   Regra Absoluta: Análise APENAS de Vídeos Efetivamente Transcritos no SQLite
   Resultados: 9:16 Shorts, Vídeos Médios, Referências Bíblicas & Chunks RAG
===========================================================================
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Etapa 3 - Análise de PLN de Conteúdo Transcrito")
    parser.add_argument("--batch-size", type=int, default=50, help="Quantidade de transcrições a analisar por lote (padrão: 50)")
    args = parser.parse_args()

    print_banner()

    analyzer = ContentAnalyzer()
    analyzed_count = analyzer.process_pending_transcriptions(limit=args.batch_size)

    print("\n" + "=" * 75)
    print(" RESUMO DA EXECUÇÃO DA ETAPA 3:")
    print(f"   • Cultos Analisados via PLN: {analyzed_count}")
    print(f"   • Banco de Dados Atualizado: {DB_PATH}")
    print("=" * 75)
    print(" [ETAPA 3 CONCLUÍDA COM SUCESSO!]")
    print(" Para gerar os relatórios em PDF/HTML e JSON Mestre, rode: python 4_gerar_relatorio.py")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
