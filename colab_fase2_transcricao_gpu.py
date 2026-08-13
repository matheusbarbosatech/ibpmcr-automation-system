# ===========================================================================
# 🚀 FASE 2 PURA: TRANSCRIÇÃO EM MASSA (GPU T4 + WHISPER LARGE-V3)
# ===========================================================================
# Arquitetura de Dados Desacoplada (ETL): Transcrição em Massa Atômica e Resiliente

import os, json, sqlite3, torch, logging
from pathlib import Path

# 🛑 MORDAÇA NOS AVISOS DO HUGGING FACE
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

# Conecta ao Google Drive
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
except ImportError:
    pass

# Instala apenas as bibliotecas de transcrição
os.system("pip install -q faster-whisper tqdm torch")

from tqdm import tqdm
from faster_whisper import WhisperModel

# 📂 PASTAS NO SEU GOOGLE DRIVE
GDRIVE_DIR = Path("/content/drive/MyDrive/IBPM_CR_Cortes")
AUDIO_DIR = GDRIVE_DIR / "audio_podcasts"
TRANSCRICOES_DIR = AUDIO_DIR / "transcricoes"
DB_PATH = GDRIVE_DIR / "ibpmcr_master.db"

TRANSCRICOES_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 💾 PREPARAÇÃO DO BANCO DE DADOS
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transcricoes (
        nome_arquivo TEXT PRIMARY KEY,
        texto_completo TEXT,
        segments_json TEXT
    )
""")
conn.commit()

# ⚡ CONFIGURAÇÃO DA GPU E MODELO
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "float32"

print("===========================================================================")
print(f" 🚀 FASE 2: TRANSCRIÇÃO ISOLADA (GPU {device.upper()})")
print("    Modelo: Faster-Whisper LARGE-V3 (Máxima Precisão)")
print("===========================================================================\n")

print("Carregando o modelo na placa de vídeo (isso leva alguns segundos)...")
whisper_model = WhisperModel("large-v3", device=device, compute_type=compute_type)

# 🔍 MAPEAMENTO DA FILA DE ÁUDIOS
audio_files = sorted([f for f in AUDIO_DIR.glob("*") if f.suffix.lower() in [".mp3", ".m4a", ".webm"] and not f.name.endswith(".part")])

# Filtra apenas os que ainda não foram transcritos com sucesso (tamanho > 100 bytes)
pending_files = []
for f in audio_files:
    txt_path = TRANSCRICOES_DIR / f"{f.stem}.txt"
    json_path = TRANSCRICOES_DIR / f"{f.stem}.json"
    if not (txt_path.exists() and txt_path.stat().st_size > 100 and json_path.exists() and json_path.stat().st_size > 100):
        pending_files.append(f)

print(f"📋 Cultos na fila para transcrever: {len(pending_files)} / {len(audio_files)}\n")

if not pending_files:
    print("🎉 Todos os áudios já foram transcritos com sucesso!")
else:
    for audio_path in tqdm(pending_files, desc="Transcrevendo Cultos", unit="vídeo"):
        v_name = audio_path.stem
        txt_path = TRANSCRICOES_DIR / f"{v_name}.txt"
        json_path = TRANSCRICOES_DIR / f"{v_name}.json"
        
        # Salvamento temporário (Atômico) para evitar corrompimento
        tmp_txt = TRANSCRICOES_DIR / f"{v_name}.tmp.txt"
        tmp_json = TRANSCRICOES_DIR / f"{v_name}.tmp.json"
        
        try:
            # Transcrição com timestamps precisos
            segments, info = whisper_model.transcribe(str(audio_path), language="pt", beam_size=5, vad_filter=True, word_timestamps=True)
            
            segments_data, full_text_parts = [], []
            for seg in segments:
                segments_data.append({
                    "start_sec": round(seg.start, 2), 
                    "end_sec": round(seg.end, 2), 
                    "text": seg.text.strip()
                })
                full_text_parts.append(seg.text.strip())
                
            full_text = " ".join(full_text_parts)
            
            # Escreve nos arquivos temporários
            with open(tmp_txt, "w", encoding="utf-8") as f: 
                f.write(full_text)
            with open(tmp_json, "w", encoding="utf-8") as f: 
                f.write(json.dumps(segments_data, ensure_ascii=False, indent=2))
                
            # Renomeia para os arquivos finais de forma segura
            tmp_txt.replace(txt_path)
            tmp_json.replace(json_path)
            
            # Grava no banco de dados SQLite
            cursor.execute("INSERT OR REPLACE INTO transcricoes VALUES (?, ?, ?)", 
                           (v_name, full_text, json.dumps(segments_data, ensure_ascii=False)))
            conn.commit()
            
        except KeyboardInterrupt:
            print(f"\n🛑 Processo interrompido manualmente pelo usuário durante: {v_name}")
            if tmp_txt.exists(): tmp_txt.unlink()
            if tmp_json.exists(): tmp_json.unlink()
            break
        except Exception as e:
            print(f"\n⚠️ Erro inesperado ao transcrever {v_name}: {e}")
            if tmp_txt.exists(): tmp_txt.unlink()
            if tmp_json.exists(): tmp_json.unlink()

conn.close()
print("\n" + "=" * 75)
print(" ✅ FASE 2 PAUSADA OU CONCLUÍDA COM TOTAL SEGURANÇA!")
print("=" * 75)
