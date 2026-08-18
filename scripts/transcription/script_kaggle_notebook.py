# ==============================================================================
# SCRIPT DE TRANSCRIÇÃO ACELERADA VIA GPU T4 PARA NOTEBOOK KAGGLE
# Modelo: Faster-Whisper (Large-V3)
# ==============================================================================
# INSTRUÇÕES NO KAGGLE:
# 1. No menu lateral direito ("Notebook options"), ative a ACCELERATOR -> "GPU T4 x2" ou "GPU P100".
# 2. Em "Input", adicione o seu Dataset com os 3 áudios (ou faça o upload direto).
# 3. Cole este código em uma célula e clique em EXECUTAR (Shift + Enter).
# 4. Ao finalizar, baixe os arquivos .txt e .json na aba "Output" à direita.
# ==============================================================================

import os
import sys
import glob
import json
import time
import subprocess
from pathlib import Path

print("=" * 70)
print("🎙️ TRANSCRIÇÃO AUTOMÁTICA DOS 3 CULTOS IBPM NA GPU KAGGLE (FASTER-WHISPER)")
print("=" * 70)

# 1. Instalar dependências necessárias
print("\n[1/4] Instalando faster-whisper no Kaggle...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "faster-whisper"], check=False)

# pyrefly: ignore [missing-import]
import torch
print(f"   • PyTorch: {torch.__version__}")
print(f"   • GPU CUDA Disponível: {torch.cuda.is_available()}")

# 2. Carregar o Modelo Faster-Whisper Large-V3 na GPU
from faster_whisper import WhisperModel

print("\n[2/4] Carregando modelo Whisper Large-V3 na GPU...")
try:
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    print("   ✅ Modelo Large-V3 float16 carregado com sucesso na GPU CUDA!")
except Exception as e:
    print(f"   ⚠️ Tentando float32 por compatibilidade: {e}")
    model = WhisperModel("large-v3", device="cuda", compute_type="float32")

# 3. Encontrar os arquivos de áudio no dataset (/kaggle/input ou /kaggle/working)
print("\n[3/4] Procurando arquivos de áudio nos diretórios do Kaggle...")
audio_exts = ["*.webm", "*.m4a", "*.mp3", "*.wav", "*.mp4", "*.ogg", "*.flac"]
audio_files = []

for ext in audio_exts:
    audio_files.extend(glob.glob(f"/kaggle/input/**/{ext}", recursive=True))
    audio_files.extend(glob.glob(f"/kaggle/working/**/{ext}", recursive=True))

audio_files = sorted(list(set(audio_files)))
print(f"   🎯 Encontrados {len(audio_files)} áudio(s) para transcrever:")
for a in audio_files:
    print(f"     - {Path(a).name}")

if not audio_files:
    print("\n❌ NENHUM ARQUIVO DE ÁUDIO ENCONTRADO!")
    print("👉 Certifique-se de adicionar o seu Dataset de áudios no menu 'Add Input' à direita no Kaggle.")
    sys.exit(0)

# Função para formatar timestamp [HH:MM:SS]
def format_ts(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# 4. Transcrever cada arquivo e salvar em /kaggle/working/
out_dir = Path("/kaggle/working")
sucessos = 0

print("\n[4/4] Iniciando transcrição acelerada por GPU...\n")
inicio_total = time.time()

for idx, audio_path in enumerate(audio_files, start=1):
    arq = Path(audio_path)
    stem = arq.stem
    txt_path = out_dir / f"{stem}.txt"
    json_path = out_dir / f"{stem}.json"

    print(f"----------------------------------------------------------------------")
    print(f"[{idx}/{len(audio_files)}] 🎙️ Transcrevendo: {arq.name}")
    print(f"----------------------------------------------------------------------")
    
    t0 = time.time()
    try:
        segments, info = model.transcribe(
            str(arq),
            language="pt",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        txt_lines = []
        seg_list = []
        raw_words = []

        for seg in segments:
            ts = format_ts(seg.start)
            txt_lines.append(f"[{ts}] {seg.text.strip()}")
            raw_words.append(seg.text.strip())
            seg_list.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip()
            })

        # Salvar arquivo TXT com formatação completa
        header = f"TRANSCRIÇÃO WHISPER LARGE-V3 GPU\nARQUIVO: {arq.name}\nDURAÇÃO: {info.duration:.1f}s\n\n"
        body = "\n".join(txt_lines)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(header + body)

        # Salvar arquivo JSON com metadados e trechos
        payload = {
            "file": arq.name,
            "duration": round(info.duration, 2),
            "language": info.language,
            "text": " ".join(raw_words),
            "segments": seg_list
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        tempo_decorrido = time.time() - t0
        print(f"   ✅ Concluído em {tempo_decorrido:.1f}s! (Duração do Culto: {info.duration/60:.1f} min)")
        print(f"   📁 Salvo: {txt_path.name} e {json_path.name}")
        sucessos += 1

    except Exception as err:
        print(f"   ❌ Erro ao transcrever {arq.name}: {err}")

tempo_total = time.time() - inicio_total
print("\n" + "=" * 70)
print(f"🎉 FINALIZADO COM SUCESSO!")
print(f"• Total Transcrito: {sucessos}/{len(audio_files)} arquivos")
print(f"• Tempo Total de GPU: {tempo_total/60:.1f} minutos")
print(f"• Os arquivos .txt e .json estão prontos para download no painel 'Output'!")
print("=" * 70)
