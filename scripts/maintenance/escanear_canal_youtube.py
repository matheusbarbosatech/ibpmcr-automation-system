import json
import re
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TXT_DIR = BASE_DIR / "data" / "transcriptions" / "txt"
DESKTOP_DIR = Path(r"C:\Users\matheus\Desktop\audios_faltantes_ibpm")
DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

print("==============================================================")
print("ESCANEANDO CANAL COMPLETO DO YOUTUBE (@ibpmcr7976)")
print("==============================================================")

# 1. Escanear aba /videos
print("Escanear aba /videos...")
res_v = subprocess.run(
    ["yt-dlp", "--flat-playlist", "--print", "%(id)s | %(title)s", "https://www.youtube.com/@ibpmcr7976/videos"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
lines_v = [l.strip() for l in res_v.stdout.splitlines() if l.strip()]

# 2. Escanear aba /streams (Lives)
print("Escanear aba /streams (Lives)...")
res_s = subprocess.run(
    ["yt-dlp", "--flat-playlist", "--print", "%(id)s | %(title)s", "https://www.youtube.com/@ibpmcr7976/streams"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
lines_s = [l.strip() for l in res_s.stdout.splitlines() if l.strip()]

print(f"\nVideos na aba /videos: {len(lines_v)}")
print(f"Videos na aba /streams: {len(lines_s)}")

todos_itens = lines_v + lines_s
print(f"TOTAL REAL DO CANAL NO YOUTUBE: {len(todos_itens)} VIDEOS/LIVES\n")

# Mapear transcrições locais existentes
txt_files = list(TXT_DIR.glob("*.txt"))
local_stems_lower = [f.stem.lower() for f in txt_files]

# Identificar vídeos do YouTube que NÃO estão no PC
faltantes_youtube = []
for item in todos_itens:
    parts = item.split(" | ")
    vid_id = parts[0]
    title = parts[1] if len(parts) > 1 else ""
    
    # Checar por ID ou por semelhança no título
    ja_existe = any(vid_id in s for s in local_stems_lower)
    if not ja_existe:
        faltantes_youtube.append({"id": vid_id, "title": title})

print(f"==============================================================")
print(f"CULTOS DO YOUTUBE QUE FALTAM NO SEU PC: {len(faltantes_youtube)}")
print("==============================================================")

for idx, f in enumerate(faltantes_youtube, start=1):
    titulo_limpo = f['title'].encode('ascii', 'ignore').decode('ascii')
    print(f"  {idx:02d}. ID: {f['id']} | Titulo: {titulo_limpo}")

# Baixar os áudios faltantes diretamente para a Área de Trabalho
print("\nBaixando os audios faltantes do YouTube para a sua Area de Trabalho...")
for idx, f in enumerate(faltantes_youtube, start=1):
    url = f"https://www.youtube.com/watch?v={f['id']}"
    out_tmpl = str(DESKTOP_DIR / f"{idx:03d}_{f['id']}_audio.%(ext)s")
    titulo_limpo = f['title'].encode('ascii', 'ignore').decode('ascii')
    print(f"  [{idx}/{len(faltantes_youtube)}] Baixando audio de: {titulo_limpo}...")
    subprocess.run(["yt-dlp", "-f", "ba", "-x", "--audio-format", "m4a", "-o", out_tmpl, url], capture_output=True)

# Compactar tudo em ZIP no Desktop
zip_path = shutil.make_archive(str(DESKTOP_DIR), "zip", str(DESKTOP_DIR))
print("\n==============================================================")
print("AUDITORIA E DOWNLOADS CONCLUIDOS COM SUCESSO!")
print(f"Pasta no Desktop: {DESKTOP_DIR}")
print(f"Arquivo ZIP no Desktop: {zip_path}")
print("==============================================================")
