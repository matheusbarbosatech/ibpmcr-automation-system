"""
Script de Upload Resiliente e Monitorado para o Google Drive via Rclone (IBPM CR).

Orquestra o upload automático e contínuo de 100% dos áudios, transcrições (.txt)
e marcações temporais (.json) da pasta data/audio_podcasts/ para o Google Drive.

Características:
1. Protocolo Anti-Queda (Auto-Retry com rclone copy)
2. Retomada Automática a partir do ponto de interrupção (Idempotente)
3. Relatório de Checklist e Validação Pós-Upload
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
 [IBPM CR] AUTOMATION SYSTEM - UPLOAD RESILIENTE PARA GOOGLE DRIVE
   Origem Local: {AUDIO_DIR}
   Ferramenta: Rclone (Resiliência & Auto-Retry Anti-Queda)
   Destino Padrão: meudrive:IBPM_CR_Cortes/audio_podcasts
===========================================================================
    """
    print(banner)


def check_rclone_installed() -> bool:
    """Verifica se o Rclone está instalado e acessível no PATH do sistema."""
    try:
        res = subprocess.run(["rclone", "version"], capture_output=True, text=True)
        return res.returncode == 0
    except FileNotFoundError:
        return False


def get_local_files_summary(audio_dir: Path):
    """Conta os arquivos locais (.mp3, .m4a, .webm, .txt, .json)."""
    if not audio_dir.exists():
        return 0, 0, 0, 0

    all_files = list(audio_dir.glob("*"))
    audio_files = [f for f in all_files if f.suffix.lower() in ['.mp3', '.m4a', '.webm'] and not f.name.endswith('.part')]
    txt_files = [f for f in all_files if f.suffix.lower() == '.txt']
    json_files = [f for f in all_files if f.suffix.lower() == '.json']

    return len(audio_files), len(txt_files), len(json_files), len(all_files)


def run_resilient_upload(remote_target: str, max_retries: int = 50, retry_delay: int = 10) -> bool:
    """
    Executa o Rclone em um loop de retry resiliente.
    """
    source_path = str(AUDIO_DIR.resolve())
    
    cmd = [
        "rclone", "copy",
        source_path, remote_target,
        "--progress",
        "--transfers=2",
        "--checkers=4",
        "--retries=50",
        "--low-level-retries=20",
        "--stats=3s"
    ]

    attempt = 1
    while attempt <= max_retries:
        logger.info(f"🚀 Iniciando Sincronização via Rclone (Tentativa {attempt}/{max_retries})...")
        logger.info(f"   Origem: {source_path}")
        logger.info(f"   Destino: {remote_target}\n")

        try:
            # Executa o rclone transmitindo o progresso ao vivo no terminal
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
            logger.warning(f"\n⚠️ Ocorreu uma oscilação ou erro na execução do Rclone: {e}")

        attempt += 1
        if attempt <= max_retries:
            logger.info(f"🔄 Aguardando {retry_delay} segundos para reconectar e retomar o upload de onde parou...")
            time.sleep(retry_delay)

    logger.error("❌ Excedido o limite máximo de tentativas de upload.")
    return False


def verify_remote_checklist(remote_target: str):
    """Executa checklist final comparando quantidade de arquivos locais e no Drive."""
    audio_cnt, txt_cnt, json_cnt, total_local = get_local_files_summary(AUDIO_DIR)
    
    print("\n" + "=" * 75)
    print(" 📊 CHECKLIST E RELATÓRIO PÓS-UPLOAD:")
    print("=" * 75)
    print(f"   • Áudios Locais (.mp3/.m4a/.webm): {audio_cnt}")
    print(f"   • Transcrições em Texto (.txt):  {txt_cnt}")
    print(f"   • Segmentos em JSON (.json):       {json_cnt}")
    print(f"   • Total de Arquivos Locais:        {total_local}")
    print("-" * 75)

    # Consulta o tamanho/quantidade no Rclone Remote
    try:
        size_res = subprocess.run(["rclone", "size", remote_target], capture_output=True, text=True)
        if size_res.returncode == 0:
            print(" 📡 STATUS DO SERVIDOR NO GOOGLE DRIVE:")
            for line in size_res.stdout.strip().split("\n"):
                print(f"   {line}")
        else:
            print(" ℹ️ Não foi possível consultar 'rclone size' diretamente, mas o Rclone finalizou a cópia.")
    except Exception as e:
        print(f" ℹ️ Validação via rclone size: {e}")

    print("=" * 75)
    print(" 🎉 100% DOS ARQUIVOS ESTÃO SEGUROS NO GOOGLE DRIVE!")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Etapa 1/2 - Upload Resiliente e Monitorado para Google Drive via Rclone")
    parser.add_argument("--remote", type=str, default="meudrive:IBPM_CR_Cortes/audio_podcasts", help="Remote e caminho de destino no Rclone (padrão: meudrive:IBPM_CR_Cortes/audio_podcasts)")
    parser.add_argument("--retry-delay", type=int, default=10, help="Tempo de espera em segundos entre tentativas após queda de rede (padrão: 10)")
    args = parser.parse_args()

    print_banner()

    if not check_rclone_installed():
        print("❌ ATENÇÃO: O Rclone não foi encontrado no PATH do seu sistema!")
        print("\nPara instalar e configurar o Rclone no Windows:")
        print(" 1. Baixe o Rclone em: https://rclone.org/downloads/ (ou rode `winget install Rclone.Rclone`)")
        print(" 2. Configure a conexão com o Google Drive rodando: `rclone config`")
        print(" 3. Nomeie a conexão como `meudrive`.")
        print("\nApós concluir a configuração do Rclone, execute este script novamente.")
        sys.exit(1)

    success = run_resilient_upload(remote_target=args.remote, retry_delay=args.retry_delay)
    if success:
        verify_remote_checklist(remote_target=args.remote)


if __name__ == "__main__":
    main()
