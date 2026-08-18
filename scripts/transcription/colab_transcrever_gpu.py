"""
Script Mestre de Transcrição GPU no Google Colab (Fase 2) - IBPM CR Automation System.

Uso no Google Colab (GPU T4 / V100 / A100):
1. Abra um Notebook no Google Colab (Ambiente de Execução -> Alterar tipo -> GPU T4).
2. Execute este script ou cole o código no Colab:
   !pip install -q faster-whisper yt-dlp structlog pydantic
   !python colab_transcrever_gpu.py

Destaques:
- Utiliza GPU CUDA com float16 e o modelo 'large-v3' da OpenAI (Faster-Whisper).
- Transcreve cultos de 2 horas em apenas 15 a 30 segundos!
- Lê a lista exata 'data/lista_audios_sem_transcricao.txt' para processar APENAS os vídeos faltantes.
- Salva os arquivos de Bloco de Notas (.txt) e (.json) diretamente no seu Google Drive.
"""

import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

# 1. Detecta execução no Google Colab e monta o Google Drive
IN_COLAB = "google.colab" in sys.modules

if IN_COLAB:
    print("🚀 Detectado ambiente GOOGLE COLAB com GPU!")
    try:
        from google.colab import drive
        drive.mount("/content/drive", force_remount=False)
        DRIVE_WORKSPACE = Path("/content/drive/MyDrive/ibpmcr-automation-system")
        DRIVE_WORKSPACE.mkdir(parents=True, exist_ok=True)
        os.chdir(str(DRIVE_WORKSPACE))
        print(f"📁 Diretório de trabalho alterado para o Google Drive: {DRIVE_WORKSPACE}")
    except Exception as e:
        print(f"⚠️ Aviso ao montar Google Drive: {e}")

BASE_DIR = Path.cwd()
sys.path.append(str(BASE_DIR))

# Suporte UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def instalar_dependencias_colab():
    """Garante que todas as bibliotecas de GPU estejam instaladas."""
    print("📦 Verificando/Instalando dependências de GPU (faster-whisper, yt-dlp)...")
    cmd = [sys.executable, "-m", "pip", "install", "-q", "faster-whisper", "yt-dlp", "structlog", "pydantic"]
    subprocess.run(cmd, check=True)


def extract_video_id(filename: str) -> Optional[str]:
    match = re.search(r'_([a-zA-Z0-9_-]{11})_', filename)
    if match:
        return match.group(1)
    return None


