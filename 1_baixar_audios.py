"""
======================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 1: DOWNLOAD DE ÁUDIOS MP3 LEVES
======================================================================

Script de execução exclusiva da ETAPA 1.
Varre prioritariamente a aba /streams do canal @ibpmcr7976, ordena todo o acervo
do vídeo MAIS ANTIGO (001 em 2022) ao MAIS RECENTE e realiza o download padronizado
dos arquivos MP3 leves (64kbps mono) em data/audio_podcasts/.

Nomenclatura Obrigatória:
  001_YYYY-MM-DD_[VIDEO_ID]_[TITULO_SANITIZADO].mp3
  002_YYYY-MM-DD_[VIDEO_ID]_[TITULO_SANITIZADO].mp3
  ...
  447_YYYY-MM-DD_[VIDEO_ID]_[TITULO_SANITIZADO].mp3

Uso:
  python 1_baixar_audios.py [--limit 500]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

# Garante importação do diretório raiz
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DB_PATH, AUDIO_DIR
from src.core.state_manager import MasterPlanManager
from src.discovery.channel_sweeper import ChannelSweeper

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa1_Download")


def main():
    parser = argparse.ArgumentParser(description="Etapa 1: Download de Áudios MP3 Leves - IBPM CR")
    parser.add_argument("--limit", type=int, default=600, help="Limite máximo de cultos a varrer (padrão: 600)")
    args = parser.parse_args()

    print("\n" + "="*75)
    print(" [IBPM CR] AUTOMATION SYSTEM - ETAPA 1: DOWNLOAD DE ÁUDIOS MP3 LEVES")
    print("   Canal: @ibpmcr7976 | Acervo Histórico: 02/10/2022 até Hoje")
    print("   Foco: Mapeamento /streams + Download de MP3 (64kbps mono)")
    print(f"   Pasta de Destino: {AUDIO_DIR}")
    print("="*75 + "\n")

    # 1. Inicializa gerenciadores
    state_mgr = MasterPlanManager()
    sweeper = ChannelSweeper()

    # 2. Varrer acervo e ordenar cronologicamente do 001 ao mais recente
    logger.info("[PASSO 1] Mapeando a aba /streams do canal @ibpmcr7976 e ordenando do mais antigo ao mais recente...")
    catalog = sweeper.sweep_and_index_channel(limit=args.limit)

    total_videos = len(catalog)
    if total_videos == 0:
        logger.error("[ERRO] Nenhum vídeo encontrado na varredura.")
        sys.exit(1)

    print(f"\n[INFO] Acervo completo mapeado: {total_videos} cultos!")
    print(f"[INFO] 1º Culto (001): {catalog[0].get('titulo_original')} ({catalog[0].get('data_publicacao')[:10]})")
    print(f"[INFO] Último Culto ({total_videos:03d}): {catalog[-1].get('titulo_original')} ({catalog[-1].get('data_publicacao')[:10]})\n")

    # 3. Executa o download ordenado e idempotente de cada arquivo MP3
    logger.info("[PASSO 2] Iniciando o download ordenado dos arquivos MP3 leves...")

    downloaded_this_run = 0
    already_on_hd = 0

    with tqdm(total=total_videos, desc="Progresso MP3s", unit="áudio") as pbar:
        for item in catalog:
            v_id = item["video_id"]
            idx = item.get("indice_sequencial", 1)
            filename = item.get("nome_arquivo_mp3", f"{idx:03d}_{v_id}.mp3")

            # Checagem de Idempotência: pula se já existir no HD
            if state_mgr.is_audio_downloaded(v_id):
                already_on_hd += 1
                pbar.set_postfix_str(f"[{idx:03d}/{total_videos:03d}] Já no HD")
                pbar.update(1)
                continue

            # Realiza o download do arquivo MP3
            pbar.set_postfix_str(f"[{idx:03d}/{total_videos:03d}] Baixando {filename[:30]}...")
            audio_path = sweeper.download_audio_file(item)
            downloaded_this_run += 1

            pbar.update(1)

    # 4. Estatísticas Finais de Disco e Conclusão
    total_size_bytes = 0
    if os.path.exists(AUDIO_DIR):
        for fname in os.listdir(AUDIO_DIR):
            fp = os.path.join(AUDIO_DIR, fname)
            if os.path.isfile(fp):
                total_size_bytes += os.path.getsize(fp)

    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
    total_size_gb = round(total_size_bytes / (1024 * 1024 * 1024), 2)

    print("\n" + "="*75)
    print(" 🎉 [ETAPA 1 CONCLUÍDA COM SUCESSO!]")
    print(f"   - Total de Cultos Mapeados:       {total_videos}")
    print(f"   - Áudios Baixados nesta Rodada:  {downloaded_this_run}")
    print(f"   - Áudios Já Existentes no HD:    {already_on_hd}")
    print(f"   - Espaço Total Ocupado em Disco: {total_size_mb} MB ({total_size_gb} GB)")
    print(f"   - Pasta dos MP3s:                {AUDIO_DIR}")
    print(f"   - Banco SQLite Local:            {DB_PATH}")
    print("="*75)
    print("\n👉 PRÓXIMO PASSO: Execute 'python 2_transcrever_fila.py' para iniciar a transcrição sequencial dos MP3s!\n")


if __name__ == "__main__":
    main()
