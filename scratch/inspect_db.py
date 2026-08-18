import sqlite3
import json
from pathlib import Path

db_path = Path("data_storage/plano_mestre_ibpmcr.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print("Tabelas encontradas:", tables)
    for table_name in tables:
        t = table_name[0]
        count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f" - Tabela: {t} | Registros: {count}")
