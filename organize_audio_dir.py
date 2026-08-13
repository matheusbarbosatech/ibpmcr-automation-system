import sys
import os
import glob
import sqlite3
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

AUDIO_DIR = Path("data/audio_podcasts")
DB_PATH = Path("data/db/ibpmcr_master.db")

print("=== INICIANDO A ORGANIZAÇÃO DA PASTA DE ÁUDIOS ===")
print(f"Pasta Alvo: {AUDIO_DIR.resolve()}\n")

# 1. Conectar ao Banco de Dados SQLite
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Busca todos os vídeos ordenados por indice_sequencial
cursor.execute("SELECT video_id, indice_sequencial, nome_arquivo_mp3, data_publicacao, titulo_sanitizado FROM videos ORDER BY indice_sequencial ASC")
db_videos = {r["video_id"]: dict(r) for r in cursor.fetchall()}

# 2. Varrer arquivos na pasta de áudios
all_files = list(AUDIO_DIR.glob("*.*"))
print(f"Total de arquivos encontrados na pasta: {len(all_files)}")

mock_removed = 0
duplicates_removed = 0
valid_audios = 0

for file_path in all_files:
    size = file_path.stat().st_size

    # Se for um placeholder (tamanho menor ou igual a 100 bytes)
    if size <= 100:
        try:
            file_path.unlink()
            mock_removed += 1
        except Exception as e:
            print(f"Erro ao remover {file_path.name}: {e}")
        continue

# Atualiza lista de arquivos restantes válidos
real_files = list(AUDIO_DIR.glob("*.*"))
print(f"✅ Removidos {mock_removed} arquivos temporários (placeholders).")
print(f"📦 Arquivos reais restantes com áudio completo: {len(real_files)}\n")

# 3. Atualizar o Banco SQLite com o status real de cada áudio baixado
cursor.execute("UPDATE videos SET audio_baixado = 0, caminho_audio = NULL")
conn.commit()

updated_count = 0
for file_path in real_files:
    fname = file_path.name
    # Extrai o video_id do nome do arquivo
    for v_id, meta in db_videos.items():
        if v_id in fname:
            cursor.execute("UPDATE videos SET audio_baixado = 1, caminho_audio = ? WHERE video_id = ?", (str(file_path.resolve()), v_id))
            updated_count += 1
            break

conn.commit()

print("=== RESUMO DA ORGANIZAÇÃO DA PASTA ===")
print(f" • Áudios Reais Preservados: {len(real_files)}")
print(f" • Registros Atualizados no SQLite: {updated_count}")
print(f" • Pasta de Destino Limpa: {AUDIO_DIR.resolve()}")
print("=======================================\n")

conn.close()
