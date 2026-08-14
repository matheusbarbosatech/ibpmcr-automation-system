"""
Bot de Monitoramento Diário e Ingestão do YouTube - IBPM CR.

Monitora o canal @ibpmcr7976 1 vez por dia (intervalo padrão de 24 horas / 86400s),
detectando automaticamente novos cultos, festividades e transmissões ao vivo.
Baixa os áudios MP3 leves e os sincroniza imediatamente com o Google Drive via Rclone!

Uso no Terminal:
    python bot_monitor_youtube.py
    python bot_monitor_youtube.py --interval 86400 (1 vez por dia)
"""

import sys
import os
import time
import argparse
import logging
from pathlib import Path

# Configuração de UTF-8 no console do Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from config.settings import AUDIO_DIR, DB_PATH
from src.discovery.channel_sweeper import ChannelSweeper
from src.core.state_manager import MasterPlanManager
from upload_monitorado import run_resilient_upload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BotMonitorYouTube")


def print_banner(interval_sec: int):
    horas = interval_sec // 3600
    banner = f"""
===========================================================================
 🤖 [IBPM CR] BOT MONITOR DIÁRIO DE CULTOS & FESTIVIDADES NO YOUTUBE
   Canal Monitorado:   @ibpmcr7976 (IBPM CR)
   Frequência:         1 VEZ POR DIA ({horas} horas / {interval_sec}s)
   Destino MP3 Local:  {AUDIO_DIR}
   Sincronização Cloud: Auto Rclone -> meudrive:IBPM_CR_Cortes/audio_podcasts
===========================================================================
    """
    print(banner)


def check_and_ingest_new_sermons(sweeper: ChannelSweeper, state_mgr: MasterPlanManager, limit: int = 600) -> int:
    logger.info("📡 Varrendo canal do YouTube (@ibpmcr7976) em busca de novos cultos/festividades do dia...")
    catalog = sweeper.sweep_and_index_channel(limit=limit)

    if not catalog:
        logger.warning("⚠️ Nenhum vídeo/live encontrado na varredura.")
        return 0

    new_downloads_count = 0

    for item in catalog:
        v_id = item["video_id"]
        idx = item.get("indice_sequencial", 1)
        date_str = str(item.get("data_publicacao", ""))[:10]
        title = item.get("titulo_original", "Culto")

        # Se já está baixado no banco ou no disco local, pula
        if state_mgr.is_audio_downloaded(v_id):
            continue

        logger.info(f"\n🎉 NOVO CULTO DETECTADO! [{idx:03d}] {date_str} - {title}")
        logger.info(f"📥 Baixando áudio MP3 leve para {v_id}...")

        try:
            audio_path = sweeper.download_audio_file(item)
            if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 10000:
                logger.info(f"✅ Áudio baixado com sucesso: {os.path.basename(audio_path)}")
                new_downloads_count += 1
        except Exception as e:
            logger.warning(f"⚠️ Falha ao baixar o novo culto {v_id}: {e}")

    if new_downloads_count > 0:
        logger.info(f"\n🚀 {new_downloads_count} novo(s) culto(s) baixado(s)! Disparando sincronização Rclone para o Google Drive...")
        run_resilient_upload("meudrive:IBPM_CR_Cortes/audio_podcasts")
    else:
        logger.info("✨ Pasta de áudios local e Google Drive já estão 100% atualizados para o dia de hoje!")

    return new_downloads_count


def main():
    parser = argparse.ArgumentParser(description="Bot Monitor Diário de Cultos e Festividades no YouTube (IBPM CR)")
    parser.add_argument("--interval", type=int, default=86400, help="Intervalo de checagem em segundos (padrão: 86400s / 1 vez por dia)")
    parser.add_argument("--single-run", action="store_true", help="Executar apenas uma checagem diária e encerrar")
    args = parser.parse_args()

    print_banner(interval_sec=args.interval)

    state_mgr = MasterPlanManager()
    sweeper = ChannelSweeper()

    logger.info("👀 Bot da Fase 1 Iniciado! Monitorando o YouTube diariamente...\n")

    cycle_count = 1

    while True:
        try:
            logger.info(f"🔄 --- Ciclo de Checagem Diária #{cycle_count} ---")
            new_files = check_and_ingest_new_sermons(sweeper, state_mgr)

            if args.single_run:
                logger.info("✅ Varredura diária única concluída.")
                break

            horas = args.interval // 3600
            logger.info(f"😴 Monitorando... Próxima varredura diária automática no YouTube em {horas} horas ({args.interval}s).\n")
            time.sleep(args.interval)
            cycle_count += 1

        except KeyboardInterrupt:
            logger.info("\n🛑 Monitoramento diário do YouTube encerrado pelo usuário.")
            break
        except Exception as e:
            logger.warning(f"⚠️ Ocorreu um erro no ciclo de monitoramento: {e}. Reiniciando ciclo em 60s...")
            time.sleep(60)


if __name__ == "__main__":
    main()
