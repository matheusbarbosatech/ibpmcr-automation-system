import sys
import os
import sqlite3
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

AUDIO_DIR = Path("data/audio_podcasts")
DB_PATH = Path("data/db/ibpmcr_master.db")

print("=== PADRONIZANDO E RENOMEANDO ARQUIVOS DE ÁUDIO NO DISCO ===")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT video_id, indice_sequencial, data_publicacao, titulo_sanitizado FROM videos ORDER BY indice_sequencial ASC")
db_videos = {r["video_id"]: dict(r) for r in cursor.fetchall()}

audio_files = list(AUDIO_DIR.glob("*.*"))
renamed_count = 0

for file_path in audio_files:
    fname = file_path.name
    ext = file_path.suffix.lower()

    # Identifica o video_id
    matched_vid = None
    for v_id in db_videos:
        if v_id in fname:
            matched_vid = v_id
            break

    if matched_vid:
        meta = db_videos[matched_vid]
        idx = meta["indice_sequencial"]
        pub_date = str(meta["data_publicacao"])[:10]
        clean_title = meta["titulo_sanitizado"]

        target_name = f"{idx:03d}_{pub_date}_{matched_vid}_{clean_title}{ext}"
        target_path = AUDIO_DIR / target_name

        if file_path != target_path:
            try:
                if target_path.exists():
                    target_path.unlink()
                file_path.rename(target_path)
                renamed_count += 1
            except Exception as e:
                print(f"Erro ao renomear {fname}: {e}")
                target_path = file_path

        cursor.execute("UPDATE videos SET audio_baixado = 1, caminho_audio = ? WHERE video_id = ?", (str(target_path.resolve()), matched_vid))

conn.commit()

cursor.execute("SELECT COUNT(*) FROM videos WHERE audio_baixado = 1")
downloaded_in_db = cursor.fetchone()[0]

print("=== RESULTADO DA PADRONIZAÇÃO DA PASTA ===")
print(f" • Arquivos Renomeados/Padronizados: {renamed_count}")
print(f" • Total de Cultos Marcados como Baixados no SQLite: {downloaded_in_db}")
print(f" • Pasta de Destino: {AUDIO_DIR.resolve()}")
print("==========================================\n")

conn.close()
