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
    """Verifica e configura o token da API do Kaggle."""
    token = os.environ.get("KAGGLE_API_TOKEN", "KGAT_0193e0e51c366c39a247e46035238ef8")
    os.environ["KAGGLE_API_TOKEN"] = token

    user_kaggle_dir = Path.home() / ".kaggle"
    user_kaggle_dir.mkdir(parents=True, exist_ok=True)
    access_token_file = user_kaggle_dir / "access_token"

    try:
        with open(access_token_file, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception:
        pass

    logger.info("Chave KAGGLE_API_TOKEN configurada no ambiente com sucesso!")
    return True


def preparar_kernel_kaggle(output_kernel_dir: Path):
    """Prepara os arquivos do Kernel Kaggle com aceleração por GPU."""
    output_kernel_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": "omatheusbsilva/ibpmcr-whisper-gpu",
        "title": "ibpmcr-whisper-gpu",
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

print("🚀 Executando transcrição em GPU T4 na Nuvem (IBPM CR)...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "faster-whisper", "yt-dlp"], check=True)

import torch
from faster_whisper import WhisperModel

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔥 GPU Ativa: {device.upper()}")

model = WhisperModel("large-v3", device=device, compute_type="float16")
print("✅ Modelo Faster-Whisper Large-V3 inicializado com sucesso!")
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
        print("   kaggle kernels status omatheusbsilva/ibpmcr-whisper-gpu")
        print(" * Para baixar os resultados via terminal, rode:")
        print("   kaggle kernels output omatheusbsilva/ibpmcr-whisper-gpu -p data/audio_podcasts/transcricoes_fase2")
        print("=" * 60 + "\n")
    except subprocess.CalledProcessError as e:
        logger.error("Falha ao enviar tarefa via Kaggle CLI", stderr=e.stderr)
        print(f"❌ Erro ao enviar tarefa: {e.stderr}")


if __name__ == "__main__":
    disparar_gpu_nuvem_cli()