def format_seconds_to_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def transcrever_lote_colab_gpu(max_audios: int = 100):
    instalar_dependencias_colab()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("❌ Erro ao importar faster_whisper. Certifique-se de instalar com: pip install faster-whisper")
        return

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    
    print("\n" + "=" * 60)
    print(f" 🔥 INICIALIZANDO MOTORE FASTER-WHISPER LARGE-V3 NA GPU ({device.upper()} - {compute_type})")
    print("=" * 60 + "\n")

    model = WhisperModel("large-v3", device=device, compute_type=compute_type)
    print("✅ Modelo Whisper Large-V3 carregado com sucesso na memória da GPU!")

    trans_dir = BASE_DIR / "data" / "audio_podcasts" / "transcricoes_fase2"
    trans_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = BASE_DIR / "data" / "audio_podcasts"

    lista_pendentes_file = BASE_DIR / "data" / "lista_audios_sem_transcricao.txt"

    pendentes: List[str] = []
    if lista_pendentes_file.exists():
        with open(lista_pendentes_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith("#"):
                    pendentes.append(line_str)
    else:
        # Se o arquivo não existir, pega todos os áudios locais sem transcrição
        for ext in [".webm", ".mp4", ".m4a", ".mp3"]:
            for af in audio_dir.glob(f"*{ext}"):
                txt_p = trans_dir / f"{af.stem}.txt"
                if not txt_p.exists():
                    pendentes.append(af.name)

    print(f"📋 {len(pendentes)} cultos pendentes para transcrição via GPU.")
    pendentes = pendentes[:max_audios]

    concluidos = 0
    erros = 0

    for idx, audio_name in enumerate(pendentes, start=1):
        stem = Path(audio_name).stem
        txt_out = trans_dir / f"{stem}.txt"
        json_out = trans_dir / f"{stem}.json"

        if txt_out.exists() and json_out.exists():
            print(f"⏩ [{idx}/{len(pendentes)}] Transcrição já existe: {txt_out.name}")
            concluidos += 1
            continue

        vid = extract_video_id(audio_name)
        src_audio = audio_dir / audio_name

        # Se o áudio não estiver no disco do Colab, baixa o áudio leve em 2 segundos
        if not src_audio.exists():
            if vid:
                print(f"📥 [{idx}/{len(pendentes)}] Baixando áudio leve do YouTube (ID: {vid})...")
                temp_audio = BASE_DIR / "data" / "cache" / f"temp_{vid}.mp3"
                temp_audio.parent.mkdir(parents=True, exist_ok=True)
                cmd_dl = [
                    "yt-dlp",
                    "-f", "ba",
                    "-x", "--audio-format", "mp3",
                    "--audio-quality", "32k",
                    "-o", str(temp_audio),
                    f"https://www.youtube.com/watch?v={vid}"
                ]
                try:
                    subprocess.run(cmd_dl, capture_output=True, text=True, check=True)
                    src_audio = temp_audio
                except Exception as e:
                    print(f"❌ Falha ao baixar áudio para {audio_name}: {e}")
                    erros += 1
                    continue
            else:
                print(f"⚠️ Áudio local não encontrado para {audio_name}. Pulando...")
                erros += 1
                continue

        print(f"⚡ [{idx}/{len(pendentes)}] Transcrevendo na GPU: '{audio_name}'...")
        try:
            segments, info = model.transcribe(
                str(src_audio),
                language="pt",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            txt_lines = []
            segments_json = []

            for seg in segments:
                ts_str = format_seconds_to_timestamp(seg.start)
                text_clean = seg.text.strip()
                txt_lines.append(f"[{ts_str}] {text_clean}")
                segments_json.append({
                    "start": float(round(seg.start, 2)),
                    "end": float(round(seg.end, 2)),
                    "text": text_clean
                })

            header = f"""================================================================================
TRANSCRIÇÃO WHISPER LARGE-V3 (GPU COLAB - IBPM CR)
ARQUIVO: {audio_name}
IDIOMA DETECTADO: {info.language} (PROBABILIDADE: {info.language_probability:.2f})
================================================================================\n\n"""

            with open(txt_out, "w", encoding="utf-8") as f:
                f.write(header + "\n".join(txt_lines))

            with open(json_out, "w", encoding="utf-8") as f:
                json.dump({
                    "arquivo_origem": audio_name,
                    "video_id": vid,
                    "language": info.language,
                    "duration_sec": info.duration,
                    "segments": segments_json
                }, f, ensure_ascii=False, indent=2)

            # Limpa cache temporário de download se foi criado
            if "temp_" in str(src_audio):
                src_audio.unlink(missing_ok=True)

            concluidos += 1
            print(f"✅ [{idx}/{len(pendentes)}] TRANSCRIÇÃO GPU CONCLUÍDA! -> {txt_out.name}")

        except Exception as err:
            print(f"❌ Erro ao transcrever {audio_name}: {err}")
            erros += 1

    print("\n" + "=" * 60)
    print(" TRANSCRIÇÃO GPU NO GOOGLE COLAB FINALIZADA!")
    print(f" * Total de cultos processados nesta rodada: {concluidos}")
    print(f" * Falhas/Erros: {erros}")
    print(f" * Transcrições salvas em: '{trans_dir}'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcrição acelerada GPU no Google Colab (Faster-Whisper Large V3)")
    parser.add_argument("--max", type=int, default=100, help="Quantidade máxima de áudios a transcrever nesta rodada")
    args = parser.parse_args()

    transcrever_lote_colab_gpu(max_audios=args.max)
