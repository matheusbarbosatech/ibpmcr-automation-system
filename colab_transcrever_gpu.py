# ===========================================================================
# 🚀 IBPM CR AUTOMATION SYSTEM - ETAPA 2 (TRANSCRIÇÃO GPU NO GOOGLE COLAB)
# ===========================================================================
# Instruções para rodar no Google Colab (Com GPU T4 Gratuita):
# 1. No Colab, ative a GPU em: Editar -> Configurações do ambiente de execução -> GPU T4
# 2. Monte seu Google Drive e rode os blocos abaixo.

# ---------------------------------------------------------------------------
# CELULA 1: Montar o Google Drive e Instalar Dependências
# ---------------------------------------------------------------------------
"""
from google.colab import drive
drive.mount('/content/drive')

!pip install -q faster-whisper tqdm
"""

# ---------------------------------------------------------------------------
# CELULA 2: Script Principal de Transcrição Ultra-Rápida em GPU (CUDA / Float16)
# ---------------------------------------------------------------------------
import os
import json
import sqlite3
import torch
from pathlib import Path
from tqdm import tqdm
from faster_whisper import WhisperModel

# 📂 Caminhos no Google Drive Montado
GDRIVE_DIR = Path("/content/drive/MyDrive/IBPM_CR_Cortes")
AUDIO_DIR = GDRIVE_DIR / "audio_podcasts"
DB_PATH = GDRIVE_DIR / "ibpmcr_master.db"

# ⚡ Configuração da GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
model_size = "medium"  # Modelo mais preciso em GPU (medium ou base)

print(f"===========================================================================")
print(f" 🚀 INICIANDO TRANSCRIÇÃO GPU NO GOOGLE COLAB")
print(f"   Dispositivo: {device.upper()} | Precisão: {compute_type} | Modelo: Faster-Whisper {model_size.upper()}")
print(f"   Pasta dos Áudios no Drive: {AUDIO_DIR}")
print(f"===========================================================================")

if not AUDIO_DIR.exists():
    raise FileNotFoundError(f"❌ Pasta de áudios não encontrada no Drive: {AUDIO_DIR}. Verifique se o upload do Rclone já enviou os arquivos!")

# Carrega modelo na GPU T4
print(f"\n⚡ Carregando modelo Faster-Whisper '{model_size}' na GPU...")
model = WhisperModel(model_size, device=device, compute_type=compute_type)
print("✅ Modelo carregado na GPU com sucesso!")

# Lista arquivos de áudio válidos no Drive
audio_extensions = {".mp3", ".m4a", ".webm"}
all_files = sorted(list(AUDIO_DIR.glob("*")))
audio_files = [f for f in all_files if f.suffix.lower() in audio_extensions and not f.name.endswith(".part")]

print(f"\n📂 Total de arquivos de áudio encontrados no Drive: {len(audio_files)}")

# Filtra áudios pendentes (que ainda não possuem .txt no Drive)
pending_audios = []
for audio_path in audio_files:
    txt_path = audio_path.with_suffix(".txt")
    if not (txt_path.exists() and txt_path.stat().st_size > 100):
        pending_audios.append(audio_path)

print(f"📋 Áudios Pendentes de Transcrição: {len(pending_audios)} (Já concluídos: {len(audio_files) - len(pending_audios)})")

if not pending_audios:
    print("\n🎉 Todos os áudios no Google Drive já estão transcritos com sucesso!")
else:
    # Conexão opcional com SQLite no Drive se existir
    conn = None
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

    pbar = tqdm(pending_audios, desc="Transcrevendo via GPU", unit="áudio")
    
    for audio_path in pbar:
        txt_path = audio_path.with_suffix(".txt")
        json_path = audio_path.with_suffix(".json")
        v_name = audio_path.stem
        
        pbar.set_postfix_str(v_name[:30])

        try:
            # Transcreve na velocidade máxima da GPU
            segments, info = model.transcribe(
                str(audio_path),
                language="pt",
                beam_size=2,
                vad_filter=True
            )

            segments_data = []
            full_text_parts = []

            for seg in segments:
                segments_data.append({
                    "segment_id": seg.id,
                    "start_sec": round(seg.start, 2),
                    "end_sec": round(seg.end, 2),
                    "text": seg.text.strip()
                })
                full_text_parts.append(seg.text.strip())

            full_text = " ".join(full_text_parts)
            segments_json_str = json.dumps(segments_data, ensure_ascii=False, indent=2)

            # Salva .txt no Google Drive
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            # Salva .json no Google Drive
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(segments_json_str)

            # Atualiza o banco SQLite no Drive se presente
            if conn:
                v_id = v_name.split("_")[2] if len(v_name.split("_")) > 2 else ""
                if v_id:
                    cursor.execute("""
                    UPDATE videos SET transcrito = 1, texto_transcrito = ?, segmentos_json = ?, tipo_transcricao = 'colab_gpu_medium' WHERE video_id = ?
                    """, (full_text, segments_json_str, v_id))
                    conn.commit()

        except Exception as e:
            print(f"\n⚠️ Erro ao transcrever {audio_path.name}: {e}")

    if conn:
        conn.close()

    print("\n" + "=" * 75)
    print(" 🎉 TRANSCRIÇÃO EM GPU NO GOOGLE COLAB CONCLUÍDA COM SUCESSO!")
    print(" Todos os arquivos .txt e .json foram salvos no seu Google Drive.")
    print(" Agora você já pode rodar 'python 3_mineracao_fase3.py' na sua máquina enviando os textos para o Groq!")
    print("=" * 75)
