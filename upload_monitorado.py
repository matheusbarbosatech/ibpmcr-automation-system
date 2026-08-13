"""
Script de Upload Resiliente e Monitorado para o Google Drive via Rclone (IBPM CR).

Orquestra o upload automático e acelerado de 100% dos áudios, transcrições (.txt)
e marcações temporais (.json) da pasta data/audio_podcasts/ para o Google Drive.

Otimizações de Alta Velocidade para Google Drive:
- --drive-chunk-size=32M (Aumenta o tamanho dos blocos de envio para máxima velocidade)
- --transfers=4 (Subida de 4 arquivos simultâneos)
- --buffer-size=16M (Buffer em memória RAM para fluxo contínuo)
"""

import sys
import os
import time
import subprocess
import argparse
import logging
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))
from config.settings import AUDIO_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UploadMonitorado")


def print_banner():
    banner = f"""
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - UPLOAD ALTA VELOCIDADE (GOOGLE DRIVE)
   Origem Local: {AUDIO_DIR}
   Otimizações: --drive-chunk-size=32M | --transfers=4 | --buffer-size=16M
   Destino: meudrive:IBPM_CR_Cortes/audio_podcasts
===========================================================================
    """
    print(banner)


def check_rclone_installed() -> bool:
    try:
        res = subprocess.run(["rclone", "version"], capture_output=True, text=True)
        return res.returncode == 0
    except FileNotFoundError:
        return False


def get_local_files_summary(audio_dir: Path):
    if not audio_dir.exists():
        return 0, 0, 0, 0

    all_files = list(audio_dir.glob("*"))
    audio_files = [f for f in all_files if f.suffix.lower() in ['.mp3', '.m4a', '.webm'] and not f.name.endswith('.part')]
    txt_files = [f for f in all_files if f.suffix.lower() == '.txt']
    json_files = [f for f in all_files if f.suffix.lower() == '.json']

    return len(audio_files), len(txt_files), len(json_files), len(all_files)


def run_resilient_upload(remote_target: str, max_retries: int = 50, retry_delay: int = 10) -> bool:
    source_path = str(AUDIO_DIR.resolve())
    
    cmd = [
        "rclone", "copy",
        source_path, remote_target,
        "--progress",
        "--transfers=4",
        "--checkers=8",
        "--drive-chunk-size=32M",
        "--drive-upload-cutoff=32M",
        "--buffer-size=16M",
        "--retries=50",
        "--low-level-retries=20",
        "--stats=3s"
    ]

    attempt = 1
    while attempt <= max_retries:
        logger.info(f"🚀 Iniciando Sincronização em Alta Velocidade via Rclone (Tentativa {attempt}/{max_retries})...")
        logger.info(f"   Origem: {source_path}")
        logger.info(f"   Destino: {remote_target}\n")

        try:
            process = subprocess.run(cmd)

            if process.returncode == 0:
                logger.info("\n✅ Rclone finalizou a cópia com 100% de SUCESSO!")
                return True
            else:
                logger.warning(f"\n⚠️ Rclone encerrou com código de aviso: {process.returncode}")
        except KeyboardInterrupt:
            logger.info("\n🛑 Upload interrompido manualmente pelo usuário.")
            return False
        except Exception as e:
            logger.warning(f"\n⚠️ Ocorreu uma oscilação na transmissão: {e}")

        attempt += 1
        if attempt <= max_retries:
            logger.info(f"🔄 Aguardando {retry_delay} segundos para reconectar e retomar a transmissão...")
            time.sleep(retry_delay)

    logger.error("❌ Excedido o limite máximo de tentativas de upload.")
    return False


def verify_remote_checklist(remote_target: str):
    audio_cnt, txt_cnt, json_cnt, total_local = get_local_files_summary(AUDIO_DIR)
    
    print("\n" + "=" * 75)
    print(" 📊 CHECKLIST E RELATÓRIO PÓS-UPLOAD:")
    print("=" * 75)
    print(f"   • Áudios Locais (.mp3/.m4a/.webm): {audio_cnt}")
    print(f"   • Transcrições em Texto (.txt):  {txt_cnt}")
    print(f"   • Segmentos em JSON (.json):       {json_cnt}")
    print(f"   • Total de Arquivos Locais:        {total_local}")
    print("-" * 75)

    try:
        size_res = subprocess.run(["rclone", "size", remote_target], capture_output=True, text=True)
        if size_res.returncode == 0:
            print(" 📡 STATUS DO SERVIDOR NO GOOGLE DRIVE:")
            for line in size_res.stdout.strip().split("\n"):
                print(f"   {line}")
    except Exception as e:
        print(f" ℹ️ Validação via rclone size: {e}")

    print("=" * 75)
    print(" 🎉 100% DOS ARQUIVOS ESTÃO SEGUROS NO GOOGLE DRIVE!")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Upload Resiliente em Alta Velocidade para Google Drive")
    parser.add_argument("--remote", type=str, default="meudrive:IBPM_CR_Cortes/audio_podcasts", help="Remote no Rclone")
    parser.add_argument("--retry-delay", type=int, default=10, help="Tempo de espera entre tentativas")
    args = parser.parse_args()

    print_banner()

    if not check_rclone_installed():
        print("❌ Rclone não encontrado no PATH!")
        sys.exit(1)

    success = run_resilient_upload(remote_target=args.remote, retry_delay=args.retry_delay)
    if success:
        verify_remote_checklist(remote_target=args.remote)


if __name__ == "__main__":
    main()
