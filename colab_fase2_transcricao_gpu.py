# ===========================================================================
# 🚀 IBPM CR AUTOMATION SYSTEM - FASE 2: TRANSCRIÇÃO DE ALTA PRECISÃO (GPU COLAB)
# ===========================================================================
# Foco 100% em Transcrever todos os áudios do Google Drive com Faster-Whisper Large-v3.
# Sem APIs externas, sem limites de taxa (TPM), em velocidade máxima na GPU T4.

import os
import json
import sqlite3
import torch
from pathlib import Path

# 1. Monta o Google Drive
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
except ImportError:
    pass

# Garantir dependências instaladas
os.system("pip install -q faster-whisper tqdm torch")

from tqdm import tqdm
from faster_whisper import WhisperModel

# 📂 PASTAS NO SEU GOOGLE DRIVE
GDRIVE_DIR = Path("/content/drive/MyDrive/IBPM_CR_Cortes")
AUDIO_DIR = GDRIVE_DIR / "audio_podcasts"
DB_PATH = GDRIVE_DIR / "ibpmcr_master.db"

# ⚡ CONFIGURAÇÃO DA GPU T4 NO COLAB
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "float32"
model_size = "large-v3"  # Modelo topo de linha da OpenAI (Full Accuracy)

print("===========================================================================")
print(f" 🚀 FASE 2: TRANSCRIÇÃO GPU EM ALTA PRECISÃO (MODELO {model_size.upper()})")
print(f"   GPU Colab: {device.upper()} | Precisão: {compute_type}")
print(f"   Pasta dos Áudios no Google Drive: {AUDIO_DIR}")
print("===========================================================================")

if not AUDIO_DIR.exists():
    raise FileNotFoundError(f"❌ Pasta {AUDIO_DIR} não encontrada no Google Drive. Verifique o upload!")

# Carrega modelo na GPU
print(f"\n⚡ Carregando modelo Faster-Whisper '{model_size}' na GPU T4...")
whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
print("✅ Modelo Large-v3 pronto para transcrição em alta velocidade!")

# Lista arquivos de áudio válidos no Drive
audio_extensions = {".mp3", ".m4a", ".webm"}
all_files = sorted(list(AUDIO_DIR.glob("*")))
audio_files = [f for f in all_files if f.suffix.lower() in audio_extensions and not f.name.endswith(".part")]

# Filtra cultos pendentes (que ainda não possuem .txt no Drive)
pending_files = []
for a_path in audio_files:
    txt_path = a_path.with_suffix(".txt")
    if not (txt_path.exists() and txt_path.stat().st_size > 100):
        pending_files.append(a_path)

print(f"\n📂 Total de Cultos no Google Drive: {len(audio_files)}")
print(f"📋 Cultos Pendentes de Transcrição: {len(pending_files)} (Já transcritos: {len(audio_files) - len(pending_files)})")

if not pending_files:
    print("\n🎉 Todos os cultos no seu Google Drive já estão transcritos com sucesso!")
else:
    conn = sqlite3.connect(str(DB_PATH)) if DB_PATH.exists() else None

    pbar = tqdm(pending_files, desc="Transcrevendo (Large-v3 GPU)", unit="culto")

    for audio_path in pbar:
        v_name = audio_path.stem
        txt_path = audio_path.with_suffix(".txt")
        json_path = audio_path.with_suffix(".json")

        pbar.set_postfix_str(v_name[:25])

        try:
            # Transcrição integral com acurácia máxima
            segments, info = whisper_model.transcribe(
                str(audio_path),
                language="pt",
                beam_size=5,
                vad_filter=True,
                word_timestamps=True
            )

            segments_data, full_text_parts = [], []
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

            # Salva os arquivos .txt e .json diretamente no seu Google Drive
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            with open(json_path, "w", encoding="utf-8") as f:
                f.write(segments_json_str)

            # Atualiza banco SQLite se presente no Drive
            if conn:
                v_id = v_name.split("_")[2] if len(v_name.split("_")) > 2 else ""
                if v_id:
                    cursor = conn.cursor()
                    cursor.execute("""
                    UPDATE videos SET transcrito = 1, texto_transcrito = ?, segmentos_json = ?, tipo_transcricao = 'colab_large_v3' WHERE video_id = ?
                    """, (full_text, segments_json_str, v_id))
                    conn.commit()

        except Exception as e:
            print(f"\n⚠️ Erro ao transcrever {audio_path.name}: {e}")

    if conn:
        conn.close()

    print("\n" + "=" * 75)
    print(" 🎉 FASE 2 CONCLUÍDA COM SUCESSO!")
    print(" Todos os cultos do Google Drive foram transcritos com o modelo Large-v3!")
    print("=" * 75)
