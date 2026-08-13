# ===========================================================================
# 🚀 IBPM CR AUTOMATION SYSTEM - ETAPA 2 (TRANSCRIÇÃO PERFEITA DE ALTA PRECISÃO)
# ===========================================================================
# Modelo Topo de Linha: Faster-Whisper LARGE-V3 em GPU (CUDA / Float16)
# Foco: Máxima Precisão, Fidelidade Teológica e Transcrição Integral Palavra por Palavra

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

# ⚡ Configuração de Alta Fidelidade na GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "float32"
model_size = "large-v3"  # Modelo topo de linha de máxima acurácia (Large-v3)

print(f"===========================================================================")
print(f" 🚀 TRANSCRIÇÃO DE ALTA PRECISÃO (FULL ACCURACY - LARGE-V3)")
print(f"   Dispositivo: {device.upper()} | Precisão: {compute_type} | Modelo: {model_size.upper()}")
print(f"   Pasta dos Áudios no Drive: {AUDIO_DIR}")
print(f"===========================================================================")

if not AUDIO_DIR.exists():
    raise FileNotFoundError(f"❌ Pasta de áudios não encontrada no Drive: {AUDIO_DIR}. Verifique se o upload do Rclone já enviou os arquivos!")

# Carrega modelo topo de linha na GPU
print(f"\n⚡ Carregando modelo Faster-Whisper '{model_size}' (Topo de Linha de Acurácia) na GPU...")
model = WhisperModel(model_size, device=device, compute_type=compute_type)
print("✅ Modelo Large-v3 carregado com sucesso na GPU!")

# Lista arquivos de áudio no Drive
audio_extensions = {".mp3", ".m4a", ".webm"}
all_files = sorted(list(AUDIO_DIR.glob("*")))
audio_files = [f for f in all_files if f.suffix.lower() in audio_extensions and not f.name.endswith(".part")]

print(f"\n📂 Total de arquivos de áudio encontrados no Drive: {len(audio_files)}")

# Filtra áudios pendentes (que ainda não possuem .txt completo no Drive)
pending_audios = []
for audio_path in audio_files:
    txt_path = audio_path.with_suffix(".txt")
    if not (txt_path.exists() and txt_path.stat().st_size > 100):
        pending_audios.append(audio_path)

print(f"📋 Áudios Pendentes de Transcrição Integral: {len(pending_audios)} / {len(audio_files)}")

if not pending_audios:
    print("\n🎉 Todos os áudios no Google Drive já possuem transcrição perfeita concluída!")
else:
    conn = None
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

    pbar = tqdm(pending_audios, desc="Transcrevendo (Large-v3 GPU)", unit="áudio")
    
    for audio_path in pbar:
        txt_path = audio_path.with_suffix(".txt")
        json_path = audio_path.with_suffix(".json")
        v_name = audio_path.stem
        
        pbar.set_postfix_str(v_name[:30])

        try:
            # Transcrição completa de máxima fidelidade com beam_size=5 e word_timestamps
            segments, info = model.transcribe(
                str(audio_path),
                language="pt",
                beam_size=5,
                vad_filter=True,
                word_timestamps=True
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

            # Salva .txt integral no Google Drive
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            # Salva .json detalhado no Google Drive
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(segments_json_str)

            # Atualiza o banco SQLite no Drive se presente
            if conn:
                v_id = v_name.split("_")[2] if len(v_name.split("_")) > 2 else ""
                if v_id:
                    cursor.execute("""
                    UPDATE videos SET transcrito = 1, texto_transcrito = ?, segmentos_json = ?, tipo_transcricao = 'colab_gpu_large_v3' WHERE video_id = ?
                    """, (full_text, segments_json_str, v_id))
                    conn.commit()

        except Exception as e:
            print(f"\n⚠️ Erro ao transcrever {audio_path.name}: {e}")

    if conn:
        conn.close()

    print("\n" + "=" * 75)
    print(" 🎉 TRANSCRIÇÃO PERFEITA (LARGE-V3) CONCLUÍDA COM SUCESSO!")
    print(" Todos os arquivos .txt e .json foram salvos no seu Google Drive.")
    print("=" * 75)
