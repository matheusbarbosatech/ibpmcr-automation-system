import sys
import os
import sqlite3
import yt_dlp
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AUDIO_DIR = Path("data/audio_podcasts")
DB_PATH = Path("data/db/ibpmcr_master.db")
v_id = "YqY27cQZf9s"
url = "https://www.youtube.com/watch?v=YqY27cQZf9s"

print(f"=== BAIXANDO O ÁUDIO COMPLETO DO CULTO DE ONTEM (ID: {v_id}) ===")

# Remove arquivos incompletos (.part ou .ytdl)
for f in AUDIO_DIR.glob(f"*{v_id}*"):
    try:
        f.unlink()
        print(f"Removido temporário: {f.name}")
    except Exception as e:
        print(f"Aviso ao remover {f.name}: {e}")

out_path = AUDIO_DIR / f"449_2026-08-13_{v_id}_2_dia_de_festividade_ministerio_de_adoracao_e_danca_12_08_26.m4a"

ydl_opts = {
    'format': 'ba/ba*/bestaudio/best',
    'outtmpl': str(out_path),
    'quiet': False,
    'no_warnings': False,
    'nocheckcertificate': True,
    'cookiefile': 'cookies.txt',
    'remote_components': ['ejs:github'],
    'js_runtimes': {'node': {}}
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])

if out_path.exists() and out_path.stat().st_size > 100000:
    sz_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ DOWNLOAD 100% CONCLUÍDO COM SUCESSO!")
    print(f"Arquivo Final: {out_path.name}")
    print(f"Tamanho Total: {sz_mb:.2f} MB")

    # Atualiza SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE videos SET audio_baixado = 1, caminho_audio = ? WHERE video_id = ?", (str(out_path.resolve()), v_id))
    conn.commit()
    conn.close()
    print("✅ Atualizado no banco SQLite!")
else:
    print("❌ Falha ao finalizar arquivo.")
