import sqlite3
import re

conn = sqlite3.connect("data/db/ibpmcr_master.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT video_id, titulo_original, data_publicacao FROM videos")
rows = cursor.fetchall()


def get_sort_key(r):
    t = r["titulo_original"]
    pub = str(r["data_publicacao"])[:10]
    m = re.search(r'\(.*?\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?\b.*?\)', t)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        day = f"{int(day):02d}"
        month = f"{int(month):02d}"
        if not year:
            year = pub[:4]
        elif len(year) == 2:
            year = "20" + year
        return f"{year}-{month}-{day}"
    return pub


sorted_rows = sorted(rows, key=get_sort_key)
print(f"Total: {len(sorted_rows)}")
print("--- PRIMEIROS 10 (001 a 010) ---")
for i, r in enumerate(sorted_rows[:10], 1):
    print(f"  {i:03d} | {get_sort_key(r)} | {r['titulo_original']}")

print("\n--- ULTIMOS 10 (438 a 447) ---")
for i, r in enumerate(sorted_rows[-10:], len(sorted_rows) - 9):
    print(f"  {i:03d} | {get_sort_key(r)} | {r['titulo_original']}")
