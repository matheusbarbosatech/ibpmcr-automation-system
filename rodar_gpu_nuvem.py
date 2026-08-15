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

    lista_file = BASE_DIR / "data" / "lista_audios_sem_transcricao.txt"
    pendentes_list = []
    if lista_file.exists():
        with open(lista_file, "r", encoding="utf-8") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith("#"):
                    pendentes_list.append(l)

    metadata = {
        "id": "omatheusbsilva/ibpmcr-whisper-gpu",
        "title": "ibpmcr-whisper-gpu",
        "code_file": "notebook_gpu.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",
        "dataset_sources": [],
        "kernel_sources": [],
        "competition_sources": []
    }

    with open(output_kernel_dir / "kernel-metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    pendentes_json_str = json.dumps(pendentes_list, ensure_ascii=False)

    py_code = f"""import os
import sys
import re
import glob
import json
import traceback
import subprocess
from pathlib import Path

def log(msg):
    print(msg)
    sys.stdout.flush()
    try:
        with open("execution_log.txt", "a", encoding="utf-8") as f:
            f.write(str(msg) + chr(10))
    except Exception:
        pass

try:
    log("[IBPM CR GPU] Instalando bibliotecas sem alterar PyTorch...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "faster-whisper", "yt-dlp"], check=False)

    import torch
    log(f"[IBPM CR GPU] PyTorch Versao: {{torch.__version__}} | CUDA Disponivel: {{torch.cuda.is_available()}}")

    model = None
    use_faster = True

    try:
        from faster_whisper import WhisperModel
        log("[IBPM CR GPU] Tentando inicializar Faster-Whisper Large-V3 em CUDA (float16)...")
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        log("[IBPM CR GPU] Modelo Faster-Whisper Large-V3 GPU ativado com sucesso!")
    except Exception as e_cuda:
        log(f"[IBPM CR GPU] Falha ao carregar CUDA ({e_cuda}). Ativando CTranslate2 CPU (int8 4-threads)...")
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=4)
            log("[IBPM CR GPU] Modelo Faster-Whisper CPU INT8 ativado!")
        except Exception as e_cpu:
            log(f"[IBPM CR GPU] Falha no CTranslate2 CPU ({e_cpu}), carregando OpenAI Whisper...")
            import whisper
            model = whisper.load_model("large-v3", device="cpu")
            use_faster = False
            log("[IBPM CR GPU] Modelo OpenAI Whisper CPU carregado!")

    pendentes = {pendentes_json_str}
    log(f"[IBPM CR GPU] Total de cultos pendentes a transcrever: {{len(pendentes)}}")

    out_dir = Path(".")

    def extract_video_id(filename):
        match = re.search(r'_([a-zA-Z0-9_-]{{11}})_', filename)
        return match.group(1) if match else None

    def format_timestamp(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{{hrs:02d}}:{{mins:02d}}:{{secs:02d}}"

    for idx, audio_name in enumerate(pendentes[:50], start=1):
        vid = extract_video_id(audio_name)
        stem = Path(audio_name).stem
        txt_out = out_dir / f"{{stem}}.txt"
        json_out = out_dir / f"{{stem}}.json"

        if not vid or txt_out.exists():
            continue

        log(f"[PROGRESS {{idx}}/{{len(pendentes)}}] Baixando audio do YouTube (ID: {{vid}})...")
        output_template = f"/tmp/audio_{{vid}}.%(ext)s"
        cmd_dl = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android,web",
            "--no-check-certificates",
            "-f", "ba",
            "-o", output_template,
            f"https://www.youtube.com/watch?v={{vid}}"
        ]

        try:
            res_dl = subprocess.run(cmd_dl, capture_output=True, text=True, check=True)
        except Exception as e:
            log(f"Erro ao baixar audio {{vid}}: {{e}}")
            if hasattr(e, 'stderr') and e.stderr:
                log(f"yt-dlp stderr: {{e.stderr[:300]}}")
            continue

        # Encontra o arquivo de áudio baixado (.m4a, .webm, .opus)
        matches = glob.glob(f"/tmp/audio_{{vid}}.*")
        if not matches:
            log(f"Nenhum arquivo encontrado para {{vid}} em /tmp/")
            continue

        temp_audio = Path(matches[0])
        log(f"[PROGRESS {{idx}}/{{len(pendentes)}}] Transcrevendo na GPU ({{temp_audio.name}}): {{audio_name}}...")
        try:
            txt_lines = []
            seg_list = []

            if use_faster:
                segments, info = model.transcribe(str(temp_audio), language="pt", beam_size=5, vad_filter=True)
                for seg in segments:
                    ts = format_timestamp(seg.start)
                    txt_lines.append(f"[{{ts}}] {{seg.text.strip()}}")
                    seg_list.append({{"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}})
            else:
                res = model.transcribe(str(temp_audio), language="pt")
                for seg in res.get("segments", []):
                    st = seg.get("start", 0.0)
                    txt = seg.get("text", "").strip()
                    ts = format_timestamp(st)
                    txt_lines.append(f"[{{ts}}] {{txt}}")
                    seg_list.append({{"start": round(st, 2), "end": round(seg.get("end", 0.0), 2), "text": txt}})

            with open(txt_out, "w", encoding="utf-8") as f:
                f.write(f"TRANSCRIÇÃO WHISPER LARGE-V3 GPU\\nARQUIVO: {{audio_name}}\\n\\n" + "\\n".join(txt_lines))

            with open(json_out, "w", encoding="utf-8") as f:
                json.dump({{"arquivo": audio_name, "video_id": vid, "segments": seg_list}}, f, ensure_ascii=False, indent=2)

            temp_audio.unlink(missing_ok=True)
            log(f"[OK {{idx}}/{{len(pendentes)}}] Transcricao concluida -> {{txt_out.name}}")
        except Exception as err:
            log(f"Erro ao transcrever {{audio_name}}: {{err}}")

    log("[IBPM CR GPU] PROCESSO CONCLUIDO COM SUCESSO!")
except Exception as fatal_err:
    log(f"FATAL ERROR NO KERNEL GPU: {{fatal_err}}")
    traceback.print_exc()
"""

    notebook_data = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [py_code]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }

    with open(output_kernel_dir / "notebook_gpu.ipynb", "w", encoding="utf-8") as f:
        json.dump(notebook_data, f, indent=2)

    logger.info("Kernel de GPU preparado como Notebook (.ipynb) com sucesso", path=str(output_kernel_dir))


