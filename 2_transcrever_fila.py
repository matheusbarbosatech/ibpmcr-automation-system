"""
Script Principal da Etapa 2: Transcrição Sequencial por Fila com Faster-Whisper CPU INT8.

Execução independente e idempotente para CPU.
Lê os arquivos MP3 baixados no disco na ordem cronológica (001 a 447+)
e transcreve fala por fala salvando o texto e os segmentos com marcas temporais no SQLite.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import AUDIO_DIR, DB_PATH
from src.discovery.transcriber_batch import BatchTranscriber
from src.core.state_manager import MasterPlanManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa2_TranscreverFila")


def print_banner():
    banner = """
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 2: TRANSCRIÇÃO SEQUENCIAL WHISPER CPU
   Dispositivo: CPU | Precisão: INT8 | Modelo: Faster-Whisper Base
   Foco: Transcrição Fiel (Strict Grounding) Áudio por Áudio do Disco
===========================================================================
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Etapa 2 - Transcrição de Fila com Faster-Whisper CPU")
    parser.add_argument("--batch-size", type=int, default=10, help="Quantidade de vídeos a transcrever por lote (padrão: 10)")
    parser.add_argument("--model-size", type=str, default="base", help="Tamanho do modelo Faster-Whisper (tiny, base, small, medium)")
    args = parser.parse_args()

    print_banner()

    transcriber = BatchTranscriber(model_size=args.model_size)
    processed_count = transcriber.process_pending_queue(max_items=args.batch_size)

    print("\n" + "=" * 75)
    print(" RESUMO DA EXECUÇÃO DA ETAPA 2:")
    print(f"   • Áudios Transcritos no Lote: {processed_count}")
    print(f"   • Modelo Utilizado: Faster-Whisper ({args.model_size}) no CPU")
    print(f"   • Banco de Dados Atualizado: {DB_PATH}")
    print("=" * 75)
    print(" [ETAPA 2 CONCLUÍDA COM SUCESSO!]")
    print(" Para prosseguir para a análise de PLN, rode: python 3_analisar_conteudo.py")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
