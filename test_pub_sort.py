import sqlite3

conn = sqlite3.connect("data/db/ibpmcr_master.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT video_id, titulo_original, data_publicacao FROM videos")
rows = cursor.fetchall()

sorted_rows = sorted(rows, key=lambda x: str(x["data_publicacao"]))
print(f"Total de vídeos: {len(sorted_rows)}")

print("\n--- PRIMEIROS 10 VÍDEOS PELA DATA DE POSTAGEM (001 a 010) ---")
for i, r in enumerate(sorted_rows[:10], 1):
    pub = str(r["data_publicacao"])[:10]
    print(f"  {i:03d} | Postado em: {pub} | ID: {r['video_id']} | {r['titulo_original']}")

print("\n--- ÚLTIMOS 10 VÍDEOS PELA DATA DE POSTAGEM (438 a 447) ---")
for i, r in enumerate(sorted_rows[-10:], len(sorted_rows) - 9):
    pub = str(r["data_publicacao"])[:10]
    print(f"  {i:03d} | Postado em: {pub} | ID: {r['video_id']} | {r['titulo_original']}")
