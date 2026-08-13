import sqlite3
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect('data/db/ibpmcr_master.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT indice_sequencial, data_publicacao, video_id, titulo_original, caminho_audio FROM videos WHERE audio_baixado = 1 ORDER BY indice_sequencial ASC LIMIT 10")

print("--- PRIMEIROS 10 ÁUDIOS REAIS BAIXADOS E ORGANIZADOS ---")
for r in cursor.fetchall():
    p = r['caminho_audio']
    fname = os.path.basename(p) if p else 'NENHUM'
    size_mb = os.path.getsize(p) / (1024 * 1024) if p and os.path.exists(p) else 0
    idx = r['indice_sequencial']
    pub = str(r['data_publicacao'])[:10]
    print(f" [{idx:03d}] Data Postagem: {pub} | Tamanho: {size_mb:.2f} MB | Arquivo: {fname}")