def monitorar_gpu_nuvem(kernel_ref: str = "omatheusbsilva/ibpmcr-whisper-gpu", interval_sec: int = 10, auto_download: bool = True):
    """
    Monitora a execução da GPU na nuvem em tempo real no terminal
    e baixa automaticamente os arquivos ao terminar.
    """
    import time
    logger.info("📡 Iniciando monitoramento em tempo real da GPU na nuvem...", kernel=kernel_ref)

    print("\n" + "=" * 65)
    print(" 📡 MONITORAMENTO EM TEMPO REAL DA GPU NA NUVEM (IBPM CR)")
    print("=" * 65)
    print(" Aguarde... O terminal atualizará o status a cada 10 segundos.")
    print(" Ao finalizar, as transcrições serão baixadas automaticamente!")
    print("=" * 65 + "\n")

    cmd_status = ["kaggle", "kernels", "status", kernel_ref]
    last_status = ""

    while True:
        try:
            res = subprocess.run(cmd_status, capture_output=True, text=True)
            output = res.stdout.strip()
            
            if "RUNNING" in output:
                curr_time = datetime.now().strftime("%H:%M:%S")
                print(f"[{curr_time}] ⚡ Status: PROCESSANDO NA GPU (KernelWorkerStatus.RUNNING)...")
            elif "COMPLETE" in output:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] STATUS: CONCLUIDO COM SUCESSO! (KernelWorkerStatus.COMPLETE)")
                
                if auto_download:
                    print("Baixando transcricoes geradas diretamente para 'data/audio_podcasts/transcricoes_fase2/'...")
                    out_dir = BASE_DIR / "data" / "audio_podcasts" / "transcricoes_fase2"
                    cmd_out = ["kaggle", "kernels", "output", kernel_ref, "-p", str(out_dir)]
                    sub_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
                    subprocess.run(cmd_out, env=sub_env, capture_output=True, text=True, encoding="utf-8", errors="ignore")
                    print(f"TODAS AS TRANSCRIÇOES FORAM SALVAS EM '{out_dir}'!")
                    
                    exec_log_file = out_dir / "execution_log.txt"
                    if exec_log_file.exists():
                        print("\n--- LOG DE EXECUÇÃO DA GPU (ÚLTIMAS LINHAS) ---")
                        with open(exec_log_file, "r", encoding="utf-8", errors="ignore") as elf:
                            print(elf.read()[-1500:])
                        print("--------------------------------------------------\n")
                break
            elif "ERROR" in output:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] STATUS: ERRO NA EXECUCAO DA GPU (KernelWorkerStatus.ERROR)")
                print("Tentando baixar logs de erro...")
                cmd_out = ["kaggle", "kernels", "output", kernel_ref, "-p", "logs/kaggle_error"]
                sub_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
                res_err = subprocess.run(cmd_out, env=sub_env, capture_output=True, text=True, encoding="utf-8", errors="ignore")
                log_file = BASE_DIR / "logs" / "kaggle_error" / f"{Path(kernel_ref).name}.log"
                if log_file.exists():
                    print("\n--- ULTIMOS LOGS DA GPU NO KAGGLE ---")
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as lf:
                        print(lf.read()[-1500:])
                    print("-------------------------------------\n")
                break
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Status: {output}")

        except KeyboardInterrupt:
            print("\n⚠️ Monitoramento pausado pelo usuário. A GPU continua rodando na nuvem.")
            break
        except Exception as e:
            print(f"⚠️ Erro ao checar status: {e}")

        time.sleep(interval_sec)


def disparar_gpu_nuvem_cli(monitor: bool = True):
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
        print("=" * 60 + "\n")

        if monitor:
            monitorar_gpu_nuvem()

    except subprocess.CalledProcessError as e:
        logger.error("Falha ao enviar tarefa via Kaggle CLI", stderr=e.stderr)
        print(f"❌ Erro ao enviar tarefa: {e.stderr}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Orquestrador CLI de GPU na Nuvem (IBPM CR)")
    parser.add_argument("--monitor-only", action="store_true", help="Apenas monitora a tarefa em execução na GPU sem reenviar")
    parser.add_argument("--no-monitor", action="store_true", help="Envia para a GPU sem ficar aguardando no terminal")

    args = parser.parse_args()

    if args.monitor_only:
        monitorar_gpu_nuvem()
    else:
        disparar_gpu_nuvem_cli(monitor=not args.no_monitor)


if __name__ == "__main__":
    from datetime import datetime
    main()
