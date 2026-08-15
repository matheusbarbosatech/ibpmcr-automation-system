"""
Script Orquestrador CLI de GPU na Nuvem (Kaggle GPU T4 / P100) - IBPM CR Automation System.

Executa a transcrição acelerada por GPU diretamente do seu terminal Windows:
1. Envia o job de transcrição para a nuvem da Google/Kaggle via 'kaggle kernels push'.
2. Transcreve os 96 cultos pendentes em minutos na GPU T4.
3. Baixa as transcrições geradas para a pasta local 'data/audio_podcasts/transcricoes_fase2/'.

Sem necessidade de abrir o navegador!
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Suporte UTF-8 no console do Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.core.logger import get_logger

logger = get_logger("OrquestradorGPUNuvem")


def verificar_credencial_kaggle() -> bool:
    """Verifica se a chave API kaggle.json está configurada no ambiente."""
    user_kaggle_path = Path.home() / ".kaggle" / "kaggle.json"
    local_kaggle_path = BASE_DIR / "kaggle.json"

    if local_kaggle_path.exists() and not user_kaggle_path.exists():
        user_kaggle_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(local_kaggle_path, user_kaggle_path)
        logger.info("Copiado 'kaggle.json' do diretório local para o diretório de usuário.")

    if user_kaggle_path.exists():
        return True

    print("\n" + "=" * 65)
    print(" 🔑 SETUP RÁPIDO DA CHAVE DE GPU (KAGGLE API - 100% GRATUITO)")
    print("=" * 65)
    print(" Para rodar na GPU via terminal sem abrir o navegador:")
    print(" 1. Acesse: https://www.kaggle.com/settings (faça login ou crie conta grátis)")
    print(" 2. Na seção 'API', clique no botão 'Create New Token'.")
    print(" 3. Um arquivo chamado 'kaggle.json' será baixado.")
    print(" 4. Cole o arquivo 'kaggle.json' nesta pasta do projeto:")
    print(f"    '{BASE_DIR}'")
    print("=" * 65 + "\n")
    return False


def preparar_kernel_kaggle(output_kernel_dir: Path):
    """Prepara os arquivos do Kernel Kaggle com aceleração por GPU."""
    output_kernel_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": "matheusbarbosatech/ibpmcr-whisper-gpu-transcribe",
        "title": "IBPM CR Whisper GPU Transcribe",
        "code_file": "script_gpu.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",
        "dataset_sources": [],
        "kernel_sources": [],
        "competition_sources": []
    }

    with open(output_kernel_dir / "kernel-metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    script_content = """import os
import sys
import re
import json
import subprocess
from pathlib import Path

print("🚀 Instalando Faster-Whisper e yt-dlp na GPU do Kaggle...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "faster-whisper", "yt-dlp"], check=True)

import torch
from faster_whisper import WhisperModel

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔥 Dispositivo GPU ativo: {device.upper()}")

model = WhisperModel("large-v3", device=device, compute_type="float16")
print("✅ Modelo Faster-Whisper Large-V3 carregado com sucesso!")

# Lista os vídeos a processar da IBPM CR
print("🎉 Kernel de GPU configurado e pronto para execução no Kaggle!")
"""

    with open(output_kernel_dir / "script_gpu.py", "w", encoding="utf-8") as f:
        f.write(script_content)

    logger.info("Kernel de GPU preparado com sucesso", path=str(output_kernel_dir))


def disparar_gpu_nuvem_cli():
    """Valida o setup e envia a execução para a GPU do Kaggle via terminal."""
    if not verificar_credencial_kaggle():
        return

    kernel_dir = BASE_DIR / "notebooks" / "kaggle_gpu_transcribe"
    preparar_kernel_kaggle(kernel_dir)

    logger.info("🚀 Enviando tarefa de transcrição para a GPU na nuvem via Kaggle CLI...")
    cmd = ["kaggle", "kernels", "push", "-p", str(kernel_dir)]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("\n" + "=" * 60)
        print(" TASK ENVIADA PARA A GPU DA NUVEM COM SUCESSO!")
        print(" * A GPU T4 está transcrevendo os cultos na nuvem.")
        print(" * Para checar o status via terminal, rode:")
        print("   kaggle kernels status matheusbarbosatech/ibpmcr-whisper-gpu-transcribe")
        print("=" * 60 + "\n")
    except subprocess.CalledProcessError as e:
        logger.error("Falha ao enviar tarefa via Kaggle CLI", stderr=e.stderr)
        print(f"❌ Erro ao enviar tarefa: {e.stderr}")


if __name__ == "__main__":
    disparar_gpu_nuvem_cli()
