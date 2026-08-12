"""
Script Principal da Etapa 1: Varredura de Lives (/streams) e Download de Áudios MP3 Leves.

Execução independente e idempotente para a máquina local com CPU.
Varrer a rota /streams do canal @ibpmcr7976, ordenar rigorosamente PELA DATA DE POSTAGEM
do vídeo mais antigo (2022) ao mais recente (2026), e baixar todos os MP3s de 64kbps mono.
"""

import sys
import os
import io
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

# Garante codificação UTF-8 no stdout do Windows PowerShell/CMD para evitar UnicodeEncodeError com emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_HANDLE, AUDIO_DIR, DB_PATH
from src.discovery.channel_sweeper import ChannelSweeper
from src.core.state_manager import MasterPlanManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa1_DownloadAudios")


def print_banner():
    banner = """
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 1: DOWNLOAD DE ÁUDIOS MP3 LEVES
   Canal: @ibpmcr7976 | Acervo Histórico: 02/10/2022 até Hoje
   Foco: Mapeamento /streams + Download de MP3 (64kbps mono)
   Pasta de Destino: {}
===========================================================================
    """.format(AUDIO_DIR)
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Etapa 1 - Mapeamento e Download de Áudios do IBPM CR")
    parser.add_argument("--limit", type=int, default=600, help="Limite máximo de vídeos a varrer (padrão: 600)")
    parser.add_argument("--force-redownload", action="store_true", help="Forçar o re-download mesmo se o arquivo já existir")
    args = parser.parse_args()

    print_banner()

    state_mgr = MasterPlanManager()
    sweeper = ChannelSweeper()

    print("\n[PASSO 1] Mapeando a aba /streams e ordenando pela DATA DE POSTAGEM...")
    catalog = sweeper.sweep_and_index_channel(limit=args.limit)

    if not catalog:
        print("❌ Nenhum vídeo encontrado na varredura.")
        return

    print(f"\n[INFO] Acervo completo mapeado: {len(catalog)} cultos!")
    primeiro = catalog[0]
    ultimo = catalog[-1]
    print(f"[INFO] 1º Culto (001): {primeiro.get('titulo_original')} ({str(primeiro.get('data_publicacao'))[:10]})")
    print(f"[INFO] Último Culto ({len(catalog):03d}): {ultimo.get('titulo_original')} ({str(ultimo.get('data_publicacao'))[:10]})\n")

    print("[PASSO 2] Iniciando o download ordenado dos arquivos MP3 leves...")

    downloaded_count = 0
    skipped_count = 0
    error_count = 0

    pbar = tqdm(catalog, desc="Progresso MP3s", unit="áudio")

    for item in pbar:
        v_id = item["video_id"]
        idx = item.get("indice_sequencial", 1)
        date_str = str(item.get("data_publicacao", ""))[:10]
        title = item.get("titulo_sanitizado", "culto")

        display_name = f"[{idx:03d}/{len(catalog):03d}] Baixando {idx:03d}_{date_str}_{v_id}_{title[:30]}"
        pbar.set_postfix_str(display_name)

        if not args.force_redownload and state_mgr.is_audio_downloaded(v_id):
            skipped_count += 1
            continue

        try:
            audio_path = sweeper.download_audio_file(item)
            if audio_path and os.path.exists(audio_path):
                downloaded_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.warning(f"⚠️ Erro ao baixar vídeo {v_id}: {e}")
            error_count += 1

    print("\n" + "=" * 75)
    print(" RESUMO DA EXECUTÇÃO DA ETAPA 1:")
    print(f"   • Total Mapeado: {len(catalog)} cultos")
    print(f"   • Baixados Agora: {downloaded_count} arquivos")
    print(f"   • Já Existiam (Ignorados): {skipped_count} arquivos")
    print(f"   • Erros / Reservados: {error_count} arquivos")
    print(f"   • Pasta dos Áudios: {AUDIO_DIR}")
    print(f"   • Banco de Dados: {DB_PATH}")
    print("=" * 75)
    print(" [ETAPA 1 CONCLUÍDA COM SUCESSO!]")
    print(" Agora você pode executar a ETAPA 2 rodando: python 2_transcrever_fila.py")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
